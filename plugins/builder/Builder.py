#    builder main class
#    Copyright (C) 2009 Mike Reed <gedit@amadron.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import gtk
import gtksourceview2
try:
    import gedit
    import gnomevfs
except:
    import pluma as gedit
    import matevfs as gnomevfs

import string
import sys
import re
import traceback
import gobject
import pango
import subprocess
import gobject
import logging
import os
import os.path

from Output import Output

__all__ = ('Output')

ui_str = """<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="BuilderOps">
        <separator/>
        <menuitem action="plugin_builder_compile"/>
        <menuitem action="plugin_builder_build"/>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""

class Builder:
    _READY = 0
    _SAVING = 1
    _EXECUTE = 2
    
    def __init__(self, config, window):
        self._l = logging.getLogger("plugin.builder")
        self._l.debug("Entered")
        self._window = window
        self._config = config
        # Store last build/compile command run for each document
        # during this session
        self._prev_commands = {} 
        
        # Map to record location of items found in the Output buffer
        # _item_locations[item number] ->
        #     if file loaded : a GtkTextBuffer mark
        #     else: a tuple of (path, line, col)
        self._item_locations = {}
        
        ui_builder = gtk.Builder()
        ui_builder.add_from_file(os.path.join(config.get_data_dir(), 'Builder.glade'))
        self._ui = ui_builder.get_object
        self._ui('dlg_unsaved_file').set_transient_for(window)
        self._ui('dlg_run_command').set_transient_for(window)
        
        # Add bottom panel console
        self._console = Output(config);
        self._console.set_item_selected_cb(self._goto)
        self._console.set_item_found_cb(self._record)
        bottom = self._window.get_bottom_panel()
        bottom.add_item(self._console.widget(), _('Build Output'), gtk.STOCK_EXECUTE)

        # Insert menu item Tools->Compile
        manager = self._window.get_ui_manager()
        self._action_group = gtk.ActionGroup("plugin_builder")
        self._action_group.add_actions([("plugin_builder_compile", None,
                                            _("_Compile"), "<control>F5",
                                            _("Compile the current document"),
                                            self._compile_doc),
                                        ("plugin_builder_build", None,
                                            _("_Build"), "<control>F6",
                                            _("Run the build command"),
                                            self._build)])
        manager.insert_action_group(self._action_group, -1)
        self._ui_id = manager.add_ui_from_string(ui_str)
        self._l.info(manager.get_ui())
        self._save_action = manager.get_action('/ui/MenuBar/FileMenu/FileSaveMenu')
        self._l.info(self._save_action)
        
    def deactivate(self):
        self._l.debug("Entered")
        
        # Remove menu item Tools->Compile File
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        manager.remove_action_group(self._action_group)
        manager.ensure_update()
        
        # Remove bottom panel console
        bottom = self._window.get_bottom_panel()
        bottom.remove_item(self._console.widget())
        
        # Tidy up
        self._window = None
        self._config = None
        self._action_group = None
        
    def _compile_doc(self, action):
        self._l.debug("Entered")
        rootdir = None
        doc = self._window.get_active_document()
        if doc:
            rootdir = os.path.dirname(doc.get_uri_for_display())
        self._generate_output(self._config.compile_cmd, rootdir)
        
        
    def _build(self, action):
        self._l.debug("Entered")
        rootdir = None
        doc = self._window.get_active_document()
        rootdir = self._config.build_root(doc)
        self._generate_output(self._config.build_cmd, rootdir)


    def _generate_output(self, get_cmd_func, rootdir):
        self._l.debug("Entered")
        bp = self._window.get_bottom_panel()
        bp.activate_item(self._console.widget())
        bp.set_property("visible", True)
        doc = self._window.get_active_document()
        active_tab = self._window.get_active_tab()
        
        unsaved = self._window.get_unsaved_documents()
        self._l.info("There are %d unsaved documents" % len(unsaved))
        self._doc_handler_ids = {}
        self._state = self._EXECUTE
        if unsaved:
            self._state = self._SAVING
            md = self._ui('dlg_unsaved_file')
            resp = 0
            for us_doc in unsaved:
                self._l.info('Makeing %s active' % us_doc.get_uri_for_display())
                tab = self._window.get_tab_from_uri(us_doc.get_uri())
                # Make doc the active doc because the only reliable way to save
                # a document is to activate the save action attached to the File
                # menu which, of course, works on the active document.  Plus it 
                # is always good to show the doc you are asking if they want to
                # save.
                self._window.set_active_tab(tab)
                if resp != 3: # yes_to_all
                    md.format_secondary_text(us_doc.get_uri_for_display())
                    resp = md.run()
                    self._l.debug("User responded with %d" % resp)
                if resp == 1 or resp == 3: # yes OR yes_to_all
                    self._doc_handler_ids[us_doc] = us_doc.connect(
                        'saved', self._execute_command, get_cmd_func, rootdir, doc)
                    #us_doc.save(0)  generates critical errors
                    self._l.info('Saving active doc')
                    self._save_action.activate()
                elif resp == 2: # no
                    self._l.info('Not saving %s' % us_doc.get_uri_for_display())
                    pass
                elif resp == 4: # no_to_all
                    self._l.info('No more docs to save before compile/build')
                    break
                else: # cancel (or closed)
                    self._l.info('User canceled compile/build')
                    self._state = self._READY
                    break
            
            self._window.set_active_tab(active_tab)
            md.hide()
            if self._state == self._SAVING:  
                self._state = self._EXECUTE
                if len(self._doc_handler_ids) == 0:
                    self._execute_command(doc, None, get_cmd_func, rootdir, doc)
        else:   
            self._execute_command(doc, None, get_cmd_func, rootdir, doc)
        
    
    def _execute_command(self, us_doc, arg1, get_cmd_func, rootdir, doc):
        """ Executes the compile or build command once all documents have been saved.
            doc - the active documents when the build/compile was initiated
            get_cmd_func - returns the build or compile command
            rootdir - for compile this is the doc dir, for build it comes from config
        """
        self._l.debug('Entered')
        
        # First check that all documents have finished saving
        if us_doc in self._doc_handler_ids.keys():
            us_doc.disconnect(self._doc_handler_ids[us_doc])
            del(self._doc_handler_ids[us_doc])
        if self._doc_handler_ids:
            self._l.info("Still waiting for documents to save")
        elif self._state != self._EXECUTE:
            self._l.info("Build/compile cancelled after saves")
        else:
            # Allow user to edit command before running
            md = self._ui('dlg_run_command')
            button_revert = self._ui('button_revert')
            buffer = self._ui('command_text').get_buffer()
            buffer.set_text(self._get_prev_command(doc, get_cmd_func))
            resp = 1
            while resp == 1:
                resp = md.run()
                if resp == 1:
                    buffer.set_text(get_cmd_func(doc))
            md.hide()
            command = buffer.get_text(buffer.get_start_iter(),
                                      buffer.get_end_iter())
            if resp == gtk.RESPONSE_OK:
                self._set_prev_command(doc, get_cmd_func, command)
                saved_cwd = os.getcwd()
                if rootdir:
                    os.chdir(rootdir)
                for k, v in self._item_locations.iteritems():
                    if isinstance(v, gtk.TextMark):
                        v.get_buffer().delete_mark(v)
                self._item_locations.clear()
                self._console.execute(command)
                os.chdir(saved_cwd)
            
        return
    
    def _get_prev_command(self, doc, get_cmd_func):
        if doc in self._prev_commands.keys():
            if get_cmd_func in self._prev_commands[doc]:
                return self._prev_commands[doc][get_cmd_func]
        return get_cmd_func(doc)
        
    def _set_prev_command(self, doc, get_cmd_func, command):
        if doc not in self._prev_commands.keys():
            self._prev_commands[doc] = {}
        self._prev_commands[doc][get_cmd_func] = command

    def _record(self, item_no, file_name, line_no, col_no):
        self._l.debug("Entered: item[%d], filename[%s], line[%d], col[%d]" % (item_no, file_name, line_no, col_no))

        # Find the document for this file_name
        open_docs = self._window.get_documents()
        self._l.debug("Looking to see if [%s] is already open" % os.path.basename(file_name))
        for doc in open_docs:
            self._l.debug("Found open doc [%s]" % doc.get_short_name_for_display())
            if doc.get_uri_for_display() == file_name:
                self._l.debug("Found!")
                # this seems a bit around the houses
                tab = self._window.get_tab_from_uri(doc.get_uri())
                self._item_locations[item_no] = self._mark_document(doc, line_no, col_no)
                return
        self._item_locations[item_no] = (file_name, line_no, col_no)
        
    def _get_tab_for_uri(self, uri):
        """Return tab for given uri, or None"""
        self._l.debug("Entered(%s)" % uri)
        open_docs = self._window.get_documents()
        for doc in open_docs:
            self._l.debug("Found open doc [%s]" % doc.get_short_name_for_display())
            if doc.get_uri_for_display() == uri:
                self._l.debug("Found!")
                # this seems a bit around the houses
                return self._window.get_tab_from_uri(doc.get_uri())
        return None

    def _set_cursor_pos(self, where):
        self._l.debug("Entered")
        doc = where.get_buffer()
        doc.place_cursor(doc.get_iter_at_mark(where))
        tab = self._window.get_tab_from_uri(doc.get_uri())
        self._window.set_active_tab(tab)
        tab.get_view().scroll_to_cursor()
        tab.get_view().grab_focus()

    def _goto(self, item_no):
        self._l.debug("Entered: item[%d]" % item_no)

        where =  self._item_locations[item_no]
        if isinstance(where, gtk.TextMark):
            self._set_cursor_pos(where)
        else:
            (file_name, line_no, col_no) = where
            self._l.info("Document no currently loaded %s:%d:%d" % (file_name, line_no, col_no))
        
            #uri = "file://" + file_name
            uri = gnomevfs.get_uri_from_local_path(file_name)
            if gedit.utils.uri_exists(uri):
                # First check that we are not in the middle of opening this document
                if self._get_tab_for_uri(uri):
                    self._l.info("    but is loading...")
                    return
                
                tab = self._window.create_tab_from_uri(uri, None, 0, False, True)
                doc = tab.get_document()
                self._l.debug("Now opening [%s]" % doc.get_uri_for_display())
                doc.connect("loaded", self._doc_loaded_cb, item_no)
            else:
                md = gtk.MessageDialog(
                    self._window,
                    gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL,
                    gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_CLOSE,
                    "Could not find '%s'" % file_name)
                md.run()
                md.destroy()

    def _doc_loaded_cb(self, doc, arg1, item_no):
        doc_uri = doc.get_uri_for_display()
        self._l.debug("Entered('%s', arg1, %d" % (doc_uri, item_no))
        # Now we have loaded the document we might as well convert all relevant
        # items to marks
        for k, v in self._item_locations.iteritems():
            if isinstance(v, tuple):
                (file_name, line_no, col_no) = v
                if file_name == doc_uri:
                    self._l.debug("Setting mark for %d:%d" % (line_no, col_no))
                    self._item_locations[k] = self._mark_document(doc, line_no, col_no)
        
        self._set_cursor_pos(self._item_locations[item_no])
        return False
        
    def _mark_document(self, doc, line_no, col_no):
        self._l.debug("Entered(doc, %d, %d)" % (line_no, col_no))
        # line_no and col_no come from an external source so they can't be trusted.
        # Unfortunately, gtk.TextBuffer.get_iter_at_line_offset just aborts the app
        # if values are out of range.  Top banana!
        lines = doc.get_line_count()
        if line_no < 0:
            line_no = 0
        if line_no > lines:
            line_no = lines
        if col_no < 0:
            col_no = 0
        cur_iter = doc.get_iter_at_line(line_no-1)
        if col_no > cur_iter.get_chars_in_line():
            col_no = cur_iter.get_chars_in_line()
            if line_no == lines:
                col_no += 1
        
        self._l.debug("Creating mark at %d:%d" % (line_no, col_no))
        cur_iter = doc.get_iter_at_line_offset(line_no-1, col_no-1)
        return doc.create_mark(None, cur_iter, False)
        
    def update_ui(self):
        #self._l.debug("Entered")
        pass


