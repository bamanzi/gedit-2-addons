import gtk
try:
        import gedit
except:
        import pluma as gedit

from gettext import gettext as _
# Menu item Fullscreen, insert a new item in the Tools menu
ui_str = """<ui>
  <menubar name="MenuBar">
    <menu name="ViewMenu" action="View">
      <placeholder name="ViewsOps_2">
        <menuitem name="FullscreenPy" action="FullscreenPy"/>
        <menuitem name="MaximizeEditor" action="MaximizeEditor"/>
      </placeholder>
    </menu>
  </menubar>
  <toolbar name="ToolBar">
    <placeholder name="Tool_Opt4"><toolitem name="MaximizeEditor" action="MaximizeEditor"/></placeholder>
  </toolbar>
</ui>
"""
class FullscreenPyWindowHelper:
        def __init__(self, plugin, window):
                self._window = window
                self._plugin = plugin
                self._panes_keep_visible = {}
                 
                # Insert menu items
                self._insert_menu()  
        
        def deactivate(self):
                # Remove any installed menu items
                self._remove_menu()
                
                # Set the window to not fullscreen
                self._window.unfullscreen()
                
                self._window = None
                self._plugin = None
                self._action_group = None

        def _insert_menu(self):
                # Get the GtkUIManager
                manager = self._window.get_ui_manager()                
                
                # Create a new action group
                self._action_group = gtk.ActionGroup("FullscreenPyPluginActions")
                self._action_group.add_toggle_actions([("FullscreenPy", 
                                                        None, 
                                                        _("Toggle Fullscreen"), 
                                                        "<Shift>F11", 
                                                        _("Toggle Fullscreen"), 
                                                        lambda a: self.on_toggle_fullscreen_activate())])
                self._action_group.add_toggle_actions([("MaximizeEditor", 
                                                        gtk.STOCK_FULLSCREEN, 
                                                        _("Maximize Editor"), 
                                                        "<Control>F11", 
                                                        _("Maximize Editor (hide side pane, bottom pane)"), 
                                                        lambda a: self.on_toggle_maximize_editor())])

                # Insert the action group
                manager.insert_action_group(self._action_group, -1)

                # Merge the UI
                self._ui_id = manager.add_ui_from_string(ui_str)

        def _remove_menu(self):
                # Get the GtkUIManager
                manager = self._window.get_ui_manager()

                # Remove the ui
                manager.remove_ui(self._ui_id)

                # Remove the action group
                manager.remove_action_group(self._action_group)

                # Make sure the manager updates
                manager.ensure_update()
                
        def update_ui(self):
                self._action_group.set_sensitive(self._window.get_active_document() != None)
        
        def get_action(self, groupname, actionname):
            "Find action by ActionGroup name and Action name"
            uim = self._window.get_ui_manager()
            groups = uim.get_action_groups()
            ga = filter(lambda group: group.get_name() == groupname, groups)
            if len(ga)==1:
                group = ga[0]
                action = group.get_action(actionname)
                return action
        
        # Menu activate handlers
        def on_toggle_fullscreen_activate(self):
            show = True
            # Test if already fullscreen, and toggle appropriately
            if (self._window.window.get_state() & gtk.gdk.WINDOW_STATE_FULLSCREEN):
                self._window.unfullscreen()
                show = True
            else:
                self._window.fullscreen()
                show = False
            self._show_hide_ui_parts(show)
        
        def on_toggle_maximize_editor(self):
            action = self.get_action('FullscreenPyPluginActions', 'MaximizeEditor')
            if not action:
                action = self.get_action('PlumaWindowAlwaysSensitiveActions', 'ViewToolbar')
            assert action != None
            self._show_hide_ui_parts(not action.get_active())
                
        def _show_hide_ui_parts(self, show):
            #comment the parts you want to keep untouched
            actpaths = [
                '/GeditWindowPanesActions/ViewSidePane',
                '/GeditWindowPanesActions/ViewBottomPane',
                '/GeditWindowAlwaysSensitiveActions/ViewToolbar',
                '/GeditWindowAlwaysSensitiveActions/ViewStatusbar',
                '/PlumaWindowPanesActions/ViewSidePane',
                '/PlumaWindowPanesActions/ViewBottomPane',
                '/PlumaWindowAlwaysSensitiveActions/ViewToolbar',
                '/PlumaWindowAlwaysSensitiveActions/ViewStatusbar',
                '/GeditHideTabbarPluginActions/ShowTabbar',   #showtabbar plugin
                '/PlumaHideTabbarPluginActions/ShowTabbar',   #showtabbar plugin
                '/RightPaneActionGroup1/ViewRightSidePane',   #rightpane plugin
                ]
            for path in actpaths:
                foo, grpname, actname = path.split('/')
                action = self.get_action(grpname, actname)
                if action:
                    if show:   #we want to restore the editor (show panes)
                        # remember which panes visible while editor maximized
                        # so next time when Maximize Editor button clicked, these panes won't be hide
                        self._panes_keep_visible[path] = action.get_active()
                    if (action.get_active()!=show) and not self._panes_keep_visible.get(path, False):
                        action.activate()

class FullscreenPyPlugin(gedit.Plugin):
        DATA_TAG = "FullscreenPyPluginInstance"

        def __init__(self):
                gedit.Plugin.__init__(self)
        def _get_instance(self, window):
                return window.get_data(self.DATA_TAG)

        def _set_instance(self, window, instance):
                window.set_data(self.DATA_TAG, instance)

        def activate(self, window):
                self._set_instance(window, FullscreenPyWindowHelper(self, window))
        def deactivate(self, window):
                self._get_instance(window).deactivate()
                self._set_instance(window, None)

        def update_ui(self, window):
                self._get_instance(window).update_ui()

