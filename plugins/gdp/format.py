# Copyright (C) 2009-2012 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""Format text and code"""

__all__ = [
    'Formatter',
    ]

from gettext import gettext as _
import os
import re
from tempfile import NamedTemporaryFile
from textwrap import wrap
import threading

from gi.repository import (
    Gio,
    GObject,
    Gtk,
    )

from pocketlint.formatdoctest import DoctestReviewer
from pocketlint.formatcheck import (
    Language,
    Reporter,
    UniversalChecker,
    )

from gdp import (
    config,
    ControllerMixin,
    setup_file_lines_view,
    )


class FilteredReporter(Reporter):
    """A class that can report only errors."""

    @property
    def error_only(self):
        return config.getboolean('formatter', 'report_only_errors')

    @error_only.setter
    def error_only(self, val):
        # Suppress the set behaviour because the config controls the rules.
        pass

    def _message_file_lines(self, line_no, message, icon=None,
                            base_dir=None, file_name=None):
        """Queue the messages in the file_lines_view."""
        if self.piter is None:
            mime_type = 'gnome-mime-text'
            # Do not queue this call because the piter must be known now
            # for all subsequent appends to work.
            self.piter = self.treestore.append(
                None, (file_name, mime_type, 0, None, base_dir))
        self.idle_append_issue(
            self.piter, file_name, icon, line_no, message, base_dir)

    def append_issue(self, piter, file_path, icon, lineno, text, path):
        self.treestore.append(piter, (file_path, icon, lineno, text, path))
        return False

    def idle_append_issue(self, piter, file_path, icon, lineno, text, path):
        GObject.idle_add(
            self.append_issue, piter, file_path, icon, lineno, text, path)


class CheckerWorker(threading.Thread):

    def __init__(self, documents, reporter, callback, quiet):
        super(CheckerWorker, self).__init__()
        self.documents = documents
        self.reporter = reporter
        self.callback = callback
        self.quiet = quiet
        self.model = self.reporter.file_lines_view.get_model()

    def _ensure_file_path(self, checker):
        if os.path.isfile(checker.file_path):
            return None
        temp_file = NamedTemporaryFile(suffix='gdp', delete=False)
        temp_file.write(checker.text)
        temp_file.flush()
        checker.file_path = temp_file.name
        return temp_file

    def start(self):
        super(CheckerWorker, self).start()
        return False

    def run(self):
        for document in self.documents:
            file_path = document.get_uri_for_display()
            text = document.props.text
            language = Language.get_language(file_path)
            self.reporter.piter = None
            checker = UniversalChecker(
                file_path, text=text, language=language,
                reporter=self.reporter)
            temp_file = self._ensure_file_path(checker)
            try:
                checker.check()
            finally:
                if temp_file:
                    temp_file.unlink(temp_file.name)
        self.callback(self.quiet)


class Formatter(ControllerMixin):
    """Format Gedit Document and selection text."""

    def __init__(self, window):
        self.window = window
        # The replace in text uses the replace dialog.
        widgets = Gtk.Builder()
        widgets.add_from_file(
            '%s/format.ui' % os.path.dirname(__file__))
        widgets.connect_signals(self.ui_callbacks)
        self.replace_dialog = widgets.get_object('replace_dialog')
        self.replace_label = widgets.get_object('replace_label')
        self.replace_label_text = self.replace_label.get_text()
        self.replace_pattern_entry = widgets.get_object(
            'replace_pattern_entry')
        self.replace_replacement_entry = widgets.get_object(
            'replace_replacement_entry')
        self._bounds = None
        self._text = None
        # Syntax and style reporting use the panel.
        other_widgets = Gtk.Builder()
        other_widgets.add_from_file(
            '%s/format.ui' % os.path.dirname(__file__))
        self.file_lines = other_widgets.get_object(
            'file_lines_scrolledwindow')
        self.file_lines_view = other_widgets.get_object('file_lines_view')
        setup_file_lines_view(self.file_lines_view, self, 'Problems')
        panel = window.get_side_panel()
        icon = Gtk.Image.new_from_stock(Gtk.STOCK_INFO, Gtk.IconSize.MENU)
        panel.add_item(
            self.file_lines, 'gdpformat', 'Check syntax and style', icon)
        self.reporter = FilteredReporter(
            Reporter.FILE_LINES, treeview=self.file_lines_view)
        self.checker_id = None
        self.checker_worker = None

    def deactivate(self):
        """Clean up resources before deactivation."""
        panel = self.window.get_side_panel()
        panel.remove_item(self.file_lines)

    @property
    def ui_callbacks(self):
        """The dict of callbacks for the ui widgets."""
        return {
            'on_replace_quit': self.on_replace_quit,
            'on_replace': self.on_replace,
            }

    def _get_bounded_text(self):
        """Return tuple of the bounds and formattable text.

        The bounds mark either the selection or the document.
        """
        document = self.active_document
        if document.props.has_selection:
            bounds = document.get_selection_bounds()
        else:
            bounds = (document.get_start_iter(), document.get_end_iter())
        text = document.get_text(bounds[0], bounds[1], True)
        return bounds, text

    def _put_bounded_text(self, bounds, text):
        """Replace the current text between the bounds with the new text.

        This change is undoable.
        """
        document = self.active_document
        document.begin_user_action()
        document.place_cursor(bounds[0])
        document.delete(*bounds)
        document.insert_at_cursor(text)
        document.end_user_action()

    def _single_line(self, text):
        """Return the text as a single line.."""
        lines = [line.strip() for line in text.splitlines()]
        return ' '.join(lines)

    def single_line(self, action):
        """Format the text as a single line."""
        bounds, text = self._get_bounded_text()
        text = self._single_line(text)
        self._put_bounded_text(bounds, text)

    def newline_ending(self, action):
        """Fix the selection's line endings."""
        bounds, text = self._get_bounded_text()
        lines = [line.rstrip() for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def get_tab_size(self):
        tab_size = 4
        try:
            settings_schema = 'org.gnome.gedit.preferences.editor'
            settings = Gio.Settings.new(settings_schema)
            tab_size = settings.get_uint('tabs-size')
        except:
            pass
        return tab_size

    def tabs_to_spaces(self, action):
        """Fix the selection's line endings."""
        tab_size = self.get_tab_size()
        bounds, text = self._get_bounded_text()
        tab_spaces = ' ' * tab_size
        lines = [line.replace('\t', tab_spaces) for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def quote_lines(self, action):
        """Quote the selected text passage."""
        bounds, text = self._get_bounded_text()
        lines = ['> %s' % line for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def sort_imports(self, action):
        """Sort python imports."""
        bounds, text = self._get_bounded_text()
        padding = self._get_padding(text)
        line = self._single_line(text)
        imports = line.split(', ')
        imports = sorted(imports, key=str.lower)
        imports = [imp.strip() for imp in imports if imp != '']
        text = self._wrap_text(', '.join(imports), padding=padding)
        self._put_bounded_text(bounds, text)

    def wrap_selection_list(self, action):
        """Wrap long lines and preserve indentation."""
        # This should use the textwrap module.
        paras = []
        indent_re = re.compile('^( +[0-9*-]*\.*)')
        bounds, text = self._get_bounded_text()
        for line in text.splitlines():
            match = indent_re.match(line)
            if match is not None:
                symbol = match.group(1)
                # When there is not symbol in the indent, remove a space
                # because a space is automatically added for the symbol.
                if not symbol.replace(' ', ''):
                    symbol = symbol[0:-1]
            else:
                symbol = ''
            padding_size = len(symbol)
            padding = ' ' * padding_size
            run = 72 - padding_size
            new_lines = []
            new_line = [symbol]
            new_length = padding_size
            # ignore the symbol
            words = line.split()
            for word in words[1:]:
                # The space between the words is 1
                if new_length + 1 + len(word) > run:
                    new_lines.append(' '.join(new_line))
                    new_line = [padding]
                    new_length = padding_size
                new_line.append(word)
                new_length += 1 + len(word)
            new_lines.append(' '.join(new_line))
            paras.extend(new_lines)
        self._put_bounded_text(bounds, '\n'.join(paras))

    def _get_padding(self, text):
        """Return the leading whitespace.

        Return '' if there is not leading whitespace.
        """
        leading_re = re.compile(r'^(\s+)')
        match = leading_re.match(text)
        if match:
            return match.group(1)
        else:
            return ''

    def _wrap_text(self, text, width=78, padding=None):
        """Wrap long lines."""
        if padding is None:
            padding = self._get_padding(text)
        line = self._single_line(text)
        lines = wrap(
            line, width=width, initial_indent=padding,
            subsequent_indent=padding, break_on_hyphens=False)
        paragraph = '\n'.join(lines)
        return paragraph

    def rewrap_text(self, action):
        """Rewrap the paragraph."""
        bounds, text = self._get_bounded_text()
        width = 78
        file_path = self.active_document.get_uri_for_display()
        language = Language.get_language(file_path)
        if language in (Language.TEXT, None):
            width = 72
        text = self._wrap_text(text, width=width)
        self._put_bounded_text(bounds, text)

    def reformat_css(self, action):
        """Reformat the CSS."""
        bounds, text = self._get_bounded_text()
        # Break the text into rules using the trailing brace; the last item
        # is not css.
        rules = text.split('}')
        trailing_text = rules.pop().strip()
        css = []
        for rule in rules:
            rule = rule.strip()
            selectors, properties = rule.split('{')
            css.append('%s {' % selectors.strip())
            for prop in properties.split(';'):
                if not prop:
                    # We always check after the last semicolon because it is
                    # a common mistake to forget it on the last property.
                    # This loop fixes the syntax if there is remaining text.
                    break
                prop = ': '.join(
                    [part.strip() for part in prop.split(':')])
                css.append('    %s;' % prop)
            css.append('    }')
        if trailing_text:
            # This could be a comment.
            css.append(trailing_text)
        self._put_bounded_text(bounds, '\n'.join(css))

    def re_replace(self, action):
        """Replace each line using an re pattern."""
        self._bounds, self._text = self._get_bounded_text()
        self.replace_dialog.show()
        self.replace_dialog.run()

    def on_replace_quit(self, widget=None):
        """End the replacement, hide he dialog."""
        self._bounds = None
        self._text = None
        self.replace_dialog.hide()

    def on_replace(self, widget=None):
        """replace each line of text."""
        pattern = self.replace_pattern_entry.get_text()
        replacement = self.replace_replacement_entry.get_text()
        try:
            line_re = re.compile(pattern)
        except re.error:
            # Show a message that the pattern failed.
            message = _("The regular expression pattern has an error in it.")
            self.replace_label.set_markup(
                '%s\n<b>%s</b>' % (self.replace_label_text, message))
            return
        lines = [
            line_re.sub(replacement, line)
            for line in self._text.splitlines()]
        self._put_bounded_text(self._bounds, '\n'.join(lines))
        self.on_replace_quit()

    def show(self):
        """Show the finder pane."""
        panel = self.window.get_side_panel()
        panel.activate_item(self.file_lines)
        panel.props.visible = True

    def reformat_doctest(self, action):
        """Reformat the doctest."""
        bounds, text = self._get_bounded_text()
        file_name = self.active_document.get_uri_for_display()
        reviewer = DoctestReviewer(file_name, text)
        new_text = reviewer.format()
        self._put_bounded_text(bounds, new_text)

    def check_style(self, action, documents=None, quiet=False):
        """Check the style and syntax of the active document."""
        if self.checker_id is not None:
            return
        if self.checker_worker is not None and self.checker_worker.is_alive():
            # This is not as reliable to Gtk's idle handle. Maybe this
            # sould call join() to wait tot the process to terminate.
            return
        self.file_lines_view.get_model().clear()
        if documents is None:
            documents = [self.active_document]
        self.checker_worker = CheckerWorker(
            documents, self.reporter, self.on_check_style_complete, quiet)
        # Queue the find worker after the events emited at the top
        # of this method.
        self.checker_id = GObject.idle_add(self.checker_worker.start)

    def on_check_style_complete(self, quiet):
        # Gracefully end the operation in the main_loop.
        GObject.idle_add(self.do_check_style_complete, quiet)

    def do_check_style_complete(self, quiet):
        self.checker_worker = None
        self.checker_id = None
        model = self.file_lines_view.get_model()
        first = model.get_iter_first()
        if first is None:
            # Noted that the mesage is in the file_path position.
            model.append(
                None, ('No problems found', 'emblem-default', 0, None, None))
        self.file_lines_view.expand_all()
        if first is not None or not quiet:
            self.show()
        return False

    def check_style_background(self, action, documents=None):
        """Check the style in the background."""
        self.check_style(action, quiet=True)

    def check_all_style(self, action):
        """Check the style and syntax of all open documents."""
        self.check_style(None, documents=self.window.get_documents())

    def on_show_syntax_errors_only_toggled(self, menu_item, data=None):
        config.set(
            'formatter', 'report_only_errors', str(menu_item.props.active))
        config.dump()
