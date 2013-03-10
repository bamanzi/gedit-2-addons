# Copyright (C) 2009 Tournier Guillaume (tournier.guillaume@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.


try:
    import gedit
except:
    import pluma as gedit
import gtk
import os, os.path, ConfigParser

ui_str="""<ui>
<menubar name="MenuBar">
  <menu name="ViewMenu" action="View">
    <menuitem name="ViewRightSidePaneMenu" action="ViewRightSidePane"/>
    <separator/>
    <menuitem name="ManageRightSidePaneMenu" action="ManageRightSidePane"/>
  </menu>
</menubar>
</ui>
"""

DEFAULT_WIDTH = 200

PREFS_PATH = os.path.dirname(__file__) + '/rightpane-prefs'

class RightPanePluginInstance:
	def __init__(self, plugin, window):
		self.window = window
		self.plugin = plugin
		self.popup = None
		self.popup_tab_list = gtk.VBox()
		# Read preferences
		self.config = ConfigParser.ConfigParser()
		self.read_prefs()
		# Determines which tab must be placed on right
		self.right_tab_indexes, self.load = [], []
		if self.config.has_option('right_pane', 'tabs'):
			for i in self.config.get('right_pane', 'tabs').split(','):
				if self.config.has_option('right_pane', 'tab' + i):
					self.load.append(self.config.get('right_pane', 'tab' + i))
					self.config.remove_option('right_pane', 'tab' + i)
		# gedit elements
		self.gbox = self.window.get_child()
		self.old_hpaned = self.gbox.get_children()[2]
		self.new_hpaned = gtk.HPaned()
		self.left_pane = self.old_hpaned.get_child1()
		self.left_head = self.left_pane.get_children()[0]
		self.left_notebook = self.left_pane.get_children()[1]
		self.right_pane = gedit.Panel()
		self.view_menu = self.gbox.get_children()[0].get_children()[2].get_submenu()
		# Insert the menu + right pane
		self.insert_menu()
		self.position_items_in_menu()
		self.insert_right_pane()
		self.window.connect("show", self.on_gedit_show)
		self.window.connect('delete-event', self.on_gedit_delete)
		self.lock, self.delete = False, False
		self.show = self.window.get_property("visible")
		if self.show:
			self.on_gedit_show()

	# Store all tabs & restore tabs on right pane
	def on_gedit_show(self, widget=None):
		self.images, self.labels, self.items = [], [], []
		self.left_radios, self.right_radios = [], []
		if widget:
			self.restore_left_pane_visibility()
		self.store_tabs()
		if widget:
			self.restore_right_tabs()
		self.build_popup()
		self.left_notebook.connect('page-added', self.on_page_added)
		self.left_notebook.connect('page-removed', self.on_page_removed)

	# When a plugin is removed from left panel, remove it also in popup
	def on_page_removed(self, widget, page, position):
		if (0 == self.items.count(page) or self.lock or self.delete):
			return
		index = self.items.index(page)
		self.items.remove(page)
		self.labels.pop(index)
		self.images.pop(index)
		try:
			self.popup_tab_list.remove(self.popup_tab_list.get_children()[index])
		except IndexError:
			True

	# Observe plugins which are not yet loaded
	def on_page_added(self, widget, page, position):
		if self.lock:
			return
		activated_item = self.get_activated_item(self.left_pane, self.left_notebook)
		self.left_pane.activate_item(page)
		img = self.clone_image(self.left_pane.get_children()[0].get_children()[0].get_children()[0])
		if activated_item:
			self.left_pane.activate_item(activated_item)
		text = self.left_notebook.get_menu_label_text(page)
		self.labels.append(text)
		self.images.append(img)
		self.items.append(page)
		if self.popup:
			self.add_tab(text, img, -1)

	# Must be done before deactivate all plugins
	def on_gedit_delete(self, widget=None, truc=None):
		if self.window:
			self.delete = True
			self.set_right_activated_tab()
			self.set_left_pane_visibility()
			self.save_prefs()
			self.destroy_right_pane()

	# Return the activate tab of a gedit Panel
	def get_activated_item(self, pane, notebook):
		for child in notebook.get_children():
			if pane.item_is_active(child):
				return child
		return None

	# Save tab infos
	def store_tabs(self):
		activated_item = self.get_activated_item(self.left_pane, self.left_notebook)
		for child in self.left_notebook.get_children():
			self.left_pane.activate_item(child)
			img = self.clone_image(self.left_pane.get_children()[0].get_children()[0].get_children()[0])
			text = self.left_notebook.get_menu_label_text(child)
			self.items.append(child)
			self.labels.append(text)
			self.images.append(img)
		if activated_item:
			self.left_pane.activate_item(activated_item)

	# Transfer a tab from left to right or right to left...
	def transfer_tab(self, pane1, pane2, item, label, image):
		self.lock = True
		pane1.remove_item(item)
		pane2.add_item(item, label, self.clone_image(image))
		self.lock = False

	# Restore right tabs using the preferences
	def restore_right_tabs(self):
		length = len(self.labels)
		for i in range(length):
			index = length - i - 1
			if self.load.count(self.labels[index]) > 0:
				self.transfer_tab(self.left_pane, self.right_pane, self.items[index], self.labels[index], self.images[index])
				self.config.set('right_pane', 'tab' + str(index), self.labels[index])
				self.right_tab_indexes.append(str(index))
				self.config.set('right_pane', 'tabs', ','.join(self.right_tab_indexes))
				if self.config.has_option('right_pane', 'tab-active') and self.config.get('right_pane', 'tab-active') == self.labels[index]:
					self.right_pane.activate_item(self.items[index])

	# Save the active right pane tab in prefs
	def set_right_activated_tab(self):
		notebook = self.right_pane.get_children()[1]
		activated_item = self.get_activated_item(self.right_pane, notebook)
		if activated_item and len(notebook.get_children()) > 1:
			self.config.set('right_pane', 'tab-active', notebook.get_menu_label_text(activated_item))
		else:
			self.config.remove_option('right_pane', 'tab-active')

	# Some plugin activate the left pane by default, but maybe the user doesn't want to display it...
	def set_left_pane_visibility(self):
		chk = self.window.get_ui_manager().get_widget("/MenuBar/ViewMenu/ViewSidePaneMenu")
		self.config.set('left_pane', 'visible', str(chk.get_active()))

	# Plugin deactivation
	def deactivate(self):
		if False == self.delete:
			if self.show:
				self.on_gedit_delete()
			else:
				self.destroy_right_pane()
		self.remove_menu()
#		self.action_group = None # Ugly but can cause a seg fault...
		self.window = None
		self.popup = None
		self.plugin = None

	# Transfer all right tabs to the left pane & destroy the right pane
	def destroy_right_pane(self):
		for str_index in self.right_tab_indexes:
			try:
				index = int(str_index)
				self.transfer_tab(self.right_pane, self.left_pane, self.items[index], self.labels[index], self.images[index])
			except IndexError:
				True
		self.new_hpaned.remove(self.old_hpaned)
		self.gbox.remove(self.new_hpaned)
		self.gbox.add(self.old_hpaned)

	def update_ui(self):
		return

	# Insert right pane items in view menu
	def insert_menu(self):
		manager = self.window.get_ui_manager()
		self.action_group = gtk.ActionGroup("RightPaneActionGroup1")
		rightpane_action = gtk.ToggleAction(name="ViewRightSidePane", label="Right Side Pane", tooltip="Right Pane", stock_id=None)
		rightpane_action.connect("activate", lambda a: self.display_right_pane())
		self.action_group.add_toggle_actions([("ViewRightSidePane", None, _("Right Side Pane"), "<Ctrl>F8", _("Right Pane"), self.display_right_pane) ])
		managerightpane_action = gtk.Action(name="ManageRightSidePane", label="Manage Left & Right Panes", tooltip="Left & Right Pane Manager", stock_id=None)
		managerightpane_action.connect("activate", lambda a: self.display_popup())
		self.action_group.add_action_with_accel(managerightpane_action, "<Ctrl>F10")
		manager.insert_action_group(self.action_group, -1)
		self.ui_id = manager.new_merge_id()
		manager.add_ui_from_string(ui_str)
		
		group2 = gtk.ActionGroup("PythonPluginActions")
		action2 = gtk.Action(name="Python",
                                          label="Python",
                                          tooltip="All Python Plugins",
                                          stock_id=None)
		group2.add_action(action2)
		 
		manager.insert_action_group(group2, -1)  
		
		manager.ensure_update()

	# Position the items in the view menu
	def position_items_in_menu(self):
		items = self.view_menu.get_children()
		pos = len(items) - 2
		self.view_menu.reorder_child(items[pos - 2], 4)
		for i in range(2):
			self.view_menu.reorder_child(items[pos - i], 6)

	# Remove the right pane items in view menu
	def remove_menu(self):
		if self.window:
			manager = self.window.get_ui_manager()
			manager.remove_ui(self.ui_id)
			manager.remove_action_group(self.action_group)
			manager.ensure_update()

	# Save preferences
	def save_prefs(self):
		f = open(PREFS_PATH, 'w')
		self.config.write(f)
		f.close()

	# Load preferences
	def read_prefs(self):
		self.config.read([PREFS_PATH, 'test.ini'])
		if False == self.config.has_section('right_pane'):
			self.config.add_section('right_pane')
		if False == self.config.has_section('left_pane'):
			self.config.add_section('left_pane')

	# Display the left pane only if preference option is True
	def restore_left_pane_visibility(self):
		if self.config.has_option('left_pane', 'visible') and not self.config.getboolean('left_pane', 'visible'):
			chk = self.window.get_ui_manager().get_widget("/MenuBar/ViewMenu/ViewSidePaneMenu")
			chk.set_active(False)
			self.left_pane.set_property("visible", False)

	# Display the right pane
	def display_right_pane(self, checkbox):
		self.config.set('right_pane', 'visible', str(checkbox.get_active()))
		self.right_pane.set_property("visible", checkbox.get_active())
		if not self.config.has_option('right_pane', 'init'):
			self.config.set('right_pane', 'init', 'True')
			self.display_popup()
		self.save_prefs()

	# Deactive the checkbox in the menu and set the preference option
	def on_close_right_pane(self, widget):
		if self.window:
			chk = self.window.get_ui_manager().get_widget("/MenuBar/ViewMenu/ViewRightSidePaneMenu")
			chk.set_active(False)
			self.config.set('right_pane', 'visible', 'False')
			self.save_prefs()

	# Left-right pane manager
	def display_popup(self):
		if not self.config.has_option('right_pane', 'init'):
			self.config.set('right_pane', 'init', 'True')
		if self.popup:
			self.popup.show()

	# Build popup elements
	def build_popup(self):
		self.popup = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		self.popup.set_title("Left-Right Pane Manager (Ctrl+F10)")
		self.popup.set_position(gtk.WIN_POS_CENTER)
		self.popup.set_type_hint(gtk.gdk.DECOR_BORDER)
		self.popup.set_destroy_with_parent(True)
		self.popup.set_deletable(True)
		self.popup.set_icon_name(gtk.STOCK_PREFERENCES)
		self.popup.connect('delete_event', self.on_popup_close, None)
		paddingH = gtk.HBox()
		paddingH.show()
		paddingV = gtk.VBox()
		paddingV.show()
		self.popup_tab_list.show()
		paddingH.pack_start(paddingV, True, True, 15)
		paddingV.pack_start(self.popup_tab_list, True, True, 15)
		self.popup.add(paddingH)
		index = 0
		for lbl in self.labels:
			self.add_tab(lbl, self.images[index], index)
			index += 1

	# Tab line info in popup
	def add_tab(self, text, img, index):
		box = gtk.HBox()
		box.set_homogeneous(False)
		box.show()
		self.popup_tab_list.pack_start(box, False, True, 5)
		img = self.clone_image(img)
		img.show()
		box.pack_start(img, False, True, 5)
		label = gtk.Label(text)
		label.set_alignment(0, 0.5)
		label.show()
		box.pack_start(label, True, True, 5)
		box2 = gtk.HBox()
		box2.set_homogeneous(True)
		box2.show()
		box.pack_start(box2, False, True, 0)
		left = gtk.RadioButton(None, label='Left')
		left.show()
		self.left_radios.append(left)
		left.connect('toggled', self.on_click_left)
		box2.pack_start(left, True, True, 5)
		right = gtk.RadioButton(left, label='Right')
		right.show()
		if self.right_tab_indexes.count(str(index)) > 0:
			right.set_active(True)
		self.right_radios.append(right)
		right.connect('toggled', self.on_click_right)
		box2.pack_start(right, True, True, 5)

	# Don't destroy the popup. Just hide it.
	def on_popup_close(self, widget, event, data=None):
		self.popup.hide()
		return True

	# Transfer a left pane tab to the right pane
	def on_click_left(self, widget):
		if not widget.get_active():
			return
		index = self.left_radios.index(widget)
		self.transfer_tab(self.right_pane, self.left_pane, self.items[index], self.labels[index], self.images[index])
		self.config.remove_option('right_pane', 'tab' + str(index))
		self.right_tab_indexes.remove(str(index))
		if 0 == len(self.right_tab_indexes):
			self.config.remove_option('right_pane', 'tabs')
		else:
			self.config.set('right_pane', 'tabs', ','.join(self.right_tab_indexes))
		self.save_prefs()
		return

	# Transfer a right pane tab to the left pane
	def on_click_right(self, widget):
		if not widget.get_active():
			return
		index = self.right_radios.index(widget)
		self.transfer_tab(self.left_pane, self.right_pane, self.items[index], self.labels[index], self.images[index])
		self.config.set('right_pane', 'tab' + str(index), self.labels[index])
		self.right_tab_indexes.append(str(index))
		self.config.set('right_pane', 'tabs', ','.join(self.right_tab_indexes))
		self.save_prefs()
		return

	# Insert the pane in gedit
	def insert_right_pane(self):
		if self.config.has_option('right_pane', 'width'):
			self.right_pane.set_size_request(self.config.getint('right_pane', 'width'), -1)
		else:
			self.right_pane.set_size_request(DEFAULT_WIDTH, -1)
		self.new_hpaned.show()
		if self.config.has_option('right_pane', 'visible') and self.config.getboolean('right_pane', 'visible'):
			chk = self.window.get_ui_manager().get_widget("/MenuBar/ViewMenu/ViewRightSidePaneMenu")
			chk.set_active(True)
			self.right_pane.show()
		self.right_pane.connect('hide', self.on_close_right_pane)
		self.gbox.remove(self.old_hpaned)
		self.new_hpaned.pack1(self.old_hpaned, True, True)
		self.new_hpaned.pack2(self.right_pane, False, True)
		self.right_pane.connect('size_allocate', self.on_resize_pane)
		self.gbox.pack_start(self.new_hpaned, True, True, 0)

	# Save the right pane width
	def on_resize_pane(self, widget, size):
		self.config.set('right_pane', 'width', str(size.width))
		self.save_prefs()

	# Clone image
	def clone_image(self, image):
		storage = image.get_storage_type()
		if storage == gtk.IMAGE_PIXMAP:
			img, mask = image.get_pixmap()
			return gtk.image_new_from_pixmap(img, mask)
		if storage == gtk.IMAGE_IMAGE:
			img, mask = image.get_image()
			return gtk.image_new_from_image(img, mask)
		if storage == gtk.IMAGE_PIXBUF:
			return gtk.image_new_from_pixbuf(image.get_pixbuf())
		if storage == gtk.IMAGE_STOCK:
			img, size = image.get_stock()
			return gtk.image_new_from_stock(img, size)
		if storage == gtk.IMAGE_ICON_SET:
			img, size = image.get_icon_set()
			return gtk.image_new_from_icon_set(img, size)
		if storage == gtk.IMAGE_ANIMATION:
			return gtk.image_new_from_animation(image.get_animation())
		if storage == gtk.IMAGE_ICON_NAME:
			img, size = image.get_icon_name()
			return gtk.image_new_from_icon_name(img, size)
#		if storage == gtk.IMAGE_EMPTY:
		img = gtk.Image()
		img.set_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_MENU)
		return img

class RightPanePlugin(gedit.Plugin):
	DATA_TAG = "RightPanePluginInstance"

	def __init__(self):
		gedit.Plugin.__init__(self)

	def _get_instance(self, window):
		return window.get_data(self.DATA_TAG)

	def _set_instance(self, window, instance):
		window.set_data(self.DATA_TAG, instance)

	def activate(self, window):
		self._set_instance(window, RightPanePluginInstance(self, window))

	def deactivate(self, window):
		self._get_instance(window).deactivate()
		self._set_instance(window, None)

	def update_ui(self, window):
		self._get_instance(window).update_ui()
