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
except:
  import pluma as gedit

from dochelper import DocHelper
from encodingshelper import EncodingsHelper
from configuredialog import ConfigureDialog

def copy(doc1, doc2):
  doc11 = DocHelper(doc1)
  doc22 = DocHelper(doc2)
  doc22.replace_new(doc11.read_all())
  doc2.set_language(doc1.get_language())

def match_func(model, iter, data):
  column, key = data # data is a tuple containing column number, key
  value = model.get_value(iter, column)
  return value == key

def search(model, iter, func, data):
  while iter:
    if func(model, iter, data):
      return iter
    result = search(model, model.iter_children(iter), func, data)
    if result: return result
    iter = model.iter_next(iter)
  return None

class BrowseDialog():

  lastwidth = 0
  lastposition = 0
  proportion = 2
  helper = None

  def __init__(self, parent, plugin, doc):

    self.plugin = plugin
    dataDir = plugin.get_data_dir()
    
    self.doc = doc

    self.builder = gtk.Builder()
    self.builder.add_from_file(os.path.join(dataDir, "browsedialog.glade"))

    dic = {
      "on_hpaned_files_size_allocate" : self.on_hpaned_files_size_allocate,
      "on_combobox1_changed" : self.on_combobox1_changed,
      "on_browse_clicked" : self.on_browse_clicked,
      "on_window_main_response" : self.on_window_main_response
    }

    self["dialog"].set_transient_for(parent)

    self.builder.connect_signals(dic)

    self.doc1 = gedit.Document()
    self.doc2 = gedit.Document()

    copy(doc, self.doc1)
    copy(doc, self.doc2)

    self.doc1.goto_line(0)
    self.doc2.goto_line(0)

    self.view1 = gedit.View(self.doc1)
    self.view2 = gedit.View(self.doc2)

    self["h_scrolledwindow1"].add(self.view1)
    self["h_scrolledwindow2"].add(self.view2)

    self.doc1.readonly = True
    self.doc2.readonly = True

    self["dialog"].set_default_response(gtk.RESPONSE_OK)
    self["dialog"].add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
    self["dialog"].add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

    self.load_encs()
    self["combobox1"].set_active(0)
    self["combobox1"].grab_focus()

    cell = gtk.CellRendererText()
    self["combobox1"].pack_start(cell, True)
    self["combobox1"].add_attribute(cell, 'text', 1)

  def __getitem__(self, item):
    return self.builder.get_object(item)

  def load_encs(self):
    liststore = gtk.ListStore(gedit.Encoding, str)
    self["combobox1"].set_model(liststore)

    enc = self.doc.get_encoding()
    liststore.append((enc, "Original encoding (" + enc.get_charset() + ")"))

    eh = EncodingsHelper()
    for enc in eh.gedit_prefs_manager_get_shown_in_menu_encodings():
      liststore.append((enc, enc.get_name() + " (" + enc.get_charset() + ")"))

  def on_hpaned_files_size_allocate(self, widget, allocation):
    new_width = allocation.width

    new_position = self["hpaned_files"].get_position()

    if(new_width != self.lastwidth):
      self.lastwidth = new_width
      self["hpaned_files"].set_position(int(new_width / self.proportion))

    if(new_position != self.lastposition):
      self.lastposition = new_position

      if(new_position > 0):
        self.proportion = new_width / float(new_position)
      else:
        self.proportion = 0

  def on_window_main_response(self, dialog, response_id):
    self["dialog"].hide()

  def on_browse_clicked(self, some1):
    cd = ConfigureDialog(self["dialog"], self.plugin)
    if cd["dialog"].run() == gtk.RESPONSE_OK:
      model = self["combobox1"].get_model()
      iter = self["combobox1"].get_active_iter()
      enc = model[iter][0]
      
      self.load_encs()
      
      model = self["combobox1"].get_model()
      iter = search(model, model.get_iter_first(), match_func, (0, enc))
      if iter == None:
        self["combobox1"].set_active(0)
      else:
        self["combobox1"].set_active_iter(iter)

  def on_combobox1_changed(self, combobox):
    index = self["combobox1"].get_active()
    model = self["combobox1"].get_model()
    enc = model[index][0]
    
    copy(self.doc1, self.doc2)
    
    doc = DocHelper(self.doc2, self.doc.get_encoding())
    doc.recode_doc(enc.get_charset())
