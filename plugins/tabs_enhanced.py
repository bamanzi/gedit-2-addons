# -*- coding: utf-8 -*-
#
# Copyright © 2009, James Campos
# Copyright © 2008, Éverton Ribeiro <nuxlli@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import gtk
try:
    import gedit
    import gconf
    is_mate = False
    APPNAME = 'gedit-2'
except:
    import pluma as gedit
    import mateconf as gconf
    is_mate = True
    APPNAME = 'pluma'
client = gconf.client_get_default()

# Find widget by name
def lookup_widget(base, widget_name):
  widgets = []

  for widget in base.get_children():
    if widget.get_name() == widget_name:
      widgets.append(widget)
    if isinstance(widget, gtk.Container):
      widgets += lookup_widget(widget, widget_name)

  return widgets

# UI Manager XML
ACTIONS_UI = """
<ui>
  <menubar name="MenuBar">
    <menu name="FileMenu" action="File">
      <placeholder name="FileOps_2">
        <menuitem name="UndoClose" action="UndoClose"/>
      </placeholder>
    </menu>
  </menubar>

  <popup name="NotebookPopup" action="NotebookPopupAction">
    <placeholder name="NotebookPupupOps_1">
      <menuitem name="UndoClose" action="UndoClose"/>
      <menuitem name="CloseOthers" action="CloseOthers"/>
    </placeholder>
  </popup>
</ui>
"""

class TabsExtendWindowHelper:

  def __init__(self, plugin, window):
    """Activate plugin."""
    self.window = window
    if not is_mate:
        self.notebook = lookup_widget(self.window, 'GeditNotebook')[0]
    else:
        self.notebook = lookup_widget(self.window, 'PlumaNotebook')[0]      
    self.handler_ids = []
    self.tabs_closed = []

    self.add_all()
    self.handler_ids.append((self.notebook, self.notebook.connect("button-press-event", self.bar_click_handler) ))
    self.handler_ids.append((self.notebook, self.notebook.connect("tab_removed", self.tab_removed_handler) ))
    self.handler_ids.append((self.notebook, self.notebook.connect("tab_added", self.tab_added_handler) ))
    self.add_actions()
    
    if self.notebook.get_n_pages() == 1 and client.get_bool("/apps/%s/plugins/tabsenhanced/hide" % APPNAME):
      self.notebook.set_show_tabs(False)

#    bottomPanel = lookup_widget(self.window.get_bottom_panel(), 'GeditNotebook')[0]
#    print bottomPanel
#    if bottomPanel:
#      self.bottomPanel.set_show_tabs(False)

  def add_all(self):
    for x in range(self.notebook.get_n_pages()):
      tab = self.notebook.get_nth_page(x)
      self.add_middle_click_in_tab(tab)

  def add_middle_click_in_tab(self, tab):
    eventbox   = self.notebook.get_tab_label(tab)
    handler_id = eventbox.connect("button-press-event", self.middle_click_handler, tab)
    self.handler_ids.append((eventbox, handler_id))

  def middle_click_handler(self, widget, event, tab):
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 2:
      self.window.close_tab(tab)

  def bar_click_handler(self, widget, event):
    curr_page = self.notebook.get_current_page()
    tab = self.notebook.get_nth_page(curr_page)
    if event.type == gtk.gdk.BUTTON_PRESS and event.button == 2:
      self.window.close_tab(tab)

  def tab_added_handler(self, widget, tab):
    if self.notebook.get_n_pages() == 1 and client.get_bool("/apps/%s/plugins/tabsenhanced/close" % APPNAME):
      self.notebook.set_show_tabs(False)
    self.add_middle_click_in_tab(tab)

  def tab_removed_handler(self, widget, tab):
    if not self.notebook:
      return
    pages = self.notebook.get_n_pages()
    if pages == 0 and client.get_bool("/apps/%s/plugins/tabsenhanced/close" % APPNAME):
      return self.window.destroy()
    if pages == 1 and client.get_bool("/apps/%s/plugins/tabsenhanced/hide" % APPNAME):
      self.notebook.set_show_tabs(False)
    self.save_tab_to_undo(tab)
    self.update_ui()
    for (handler_id, widget) in self.handler_ids:
      if widget == tab:
        widget.disconnect(handler_id)
        self.handler_ids.remove(handler_id)
        break

  def get_current_line(self, document):
    """ Get current line for documento """
    return document.get_iter_at_mark(document.get_insert()).get_line() + 1

  # TODO: Save position tab
  def save_tab_to_undo(self, tab):
    """ Save close tabs """

    document = tab.get_document()
    if document.get_uri() != None:
      self.tabs_closed.append((
        document.get_uri(),
        self.get_current_line(document)
      ))

  def on_undo_close(self, action):
    if len(self.tabs_closed) > 0:
      uri, line = tab = self.tabs_closed[-1:][0]

      if uri == None:
        self.window.create_tab(True)
      else:
        self.window.create_tab_from_uri(uri, None, line, True, True)

      self.tabs_closed.remove(tab)
    self.update_ui()

  def on_close_other(self, action):
    if self.notebook.get_n_pages() > 1:
      dont_close = self.window.get_active_tab()

      tabs = []
      for x in range(self.notebook.get_n_pages()):
        tab = self.notebook.get_nth_page(x)
        if tab != dont_close:
          tabs.append(tab)

      tabs.reverse()
      for tab in tabs:
        self.window.close_tab(tab)

      self.update_ui()

  def add_actions(self):
    undoclose = (
      'UndoClose', # name
      'gtk-undo', # icon stock id
      'Undo Close', # label
      '<Ctrl><Shift>T',# accelerator
      'Reopen the last closed tab', # tooltip
      self.on_undo_close # callback
    )

    closeothers = (
      'CloseOthers', # name
      'gtk-close', # icon stock id
      'Close Others', # label
      '<Ctrl><Shift>O',# accelerator
      'Close other tabs', # tooltip
      self.on_close_other # callback
    )

    action_group = gtk.ActionGroup(self.__class__.__name__)
    action_group.add_actions([undoclose, closeothers])

    ui_manager = self.window.get_ui_manager()
    ui_manager.insert_action_group(action_group, 0)
    ui_id = ui_manager.add_ui_from_string(ACTIONS_UI)

    data = { 'action_group': action_group, 'ui_id': ui_id }
    self.window.set_data(self.__class__.__name__, data)
    self.update_ui()

  def deactivate(self):
    """Deactivate plugin."""
    # disconnect
    for (widget, handler_id) in self.handler_ids:
      widget.disconnect(handler_id)

    self.notebook.set_show_tabs(True)
    data = self.window.get_data(self.__class__.__name__)
    ui_manager = self.window.get_ui_manager()
    ui_manager.remove_ui(data['ui_id'])
    ui_manager.remove_action_group(data['action_group'])
    ui_manager.ensure_update()
    self.window.set_data(self.__class__.__name__, None)

    self.window = None
    self.notebook = None

  def update_ui(self):
    """Update the sensitivities of actions."""
    pass
    windowdata = self.window.get_data(self.__class__.__name__)
    windowdata['action_group'].get_action('UndoClose').set_sensitive(len(self.tabs_closed) > 0)
    windowdata['action_group'].get_action('CloseOthers').set_sensitive(self.notebook.get_n_pages() > 1)


class TabsExtendPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = TabsExtendWindowHelper(self, window)

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)
        dialog = gtk.Dialog("Extend Tabs Configuration", None, 0, buttons)
        self.chk_hide = gtk.CheckButton("Auto hide tab bar")
        self.chk_hide.set_active(client.get_bool("/apps/%s/plugins/tabsenhanced/hide" % APPNAME))
        self.chk_close = gtk.CheckButton("Close gedit when last tab is closed")
        self.chk_close.set_active(client.get_bool("/apps/%s/plugins/tabsenhanced/close" % APPNAME))
        dialog.vbox.pack_start(self.chk_hide, True, True, 0)
        dialog.vbox.pack_start(self.chk_close, True, True, 0)
        dialog.connect("response", self.response)
        dialog.show_all()
        return dialog

    def response(self, dialog, res): # Handles configuration dialog response
        # Hide configuration dialog
        dialog.hide()
        if res == gtk.RESPONSE_OK:
          client.set_bool("/apps/%s/plugins/tabsenhanced/hide" % APPNAME, self.chk_hide.get_active())
          client.set_bool("/apps/%s/plugins/tabsenhanced/close" % APPNAME, self.chk_close.get_active())
#          notebook = lookup_widget(self, 'GeditNotebook')[0]
#          if self.chk_hide.get_active() and notebook.get_n_pages() == 1:
#            notebook.set_show_tabs(False)
#          else:
#            notebook.set_show_tabs(True)
