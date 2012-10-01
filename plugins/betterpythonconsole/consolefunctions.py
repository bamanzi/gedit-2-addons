#!/usr/bin/env python

#    This file is part of the Better Python Console Plugin for Gedit
#    Copyright (C) 2007 Zeth Green <zethgreen@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""Core Functions for Gedit to interact with the Python Console. """

import sys
import gtk
import gedit
import gobject
import subprocess

# Insert a new item in the Tools menu
UI_STR = """<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="ToolsOps_2">
        <menuitem name="BetterConsole" action="BetterConsole"/>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""
class BetterConsoleHelper:
    """Provides interaction with Gedit."""
    def __init__(self, plugin, window, consolepath):
        self._window = window
        self._plugin = plugin
        self._consolepath = consolepath
        # Insert menu items
        self._insert_menu()

    def deactivate(self):
        """Remove any installed menu items from the Gedit Menu."""
        self._remove_menu()

        self._window = None
        self._plugin = None
        self._action_group = None

    def _insert_menu(self):
        """Insert our item into the Gedit menu."""
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Create a new action group
        self._action_group = gtk.ActionGroup("BetterConsolePluginActions")
        self._action_group.add_actions([("BetterConsole", None, _("Run Module"),
                                         'F5', _("Run file in Python Console"),
                                         self.on_clear_document_activate)])

        # Insert the action group
        manager.insert_action_group(self._action_group, -1)

        # Merge the UI
        self._ui_id = manager.add_ui_from_string(UI_STR)

    def _remove_menu(self):
        """Pull our item from the menu."""
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()

    def update_ui(self):
        """Unused in our case at the moment,
        but required for the plugins system to be happy."""
        self._action_group.set_sensitive(
            self._window.get_active_document() != None)

    def on_clear_document_activate(self, action):
        """Menu activate handler,
        i.e. this is what happens when someone clicks Run Module.
        Contains sanity checks which is against the Zen of Python."""
        # Is there even a document?
        doc = self._window.get_active_document()
        if not doc:
            return
        our_filename = doc.get_short_name_for_display()
        
        # Check for unsaved changes 
        unsaved = self._window.get_unsaved_documents()        
        unsaved_filenames = []
        for i in range(len(unsaved)):
            unsaved_filenames.append(unsaved[i].get_uri_for_display())        
        if unsaved_filenames.count(our_filename) == 1:
            mes_id = "unsaved_changes"
            message = "There are unsaved changes."  
            self.send_staus_message(message, mes_id)
            
        # Check for an untitled document 
        elif doc.is_untitled() == True:
            mes_id = "untitled_document"
            message = "You must save the document first."
            self.send_staus_message(message, mes_id)
            
        # Check for an non-local file    
        elif doc.get_uri()[:7]!="file://":
            mes_id = "unsupported_location"
            message = """This file location is currently unsupported.
            Please save the file locally."""
            self.send_staus_message(message, mes_id)
            
        # Everything is fine
        else:
            self.launch_python_console(doc.get_uri_for_display())
            mes_id = "upforit"
            message = "The module " + doc.get_short_name_for_display() + \
            " has been executed."
            self.send_staus_message(message, mes_id)
               
    def launch_python_console(self, filename):
        """Launch a console."""
        interpreter_name = "python"
        fullpath = self._consolepath + "/consoleinterface.py"
        run_command = [interpreter_name, fullpath, filename]
        p1 = subprocess.Popen(run_command, stdout=subprocess.PIPE)

    def send_staus_message(self, message, mes_id):
        """Put a message on the Status bar."""
        our_statusbar = self._window.get_statusbar()
        our_newid = our_statusbar.get_context_id(mes_id)
        our_statusbar.push(our_newid, message)
        gobject.timeout_add(
            2000,self.clear_statusbar_from_crap,our_newid,our_statusbar)  

    def clear_statusbar_from_crap(self, crap_id, status_bar):
        """Take a message off the Status bar."""
        status_bar.pop(crap_id)
        return False        
