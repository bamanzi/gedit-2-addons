# -*- coding: UTF-8 -*-
#
# File: switcher.py
#
# Copyrigt © 2006 Mikael Hermansson <mikael.hermansson@linuxmail.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
try:
	import gedit
except:
	import pluma as gedit

import gtk
import gobject

class App(gtk.Window):
	__gsignals__ = {
		'switcher' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,())
 	}

	def __init__(self):
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		self.set_default_size(640,400)
		self.set_title("Switcher plugin select document:");
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_keep_above(True)
		self.set_skip_taskbar_hint(True)
		sc = gtk.ScrolledWindow()
		sc.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.treeview = gtk.TreeView()
		self.model = gtk.ListStore(gobject.TYPE_OBJECT, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN)
		self.treeview.set_model(self.model)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Document:", cell)
		col.set_expand(True)
		col.add_attribute(cell, "text", 1)
		self.treeview.append_column(col)
		self.treeview.set_search_column(1)
		cell = gtk.CellRendererToggle()
		col = gtk.TreeViewColumn("Modified:", cell)
		col.set_expand(False)
		col.add_attribute(cell, "active", 2)
		self.treeview.append_column(col)
		sc.add(self.treeview)
		self.add(sc)
		self.connect("delete_event", self.on_delete_event)
		self.connect("key-press-event", self.on_key_press_event)
		self.connect("focus-out-event", self.on_focus_out)
		
		
	def on_row_activated(self, tw, path, col, window):
		it=self.model.get_iter(path)
		doc=self.model.get(it, 0)[0]
		if doc != None:
			tab = gedit.tab_get_from_document(doc)
			window.set_active_tab(tab)
		
		self.hide()
	
	def on_focus_out(self, w, ev):
		self.hide()
	
	def on_key_press_event(self, w,  ev) :
		"""escape key"""
		if (ev.keyval==gtk.keysyms.Escape) :
			self.window.hide()
			return True

		return False

	def on_delete_event(self, win, ev):
		self.hide()
		return True

	def add_bindings_to_window(self, window):
		self.ui = window.get_ui_manager()
		self.action_group=gtk.ActionGroup("Switcher")
		self.actionSwitchDocument = gtk.Action("actionSwitchDocument", "Switch document", "Switch between windows", 0) 
		self.action_group.add_action_with_accel(self.actionSwitchDocument,"<Control>Escape")
		self.actionSwitchDocument.connect("activate", self.on_switch_document, window)
		self.ui.insert_action_group(self.action_group, -1)
		self.gid = self.ui.new_merge_id();
		self.ui.add_ui(self.gid, "/MenuBar/DocumentsMenu/", "Plugin", "actionSwitchDocument",gtk.UI_MANAGER_SEPARATOR , 0) 
		self.ui.add_ui(self.gid, "/MenuBar/DocumentsMenu/", "Menu", "actionSwitchDocument",gtk.UI_MANAGER_MENUITEM , 0) 
		self.treeview.connect("row-activated", self.on_row_activated, window)
		# why the fuck does it not pass it on
	#	self.connect("key-press-event", self.mainwindow_on_key_press_event)

	def mainwindow_on_key_press_event(self, ev):
		if ev.keyval == gtk.keysyms.Tab and (ev.state & gtk.gdk.CONTROL_MASK)== 1 :
			self.on_switch_document(None, window)
			return True
		
		return False

	def on_switch_document(self, menu, window):
		self.model.clear()
		docs=window.get_documents()
		if docs == None:
			return 
			
		i = 1
		for doc in docs:
			it = self.model.append()
			self.model.set_value(it, 0, doc)
			self.model.set_value(it, 1, str(i)+" "+doc.get_uri())
			self.model.set_value(it, 2, doc.get_modified())
			i=i+1
			
		self.show_all()
		self.treeview.grab_focus()

class MultiView(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
			
	def activate(self, window):
		self.list = App()
		self.list.add_bindings_to_window(window)

	def deactivate(self, window):
		pass

	def update_ui(self, win):	
		pass		



gobject.type_register(MultiView)

