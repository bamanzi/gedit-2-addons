# -*- coding: utf8 -*-
#  Highlight Text plugin for gedit
#
#  Copyright (C) 2010 Derek Veit
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

"""
This module provides the plugin object that gedit interacts with.

Classes:
HighlightTextPlugin       -- object is loaded once by an instance of gedit
HighlightTextWindowHelper -- object is constructed for each gedit window

Each time the same gedit instance makes a new window, gedit calls the plugin's
activate method, which then constructs a helper object to handle the new window.

Settings common to all gedit windows are attributes of HighlightTextPlugin.
Settings specific to one window are attributes of HighlightTextWindowHelper.

"""

try:
  import gedit
except:
  import pluma as gedit
import gtk

from .logger import Logger
LOGGER = Logger(level=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')[2])

class HighlightTextPlugin(gedit.Plugin):
    
    """
    An object of this class is loaded once by a gedit instance.
    
    Public methods:
    activate        -- gedit calls this to start the plugin.
    deactivate      -- gedit calls this to stop the plugin.
    update_ui       -- gedit calls this at certain times when the UI changes.
    is_configurable -- gedit calls this to check if the plugin is configurable.
    
    """
    
    def __init__(self):
        """Initialize plugin attributes."""
        LOGGER.log()
        
        gedit.Plugin.__init__(self)
        
        self._instances = {}
        """Each gedit window will get a HighlightTextWindowHelper instance."""
    
    def activate(self, window):
        """Add and start a helper object for this gedit window."""
        LOGGER.log()
        if not self._instances:
            LOGGER.log('Highlight Text activating.')
        self._instances[window] = HighlightTextWindowHelper(self, window)
        self._instances[window].activate()
    
    def deactivate(self, window):
        """Stop and remove the helper object for this gedit window."""
        LOGGER.log()
        self._instances[window].deactivate()
        self._instances.pop(window)
        if not self._instances:
            LOGGER.log('Highlight Text deactivated.')
    
    def update_ui(self, window):
        """Forward gedit's update_ui command for this window."""
        LOGGER.log()
        self._instances[window].update_ui()
    
    def is_configurable(self):
        """Identify for gedit whether this plugin is configurable."""
        LOGGER.log()
        return False
    

class HighlightTextWindowHelper(object):
    
    """
    HighlightTextPlugin creates a HighlightTextWindowHelper object for each
    gedit window.
    
    Public methods:
    activate   -- HighlightTextPlugin calls this when gedit calls activate for
                  this window.
    deactivate -- HighlightTextPlugin calls this when gedit calls deactivate for
                  this window.
    update_ui  -- HighlightTextPlugin calls this when gedit calls update_ui for
                  this window.  Also, HighlightTextWindowHelper.activate calls
                  this.
    
    """
    
    def __init__(self, plugin, window):
        """Initialize plugin attributes for this window."""
        LOGGER.log()
        
        self._plugin = plugin
        """The Plugin that spawned this helper object."""
        self._window = window
        """The window this helper object runs on."""
        
        self._ui_id = None
        """The menu's UI identity."""
        self._action_group = None
        """The menu's action group."""
    
    def activate(self):
        """Add the plugin features for this window."""
        LOGGER.log()
        LOGGER.log('Highlight Text activating for %s' % self._window)
        self._insert_menu()
        self.update_ui()
    
    def deactivate(self):
        """Remove the plugin features for this window."""
        LOGGER.log()
        self._remove_menu()
        self._plugin = None
        LOGGER.log('Highlight Text deactivated for %s' % self._window)
        self._window = None
    
    def update_ui(self):
        """Activate the custom menu item."""
        LOGGER.log()
        document = self._window.get_active_document()
        current_view = self._window.get_active_view()
        if document and current_view and current_view.get_editable():
            self._action_group.set_sensitive(True)
    
    def _insert_menu(self):
        """Create the custom menu item."""
        LOGGER.log()

        manager = self._window.get_ui_manager()
        
        name = 'HighlightText'
        stock_id = None
        label = 'Highlight Text'
        accelerator = '<Shift><Control>j'
        tooltip = 'Highlight all occurances of the text currently selected.'
        callback = self._highlight_selection

        actions = [
            (name, stock_id, label, accelerator, tooltip, callback),
            ]
        self._action_group = gtk.ActionGroup("HighlightTextPluginActions")
        self._action_group.add_actions(actions)
        manager.insert_action_group(self._action_group, -1)
        
        ui_str = """
            <ui>
              <menubar name="MenuBar">
                <menu name="SearchMenu" action="Search">
                  <placeholder name="SearchOps_1">
                    <placeholder name="HighlightText">
                      <separator />
                      <menuitem action="HighlightText"/>
                    </placeholder>
                  </placeholder>
                </menu>
              </menubar>
            </ui>
            """
        self._ui_id = manager.add_ui_from_string(ui_str)
    
        LOGGER.log('Menu added for %s' % self._window)
    
    def _remove_menu(self):
        """Remove the custom menu item."""
        LOGGER.log()
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        self._ui_id = None
        manager.remove_action_group(self._action_group)
        self._action_group = None
        manager.ensure_update()
        LOGGER.log('Menu removed for %s' % self._window)
    
    def _highlight_selection(self, action):
        """Highlight all occurances of the currently selected text."""
        LOGGER.log()
        document = self._window.get_active_document()
        text = self._get_text_selection()
        LOGGER.log('Highlighting "%s"' % text)
        #flags = gedit.SEARCH_DONT_SET_FLAGS
        flags = gedit.SEARCH_CASE_SENSITIVE
        #flags |= gedit.SEARCH_ENTIRE_WORD
        document.set_search_text(text, flags)
    
    def _get_text_selection(self):
        """Return the currently selected text."""
        LOGGER.log()
        document = self._window.get_active_document()
        if document.get_has_selection():
            start_iter, end_iter = document.get_selection_bounds()
            selected_text = document.get_text(start_iter, end_iter)
        else:
            selected_text = ''
        return selected_text
    

