# -*- coding: utf-8 -*-

#  Gedit pylint plugin
#
#  Copyright © 2008, 2010-2011  B. Clausius <barcc@gmx.de>
#  Copyright © 2007-2008  P. Henrique Silva <ph.silva@gmail.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

#    Contributor(s):
#        Francisco J. Jordano Jimenez <arcturus@ardeenelinfierno.com>
#
#    pylint results parser based on code by Christopher Lenz
#    Copyright © 2005  Christopher Lenz
#

import gtk
import pango
import gio

import subprocess
import os.path
import tempfile
import time
import re

import config


PYTHON_MIME_TYPE = 'text/x-python'
PYTHON_LANG_NAME = 'Python'


class PylintResultsModel (gtk.ListStore):

    def __init__ (self):
        super(PylintResultsModel, self).__init__ (str, int, str, str)

    def add (self, msg):
        self.append ([msg.stock_id, msg.lineno, msg.message, msg.msg_type])

class PylintResultsView (gtk.TreeView):

    def __init__ (self, panel):
        super (PylintResultsView, self).__init__ ()

        self._panel = panel

        icon = gtk.TreeViewColumn ("Type")
        icon_cell = gtk.CellRendererPixbuf ()
        icon.pack_start (icon_cell)
        icon.add_attribute (icon_cell, 'stock-id', 0)
        icon.set_sort_column_id (0)
        self.append_column (icon)

        linha = gtk.TreeViewColumn ("Line")
        linha_cell = gtk.CellRendererText ()
        linha.pack_start (linha_cell)
        linha.add_attribute (linha_cell, 'text', 1)
        linha.set_sort_column_id (1)
        self.append_column (linha)

        msgtype = gtk.TreeViewColumn ("Number")
        msgtype_cell = gtk.CellRendererText ()
        msgtype.pack_start (msgtype_cell)
        msgtype.add_attribute (msgtype_cell, 'text', 3)
        msgtype.set_sort_column_id (3)
        self.append_column (msgtype)

        msg = gtk.TreeViewColumn ("Message")
        msg_cell = gtk.CellRendererText ()
        msg.pack_start (msg_cell)
        msg.add_attribute (msg_cell, 'text', 2)
        msg.set_sort_column_id (2)
        self.append_column (msg)

        self.connect ("row-activated", self._row_activated_cb)

    def _row_activated_cb (self, view, row, column):

        model = view.get_model ()
        iter = model.get_iter (row)

        window = self._panel.get_window ()

        doc = window.get_active_document ()
        line = model.get_value (iter, 1) - 1
        doc.goto_line (line)

        view = window.get_active_view ()

        text_iter = doc.get_iter_at_line (line)
        view.scroll_to_iter (text_iter, 0.25)
        view.grab_focus()

class PylintResultsPanel (gtk.Viewport):
    
    _ui_file = os.path.join(os.path.dirname(__file__) ,'gedit_pylint.ui')

    def __init__ (self, instance, window):

        super(PylintResultsPanel, self).__init__ ()

        self._window = window
        self._instance = instance
        
        builder = gtk.Builder()
        builder.add_from_file(self._ui_file)
        builder.connect_signals(self)
        widget = builder.get_object("hbox_panel")
        scrolledwindow = builder.get_object("scrolledwindow_results")
        self.checkbutton_highlight = builder.get_object("checkbutton_highlight")
        
        self._view = PylintResultsView (self)
        
        scrolledwindow.add (self._view)
        self.add (widget)
        self._view.show ()
        widget.show ()

    def set_model (self, model):
        self._view.set_model (model)

    def get_window (self):
        return self._window

    def on_button_check_clicked(self, *args):
        self._instance.on_action_pylint_activate(None)

    def on_checkbutton_highlight_toggled(self, button):
        doc = self._window.get_active_document ()
        if button.get_active():
            self._instance._hightlight_errors (self._instance._errors[doc])
        else:
            self._instance._remove_tags (doc)
    
    def on_button_config_clicked(self, *args):
        dialog = self._instance._plugin.config.create_dialog()
        dialog.run()

class PylintMessage (object):

    def __init__ (self, doc, msg_type, category, lineno, message, method, tag):

        self._doc = doc

        self._msg_type = msg_type
        self._category = category
        
        self._lineno = lineno
        self._message = message

        self._method = method
        self._tag    = tag

        self._start_iter = None
        self._end_iter   = None

        self._stock_id = self._get_stock_id (category)

    def _get_stock_id (self, category):

        if category == "error":
            return gtk.STOCK_DIALOG_ERROR
        
        elif category == "warning":
            return gtk.STOCK_DIALOG_WARNING

        elif category in ["convention", "refactor"]:
            return gtk.STOCK_DIALOG_INFO

        else:
            return gtk.STOCK_DIALOG_INFO

    def setWordBounds (self, start, end):
        self._start_iter = start
        self._end_iter = end

    doc     = property (lambda self: self.__doc)

    msg_type= property (lambda self: self._msg_type)
    category= property (lambda self: self._category)

    lineno  = property (lambda self: self._lineno)
    message = property (lambda self: self._message)

    method  = property (lambda self: self._method)
    tag    = property (lambda self: self._tag)

    start  = property (lambda self: self._start_iter)
    end    = property (lambda self: self._end_iter)

    stock_id = property (lambda self: self._stock_id)
    
class PylintInstance (object):

    def __init__ (self, plugin, window):
        self._plugin = plugin
        self._window = window

        self._merge_id = None
        self._action_group = None

        self._panel = None

        self._results = {None: PylintResultsModel()}
        self._errors  = {}

        self._word_error_tags = {}
        self._line_error_tags = {}

        self._status_id = 98

        self._insert_panel ()
        self._insert_menu ()

        self._attach_events ()

    def deactivate (self):

        self._remove_menu ()
        self._remove_panel ()

        # "destroy objects"
        self._merge_id = None
        self._action_group = None

        self._panel = None
        self._results = {}

        self._merge_id = None
        self._action_group = None

        self._panel = None

        self._results = {}
        self._errors  = {}

        for doc in self._window.get_documents():
            self._remove_tags (doc)

        self._word_error_tags = {}
        self._line_error_tags = {}

        self._window = None
        self._plugin = None

    def update_ui (self):

        doc = self._window.get_active_document()
        
        self._action_group.set_sensitive(doc != None)

        if doc in self._results:
            self._panel.set_model (self._results[doc])
        else:
            self._panel.set_model (self._results[None])

    def _insert_panel (self):

        self._panel = PylintResultsPanel (self, self._window)

        image = gtk.Image()
        image.set_from_icon_name('gnome-mime-text-x-python',
                                 gtk.ICON_SIZE_MENU)

        bottom_panel = self._window.get_bottom_panel()
        bottom_panel.add_item(self._panel, 'Pylint Results', image)

    def _remove_panel (self):

        bottom_panel = self._window.get_bottom_panel()
        bottom_panel.remove_item(self._panel)

    def _insert_menu (self):
        manager = self._window.get_ui_manager()

        self._action_group = gtk.ActionGroup("GeditPylintPluginActions")
        self._action_group.set_translation_domain('pylint')
        self._action_group.add_actions([('Pylint', None,
                                         _('Pylint'),
                                         None,
                                         _('Run Pylint for the current document'),
                                         self.on_action_pylint_activate)])
        
        manager.insert_action_group(self._action_group, -1)

        ui_str = """<ui>
                    <menubar name="MenuBar">
                     <menu name="ToolsMenu" action="Tools">
                      <placeholder name="ToolsOps_2">
                        <menuitem name="Pylint" action="Pylint"/>
                       </placeholder>
                      </menu>
                     </menubar>
                    </ui>"""

        self._merge_id = manager.add_ui_from_string(ui_str)

    def _remove_menu (self):
        manager = self._window.get_ui_manager ()
        manager.remove_ui (self._merge_id)
        manager.remove_action_group (self._action_group)
        manager.ensure_update ()

    def _add_tags (self, doc):

        self._word_error_tags[doc] = doc.create_tag ("pylint-word-error",
                                                     underline = pango.UNDERLINE_ERROR)
        
        self._line_error_tags[doc] = doc.create_tag ("pylint-line-error",
                                                     background =  self._plugin.config.color_highlight)


    def _remove_tags (self, doc):

        if self._word_error_tags.has_key (doc):
            start, end = doc.get_bounds ()
            doc.remove_tag (self._word_error_tags[doc], start, end)
            doc.remove_tag (self._line_error_tags[doc], start, end)

    def _attach_events (self):
        self._window.connect ("tab_added", self.on_tab_added)
        self._window.connect ("tab_removed", self.on_tab_removed)

    def on_tab_added (self, window, tab):

        doc = tab.get_document ()

        self._errors[doc] = []

        # add tags to document
        self._add_tags (doc)

    def on_tab_removed (self, window, tab):

        doc = tab.get_document()
        if self._results.has_key(doc):
            self._results[doc] = None
            del self._results[doc]

            self._errors[doc] = None
            del self._errors[doc]

            self._remove_tags (doc)
            
    def on_action_pylint_activate(self, action):

        doc = self._window.get_active_document ()

        # only run on Python documents (not perfect, maybe use mime type too)
        if not self._is_python_document(doc):

            # flash_message is only avaiable on gedit >= 2.17.5
            status = self._window.get_statusbar ()
            try:
                status.flash_message (self._status_id, "%s is not a Python file." % doc.get_uri_for_display ())
            except AttributeError:
                print "%s is not a Python file." % doc.get_uri_for_display ()
        
            return
        
        # Check for pylint version
        if not self._check_pylint_version():
            # same as above
            status = self._window.get_statusbar()
            try:
                status.flash_message (self._status_id, "Incorrect pylint version, " \
                                      "you need at least 0.12.2 version or newer.")
            except AttributeError:
                print "Incorrect pylint version, you need at least " \
		      "0.12.2 version or newer."
            
            return

        in_filename = None
        if not doc.get_modified():
            in_filename = gio.File(uri=doc.get_uri() or '').get_path()
            in_tmpFile = None
        if in_filename is None:
            # get iters and text
            start, end = doc.get_bounds ()

            text = doc.get_text (start, end)

            # save to a temporary
            in_tmpFile = tempfile.NamedTemporaryFile ("w+", suffix="-gedit-pylint")
            in_tmpFile.write (text)
            in_tmpFile.flush ()
            in_filename = in_tmpFile.name

        # build cmdline
        cmdline = ("pylint", "--include-ids=y", "--reports=no", "--output-format=parseable",
                  in_filename)

        # run and capture output
        out_tmpFile = tempfile.NamedTemporaryFile ("w+", suffix=".gedit-pylint")

        # run pylint from the parentdir of the package, so that pylint can find modules there
        cwd = os.path.dirname(doc.get_uri_for_display())
        while os.path.exists(os.path.join(cwd,'__init__.py')):
            cwd = os.path.dirname(cwd)
        
        #print 'run:', cmdline
        process = subprocess.Popen (cmdline,
                                    stdout=out_tmpFile,
                                    stderr=open('/dev/null', "w"),
                                    cwd=cwd)

        process.wait ()

        # cleanup previous run errors
        self._remove_tags (doc)
        if doc not in self._results:
            self._results[doc] = PylintResultsModel ()
            self._panel.set_model (self._results[doc])
        self._results[doc].clear ()
        
        self._panel.checkbutton_highlight.set_active(True)

        # display results
        errors, err_lines = self._check_return (out_tmpFile)

        if errors:
            self._errors[doc] = self._parse_errors (err_lines)
            self._hightlight_errors (self._errors[doc])
            self._add_to_results (self._errors[doc])

        else:
            # no errors, just display a sucess message

            # flash message is only avaiable will be on gedit CVS as soon as my patch got accepted
            status = self._window.get_statusbar ()

            try:
                status.flash_message (self._status_id, "No errors found on %s." % doc.get_uri_for_display ())
            except AttributeError:
                print "No errors found on %s." % doc.get_uri_for_display ()
            

        # remove temp files
        if in_tmpFile:
            in_tmpFile.close()
        out_tmpFile.close()

    def _check_return (self, out):
        out.flush ()
        out.seek (0)

        contents = out.readlines()

        return True, contents

    def _parse_errors (self, err_lines):
        errors = []
        msg_re = re.compile(r'^(?P<file>.+):(?P<line>\d+): '
                            r'\[(?P<type>[A-Z]\d*)(?:, (?P<method>[^\]]+))?\] '
                            r'(?P<msg>.*)$')
        msg_categories = dict(W='warning', E='error', C='convention', R='refactor')

        #print 'pylint output:'
        for line in err_lines:
            match = msg_re.search(line)

            if match:
                msg_type = match.group('type')
                category = msg_categories.get(msg_type[0])

                if len(msg_type) == 1:
                    msg_type = None

                lineno = int(match.group('line'))
                method = match.group('method')
                msg = match.group('msg') or ''
                tag = self._parse_tag (msg_type, msg)
            else:
                msg_type = None #'E0'
                category = 'error'
                lineno = 1
                method = 'None'
                msg = 'plugin failed to parse pylint-error: '+line.rstrip()
                tag = ''
                print '--- plugin failed to parse pylint-error ---'
                print line.rstrip()
            
            if msg_type is not None:
                errors.append(PylintMessage(self._window.get_active_document,
                                            msg_type,
                                            category,
                                            lineno,
                                            msg,
                                            method,
                                            tag or ''))

        #print 'pylint found %d errors' % len(errors)
        return errors

    def _hightlight_errors (self, errors):

        doc = self._window.get_active_document ()

        for err in errors:

            if err.category != "error":
                continue

            start = doc.get_iter_at_line (err.lineno - 1)
 
            end = doc.get_iter_at_line (err.lineno - 1)
            end.forward_to_line_end ()

            # apply tag to word, if any
            if err.tag:
                try:
                    match_start, match_end = start.forward_search (err.tag,
                                                               gtk.TEXT_SEARCH_TEXT_ONLY,
                                                               end)
                    if self._plugin.config.word_errors:
                        doc.apply_tag (self._word_error_tags[doc], match_start, match_end)
                except TypeError:
                    pass

            # apply tag to entire line
            if self._plugin.config.line_errors:
                doc.apply_tag (self._line_error_tags[doc], start, end)
                

    def _add_to_results (self, errors):

        doc = self._window.get_active_document ()

        for err in errors:
            self._results[doc].add (err)

    def _parse_tag (self, msg_type, msg):

        tag = ''

        if msg_type == "E0602":
            tag = msg[msg.find("'")+1: msg.rfind("'")]

        return tag
    
    def _check_pylint_version(self):
        """
            Check the version of pylint, some packages versions
            of pylint (ubuntu 6.10 for example) are too old
            and not include the --output-format option.
        """
        # run and capture output
        version_tmpFile = tempfile.NamedTemporaryFile ("w+", suffix=".gedit-pylint-version")
        cmd = "pylint --version"
        reg_exp = re.compile('\d+')
        
        #Version definition:
        _VERSION_ = ['0', '12', '2'] #version, mayor and minor

        try:
            process = subprocess.Popen (cmd.split(" "),
                                        stdout=version_tmpFile,
                                        stderr=open('/dev/null', "w"),
                                        cwd=tempfile.gettempdir())

            process.wait ()
        except OSError, e:
            return False
        
        #Parse the output
        version_tmpFile.flush ()
        version_tmpFile.seek (0)
        
        contents = version_tmpFile.readlines()

        # check return code, if 2, --version option doesn't exists.
        # maybe you are using an older logilab-common package ( < 0.21.1)
        # which have a bug and don't added a --version option to pylint
        # see logilab bug #3197 (http://www.logilab.org/view?rql=Any%20X%20WHERE%20X%20eid%203471)

        if process.returncode == 2:
            print "Pylint doesn have a --version option. Chek your logilab-common version. " \
                  "See logilab.org bug #3197 for more information."

            return False

        if len(contents) >= 1:
            
            for line in contents:
                #Search for the line with the version info
                if line.find("pylint ") >= 0:
                    #Retrieve the version numbers
                    version = reg_exp.findall(line)
                    
                    #Check for versions
                    if version >= _VERSION_ :
                        return True
                    else:
                        return False

            return False            

        else:

            return False
        
        
        version_tmpFile.close()

    def _is_python_document (self, doc):

        if not doc.get_language(): return False

        if doc.get_language().get_name() == PYTHON_LANG_NAME:
            return True

        if not doc.get_mime_type(): return False

        if doc.get_mime_type() == PYTHON_MIME_TYPE:
            return True

        # ok, there's nothing more to do
        return False



    
    
