#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# Shows a list of python def's.
# You can choose a hotkey for this (e.g., F2) to be more useful.
#
# - Ricardo Lenz
#

import gtk
try:
    import gedit
except:
    import pluma as gedit
import pango
import glib

from gui import *


ui = """
<ui>
    <menubar name="MenuBar">
    <menu name="PythonMenu" action="Python">
      <placeholder name="ToolsOps_5">
        <menuitem action="ShowPythonDefs" />
      </placeholder>
    </menu>
    </menubar>
</ui>
"""



class PythonDefs:
    
    def __init__(self, window, pluginManager):
        self.window = window
        self.pluginManager = pluginManager

        action = ( "ShowPythonDefs", gtk.STOCK_JUSTIFY_FILL, "Show Python Defs", "", \
            "Shows all source code def's", self.on_run )            
        self.action_group = gtk.ActionGroup( "PythonPluginActions" )
        self.action_group.add_actions( [action] )

        manager = window.get_ui_manager()
        manager.insert_action_group( self.action_group, -1 )
        self.ui_id = manager.add_ui_from_string( ui )


    def __del__(self):
        manager = self.window.get_ui_manager()
        manager.remove_ui( self.ui_id )
        manager.remove_action_group( self.action_group )
        manager.ensure_update()


    def update_ui(self):
        doc = self.window.get_active_document()
        ok = doc != None
        if ok:
            ok = doc.get_uri() != ""
            
        self.action_group.set_sensitive( ok )


    def on_run(self, *args):
        Gui().run( self.window )




class PythonDefs_manager(gedit.Plugin):

    def __init__(self):
        gedit.Plugin.__init__(self)
        self.per_window_plugins = {}

    def activate(self, window):
        self.per_window_plugins[window] = PythonDefs( window, self )

    def deactivate(self, window):
        self.per_window_plugins[window].__del__()

    def update_ui(self, window):
        self.per_window_plugins[window].update_ui()


