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
'''

import os
import gtk
try:
  import gedit
  import gconf
except:
  import pluma as gedit
  import mateconf as gconf

from encodingshelper import EncodingsHelper

# duplicate of gedit/dialogs/gedit-encodings-dialog.c

class ConfigureDialog:

  def __init__(self, parent, plugin):

    self.plugin = plugin

    dataDir = plugin.get_data_dir()

    self.builder = gtk.Builder()
    self.builder.add_from_file(os.path.join(dataDir, "configuredialog.glade"))

    dic = {
      "on_window_main_response" : self.on_window_main_response,
      "on_button_add_clicked" : self.on_button_add_clicked,
      "on_button_remove_clicked" : self.on_button_remove_clicked,
      "on_treeview2_cursor_changed" : self.on_treeview2_cursor_changed,
      "on_treeview3_cursor_changed" : self.on_treeview3_cursor_changed
    }

    self.builder.connect_signals(dic)

    self["dialog"].set_transient_for(parent)

    self["dialog"].set_default_response(gtk.RESPONSE_OK)
    self["dialog"].add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self["dialog"].add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

    self.init_dialog()

  def __getitem__(self, item):
    return self.builder.get_object(item)

  def load_enc_list(self, encs, tree):
    liststore = gtk.ListStore(gedit.Encoding, str, str)
    tree.set_model(liststore)
    
    cell = gtk.CellRendererText()
    col = gtk.TreeViewColumn("Description", cell, text=1)
    tree.append_column(col)
    
    cell = gtk.CellRendererText()
    col = gtk.TreeViewColumn("Encoding", cell, text=2)
    tree.append_column(col)
    
    for enc in encs:
      liststore.append((enc, enc.get_name(), enc.get_charset()))

  def get_enc_list(self):
    encs = []
    model = self["treeview3"].get_model()
    
    for enc in model:
      encs.append(enc[0])
      
    return encs

  def init_dialog(self):
    eh = EncodingsHelper()
    
    encs = eh.gedit_get_all_encodings()
    for enc in eh.gedit_prefs_manager_get_shown_in_menu_encodings():
      if enc in encs:
        encs.remove(enc)

    self.load_enc_list(encs, self["treeview2"])
    self.load_enc_list(eh.gedit_prefs_manager_get_shown_in_menu_encodings(), self["treeview3"])

  def on_window_main_response(self, dlg, resp):
    if resp == gtk.RESPONSE_OK:
      eh = EncodingsHelper()
      eh.gedit_prefs_manager_set_shown_in_menu_encodings(self.get_enc_list())
      
      self.plugin.reload_ui()

    self["dialog"].hide()

  def on_button_remove_clicked(self, button):
    selection = self["treeview3"].get_selection()
    (model, iter) = selection.get_selected()
    
    if iter == None:
      return
    
    enc = model[iter]
    model2 = self["treeview2"].get_model()
    model2.append(enc)
    model.remove(iter)

  def on_button_add_clicked(self, button):
    selection = self["treeview2"].get_selection()
    (model, iter) = selection.get_selected()

    if iter == None:
      return
    
    model3 = self["treeview3"].get_model()
    model3.append(model[iter])
    model.remove(iter)

  def on_treeview2_cursor_changed(self, tree_view):
    selection = self["treeview2"].get_selection()
    (model, iter) = selection.get_selected()
    self["button_add"].set_sensitive(iter != None)

  def on_treeview3_cursor_changed(self, tree_view):
    selection = self["treeview3"].get_selection()
    (model, iter) = selection.get_selected()
    self["button_remove"].set_sensitive(iter != None)
