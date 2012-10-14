#!/usr/bin/python
# Copyright (C) 2009-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""Find in files and replace strings in many files."""

__metaclass__ = type

__all__ = [
    'extract_match',
    'find_files',
    'find_matches',
    'Finder',
    ]

from collections import namedtuple
import mimetypes
import os
import re
import sre_constants
import sys
import threading
from optparse import OptionParser

import gobject as GObject
import gtk as Gtk

from gdp import PluginMixin, setup_file_lines_view

try:
    import gedit
    APP_KEY = 'gedit-2'
    import gconf
    import gnomevfs
except:
    import pluma as gedit
    APP_KEY = 'pluma'
    import mateconf as gconf
    import matevfs as gnomevfs

find_params = namedtuple(
    'FindParams', ['path', 'pattern', 'is_re', 'is_case', 'file_pattern'])


def find_matches(root_dir, file_pattern, match_pattern, substitution=None):
    """Iterate a summary of matching lines in a file."""
    match_re = re.compile(match_pattern)
    for candidate in find_files(root_dir, file_pattern=file_pattern):
        file_path, mime_type = candidate
        summary = extract_match(
            file_path, match_re, substitution=substitution)
        if summary:
            summary['mime_type'] = mime_type
            yield summary


def find_files(root_dir, skip_dir_pattern='^[.]', file_pattern='.*'):
    """Iterate the matching files below a directory."""
    skip_dir_re = re.compile(r'^.*%s' % skip_dir_pattern)
    file_re = re.compile(r'^.*%s' % file_pattern)
    for path, subdirs, files in os.walk(root_dir):
        subdirs[:] = [dir_ for dir_ in subdirs
                      if skip_dir_re.match(dir_) is None]
        for file_ in files:
            file_path = os.path.join(path, file_)
            if os.path.islink(file_path):
                continue
            mime_type, encoding_ = mimetypes.guess_type(file_)
            if PluginMixin.is_editable(mime_type):
                if file_re.match(file_path) is not None:
                    yield file_path, mime_type


def extract_match(file_path, match_re, substitution=None):
    """Return a summary of matches in a file."""
    lines = []
    content = []
    match = None
    file_ = open(file_path, 'r')
    try:
        for lineno, line in enumerate(file_):
            match = match_re.search(line)
            if match:
                lines.append(
                    {'lineno': lineno + 1, 'text': line.strip(),
                     'match': match})
                if substitution is not None:
                    line = match_re.sub(substitution, line)
            if substitution is not None:
                content.append(line)
    finally:
        file_.close()
    if lines:
        if substitution is not None:
            file_ = open(file_path, 'w')
            try:
                file_.write(''.join(content))
            finally:
                file_.close()
        return {'file_path': file_path, 'lines': lines}
    return None


class FinderWorker(threading.Thread):

    def __init__(self, treestore, find_params, callback, substitution=None):
        self.treestore = treestore
        self.find_params = find_params
        self.callback = callback
        self.substitution = substitution
        self.theme = Gtk.icon_theme_get_default()

    @property
    def pattern(self):
        pattern = self.find_params.pattern
        if not self.find_params.is_re:
            pattern = re.escape(pattern)
        if not self.find_params.is_case:
            pattern = '(?i)%s' % pattern
        return pattern

    def run(self):
        try:
            for summary in find_matches(
                self.find_params.path, self.find_params.file_pattern,
                self.pattern, substitution=self.substitution):
                file_path = summary['file_path']
                mime_type = summary['mime_type'] or 'text'
                mime_type = 'gnome-mime-%s' % mime_type.replace('/', '-')
                if not self.theme.has_icon(mime_type):
                    mime_type = 'gnome-mime-text'
                piter = self.treestore.append(
                    None,
                    (file_path, mime_type, 0, None, self.find_params.path))
                if self.substitution is None:
                    icon = Gtk.STOCK_FIND
                else:
                    icon = Gtk.STOCK_FIND_AND_REPLACE
                for line in summary['lines']:
                    self.treestore.append(piter,
                        (file_path, icon, line['lineno'], line['text'],
                         self.find_params.path))
            if self.treestore.get_iter_first() is None:
                message = 'No matches found'
                self.treestore.append(
                    None, (message, 'stock_dialog-info', 0, None, None))
        except sre_constants.error, e:
            message = 'Find could not be run: %s' % str(e)
            self.treestore.append(
                None, (message, 'stock_dialog-info', 0, None, None))
        self.callback()


class Finder(PluginMixin):
    """Find and replace content in files."""

    WORKING_DIRECTORY = '<Working Directory>'
    CURRENT_FILE = '<Current File>'
    CURRENT_FILE_DIR = '<Dir of Current File>'
    FILE_BROWSER_ROOT = '<FileBrowser Root Dir>'
    ANY_FILE = '<Any Text File>'

    def __init__(self, window):
        self.window = window
        self.signal_ids = {}
        self.last_find = None
        self.widgets = Gtk.Builder()
        self.widgets.add_from_file(
            '%s/find.ui' % os.path.dirname(__file__))
        self.setup_widgets()
        self.find_panel = self.widgets.get_object('find_side_panel')
        panel = window.get_side_panel()
        icon = Gtk.image_new_from_stock(Gtk.STOCK_FIND, Gtk.ICON_SIZE_MENU)
        panel.add_item(self.find_panel, 'Find in files', icon)

    def setup_widgets(self):
        """Setup the widgets with default data."""
        self.widgets.connect_signals(self.ui_callbacks)
        self.pattern_comboentry = self.widgets.get_object(
            'pattern_comboentry')
        self.pattern_comboentry.get_child().connect(
            'activate', self.on_find_in_files)
        self.pattern_comboentry.get_child().set_width_chars(24)
        self.setup_comboentry(self.pattern_comboentry)
        
        self.path_comboentry = self.widgets.get_object('path_comboentry')
        self.setup_comboentry(self.path_comboentry, self.CURRENT_FILE)
        self.update_comboentry(self.path_comboentry, self.CURRENT_FILE_DIR, False)
        self.update_comboentry(self.path_comboentry, self.FILE_BROWSER_ROOT, False)
        self.update_comboentry(self.path_comboentry, os.getcwd())
        
        self.file_comboentry = self.widgets.get_object('file_comboentry')
        self.setup_comboentry(self.file_comboentry, self.ANY_FILE)
        self.substitution_comboentry = self.widgets.get_object(
            'substitution_comboentry')
        self.setup_comboentry(self.substitution_comboentry)
        self.file_lines_view = self.widgets.get_object('file_lines_view')
        setup_file_lines_view(self.file_lines_view, self, 'Matches')

    def deactivate(self):
        """Clean up resources before deactivation."""
        panel = self.window.get_side_panel()
        panel.remove_item(self.find_panel)

    def setup_comboentry(self, comboentry, default=None):
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        liststore.set_sort_column_id(0, Gtk.SORT_ASCENDING)
        comboentry.set_model(liststore)
        comboentry.set_text_column(0)
        if default is not None:
            self.update_comboentry(comboentry, default)

    def update_comboentry(self, comboentry, text, set_active=True):
        """Update the match text combobox."""
        found_index = None
        for index, row in enumerate(iter(comboentry.get_model())):
            if row[0] == text:
                # The text is already in the list, does it need to be active?
                found_index = index
                break
        if found_index is not None and set_active:
            comboentry.set_active(found_index)
        elif found_index is None:
            comboentry.append_text(text)
            if set_active:
                self.update_comboentry(comboentry, text)

    @property
    def ui_callbacks(self):
        """The dict of callbacks for the ui widgets."""
        return {
            'on_find_in_files': self.on_find_in_files,
            'on_replace_in_files': self.on_replace_in_files,
            'on_save_results': self.on_save_results,
            }

    def show(self, data):
        """Show the finder pane."""
        panel = self.window.get_side_panel()
        panel.activate_item(self.find_panel)
        panel.props.visible = True

    def show_replace(self, data):
        """Show the finder pane and expand replace."""
        self.show(None)
        self.widgets.get_object('actions').activate()

    @property
    def path(self):
        """The base directory to traverse set by the user."""
        path_ = self.path_comboentry.get_active_text()
        self.update_comboentry(self.path_comboentry, path_)
        if path_ in (self.WORKING_DIRECTORY, '', None):
            path_ = '.'
        elif (path_ == self.CURRENT_FILE) or (path_ == self.CURRENT_FILE_DIR):
            document = self.active_document
            path_ = os.path.dirname(document.get_uri_for_display())
        elif path_ == self.FILE_BROWSER_ROOT:
            key = u'/apps/%s/plugins/filebrowser/on_load/virtual_root' % APP_KEY
            root_uri = gconf.client_get_default().get_string(key)
            path_ = gnomevfs.get_local_path_from_uri(root_uri)
        
        return path_

    @property
    def file_pattern(self):
        """The pattern to match the file name with."""
        pattern = self.file_comboentry.get_active_text()
        self.update_comboentry(self.file_comboentry, pattern)
        if pattern in (self.ANY_FILE, '', None):
            pattern = '.'
        if self.path_comboentry.get_active_text() == self.CURRENT_FILE:
            document = self.active_document
            pattern = os.path.basename(document.get_uri_for_display())
        return pattern

    @property
    def match_pattern(self):
        pattern = self.pattern_comboentry.get_active_text()
        self.update_comboentry(self.pattern_comboentry, pattern)
        return pattern

    def on_file_path_added(self, window, new_path):
        self.update_comboentry(
            self.path_comboentry, new_path, set_active=False)

    def get_find_params(self):
        """Return the find parameters as a tuple."""
        return find_params(
            os.path.abspath(self.path),
            self.match_pattern,
            self.widgets.get_object('re_checkbox').get_active(),
            self.widgets.get_object('match_case_checkbox').get_active(),
            self.file_pattern)

    def on_find_in_files(self, widget=None, substitution=None):
        """Find and present the matches."""
        treestore = self.file_lines_view.get_model()
        treestore.clear()
        find_params = self.get_find_params()
        self.last_find = find_params
        pattern = find_params.pattern
        self.file_lines_view.get_column(0).props.title = (
            'Matches for [%s]' % pattern)
        find_worker = FinderWorker(
            treestore, find_params, self.on_find_complete, substitution)
        find_worker.run()

    def on_find_complete(self):
        if self.path_comboentry.get_active_text() == self.CURRENT_FILE:
            self.file_lines_view.expand_all()

    def on_replace_in_files(self, widget=None):
        """Find, replace, and present the matches."""
        substitution = self.substitution_comboentry.get_active_text() or ''
        self.update_comboentry(self.substitution_comboentry, substitution)
        response = Gtk.RESPONSE_ACCEPT
        find_params = self.get_find_params()
        if self.last_find != find_params:
            dialog = Gtk.Dialog(
                title="Untested replacement", parent=self.window,
                flags=Gtk.DIALOG_MODAL | Gtk.DIALOG_DESTROY_WITH_PARENT,
                buttons=(Gtk.STOCK_FIND, Gtk.RESPONSE_REJECT,
                         Gtk.STOCK_FIND_AND_REPLACE, Gtk.RESPONSE_ACCEPT))
            question = Gtk.Label(
                _("Do want to test this replacement using Find first?"))
            question.set_alignment(0, 0)
            question.props.xpad = 6
            dialog.vbox.pack_start(question, expand=False, padding=6)
            question.show()
            params_summary = Gtk.Label()
            params_summary.set_markup(_(
                "<b>Look in:</b> %s\n"
                "<b>Search for:</b> %s\n"
                "<b>Regular expression:</b> %s\n"
                "<b>Match case:</b> %s\n"
                "<b>File name pattern:</b> %s")
                % find_params)
            params_summary.props.selectable = True
            params_summary.props.xpad = 3
            params_summary.props.ypad = 3
            box = Gtk.EventBox()
            box.set_border_width(6)
            box.modify_bg(Gtk.STATE_NORMAL, Gtk.gdk.Color('#fff'))
            box.add(params_summary)
            dialog.vbox.pack_start(box)
            box.show()
            params_summary.show()
            response = dialog.run()
            dialog.destroy()
        if response == Gtk.RESPONSE_REJECT:
            self.on_find_in_files()
        elif response == Gtk.RESPONSE_ACCEPT:
            self.on_find_in_files(substitution=substitution)

    def on_save_results(self, widget=None):
        """Save the search results to a file."""
        dialog = Gtk.FileChooserDialog(
            title="Save find results", parent=self.window,
            action=Gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.RESPONSE_CANCEL,
                     Gtk.STOCK_SAVE, Gtk.RESPONSE_ACCEPT))
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name('_find.log')
        if (dialog.run() == Gtk.RESPONSE_ACCEPT):
            file_name = dialog.get_filename()
            log_text = self.get_results_as_log()
            with open(file_name, 'w') as log_file:
                log_file.write(log_text)
        dialog.destroy()

    def get_results_as_log(self):
        """Return the results in the file_lines_view as a log."""
        lines = []
        treestore = self.file_lines_view.get_model()
        for file_match in treestore:
            lines.append(file_match[0])
            for line_match in file_match.iterchildren():
                line = '    %4s: %s' % (line_match[2], line_match[3])
                lines.append(line)
        return '\n'.join(lines)


def get_option_parser():
    """Return the option parser for this program."""
    usage = "usage: %prog [options] root_dir file_pattern match"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-s", "--substitution", dest="substitution",
        help="The substitution string (may contain \\[0-9] match groups).")
    parser.set_defaults(substitution=None)
    return parser


def main(argv=None):
    """Run the command line operations."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, args) = parser.parse_args(args=argv[1:])

    root_dir = args[0]
    file_pattern = args[1]
    match_pattern = args[2]
    substitution = options.substitution
    print "Looking for [%s] in files like %s under %s:" % (
        match_pattern, file_pattern, root_dir)
    for summary in find_matches(
        root_dir, file_pattern, match_pattern, substitution=substitution):
        print "\n%(file_path)s" % summary
        for line in summary['lines']:
            print "    %(lineno)4s: %(text)s" % line


if __name__ == '__main__':
    sys.exit(main())
