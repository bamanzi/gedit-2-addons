'''
Encoding converter plugin for gedit application
Copyright (C) 2009  Alexey Kuznetsov <ak@axet.ru>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

----

thx to http://live.gnome.org/Gedit/PythonPluginHowTo

version 1.1.0
'''

import gedit
import gtk
import os
import sys

from browsedialog import BrowseDialog
from dochelper import DocHelper
from encodingshelper import EncodingsHelper

class EncodingConverterPluginHelper:
  
  window = None
  plugin = None
  action_group = None
  ui_id = None

  def __init__(self, plugin, window):
    self.window = window
    self.plugin = plugin

    doc = self.window.get_active_document()

    self.load_menus()

  def load_menus(self):

    manager = self.window.get_ui_manager()

    if self.ui_id != None:
      manager.remove_ui(self.ui_id)

    if self.action_group != None:
      manager.remove_action_group(self.action_group)

    self.ui_id = manager.new_merge_id()

    self.action_group = gtk.ActionGroup("GeditToUTF8EncodingConverterPluginActions")
    
    manager.add_ui(self.ui_id, "/MenuBar/ToolsMenu", "fromSEPARATOR", "fromSEPARATOR", gtk.UI_MANAGER_SEPARATOR, False)

    eh = EncodingsHelper()
    encs = eh.gedit_prefs_manager_get_shown_in_menu_encodings()

    for enc in encs:
      action = "from_" + enc.get_charset()
      actions = [(action, None, "Convert text from " + enc.get_charset(), None, "Convert text from " + enc.get_charset(), self.from_encoding)]
      self.action_group.add_actions(actions, (self.window, enc))
      manager.add_ui(self.ui_id, "/MenuBar/ToolsMenu", action, action, gtk.UI_MANAGER_MENUITEM, False)

    actions = [("fromBROWSE", None, "Convert text from ...", None, "Convert text from ...", self.from_browse)]
    self.action_group.add_actions(actions, self.window)
    manager.add_ui(self.ui_id, "/MenuBar/ToolsMenu", "fromBROWSE", "fromBROWSE", gtk.UI_MANAGER_MENUITEM, False)

    manager.insert_action_group(self.action_group, -1)

  def close(self):
    manager = self.window.get_ui_manager()
    manager.remove_ui(self.ui_id)
    manager.remove_action_group(self.action_group)
    manager.ensure_update()

    self.action_group = None
    self.window = None
    self.plugin = None

  def update_ui(self):
    doc = self.window.get_active_document()
    self.action_group.set_sensitive(bool(doc and not doc.get_readonly()))

  def from_encoding(self, widget, window, enc):
    doc = DocHelper(window.get_active_document())
    doc.recode_doc(enc.get_charset())

  def from_browse(self, widget, window):
    doc1 = window.get_active_document()
    bd = BrowseDialog(window, self.plugin, doc1)
    res = bd["dialog"].run()
    if res == gtk.RESPONSE_OK:
      doc2 = DocHelper(bd.doc2)
      doc = DocHelper(doc1)
      doc.replace_new(doc2.read_all())
