# -*- encoding:utf-8 -*-


# findadvance_ui.py
#
#
# Copyright 2010 swatch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#



import sys
try:
	import pygtk
	pygtk.require("2.0")
except:
	pass
try:
	import gtk
	import gtk.glade
	import gtk.gdk
except:
	sys.exit(1)

import os.path
import os
#import pango
import re
#import config_manager
try:
	import gconf
	is_mate = False
except:
	import mateconf as gconf
	is_mate = True


#gtk.glade.bindtextdomain('advancedfind', os.path.join(os.path.dirname(__file__), 'locale'))
#gtk.glade.bindtextdomain('advancedfind', '/usr/share/locale')
#gtk.glade.textdomain('advancedfind')



class AdvancedFindUI(object):
	def __init__(self, plugin):
		try:
			self._instance, self._window = plugin.get_instance()
		except:
			pass

		gladefile = os.path.join(os.path.dirname(__file__),"FindDialog.glade")
		ui = gtk.Builder()
		ui.set_translation_domain('advancedfind')
		ui.add_from_file(gladefile)
		ui.connect_signals({ "on_findDialog_destroy" : self.on_findDialog_destroy_action,
							"on_findDialog_focus_in_event": self.on_findDialog_focus_in_event_action,
							"on_findDialog_focus_out_event" : self.on_findDialog_focus_out_event_action,
							
							"on_findButton_clicked" : self.on_findButton_clicked_action,
							"on_replaceButton_clicked" : self.on_replaceButton_clicked_action,
							"on_findAllButton_clicked" : self.on_findAllButton_clicked_action,
							"on_replaceAllButton_clicked" : self.on_replaceAllButton_clicked_action,
							"on_closeButton_clicked" : self.on_closeButton_clicked_action,
							"on_selectPathButton_clicked" : self.on_selectPathButton_clicked_action,
							"on_selectPathDialogOkButton_clicked" : self.on_selectPathDialogOkButton_clicked_action,
							"on_selectPathDialogCancelButton_clicked" : self.on_selectPathDialogCancelButton_clicked_action,
							
							"on_matchWholeWordCheckbutton_toggled" : self.on_matchWholeWordCheckbutton_toggled_action,
							"on_matchCaseCheckbutton_toggled" : self.on_matchCaseCheckbutton_toggled_action,
							"on_wrapAroundCheckbutton_toggled" : self.on_wrapAroundCheckbutton_toggled_action,
							"on_followCurrentDocCheckbutton_toggled" : self.on_followCurrentDocCheckbutton_toggled_action,
							"on_includeSubfolderCheckbutton_toggled" : self.on_includeSubfolderCheckbutton_toggled_action,
							"on_regexSearchCheckbutton_toggled" : self.on_regexSearchCheckbutton_toggled_action,
							
							"on_forwardRadiobutton_toggled" : self.directionRadiobuttonGroup_action,
							"on_backwardRadiobutton_toggled" : self.directionRadiobuttonGroup_action,
							
							"on_currentFileRadiobutton_toggled" : self.scopeRadiobuttonGroup_action,
							"on_allFilesRadiobutton_toggled" : self.scopeRadiobuttonGroup_action,
							"on_allFilesInPathRadiobutton_toggled" : self.scopeRadiobuttonGroup_action,
							"on_currentSelectionRadiobutton_toggled" : self.scopeRadiobuttonGroup_action })

		self.findDialog = ui.get_object("findDialog")
		#self.findDialog.set_keep_above(True)
		self.findDialog.set_transient_for(self._window)

		accelgroup = gtk.AccelGroup()
		#key, modifier = gtk.accelerator_parse('Escape')
		#accelgroup.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.esc_accel_action)
		key, modifier = gtk.accelerator_parse('Return')
		accelgroup.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.return_accel_action)
		key, modifier = gtk.accelerator_parse('KP_Enter')
		accelgroup.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.return_accel_action)
		self.findDialog.add_accel_group(accelgroup)

		self.findTextEntry = ui.get_object("findTextComboboxentry")
		#self.findTextListstore = ui.get_object("findTextListstore")
		#find_cell = gtk.CellRendererText()
		#self.findTextEntry.pack_start(find_cell, True)
		#self.findTextEntry.add_attribute(find_cell, 'text', 0)
		self.findTextEntry.set_text_column(0)
		self.findTextEntry.child.set_icon_from_stock(1, "gtk-clear")
		self.findTextEntry.child.connect('icon-press', self.findEntryIconPress)
		try:
			for find_text in self._instance.find_history:
				self.findTextEntry.prepend_text(find_text)
		except:
			pass

		self.replaceTextEntry = ui.get_object("replaceTextComboboxentry")
		#self.replaceTextListstore = ui.get_object("replaceTextListstore")
		#replace_cell = gtk.CellRendererText()
		#self.replaceTextEntry.pack_start(replace_cell, True)
		#self.replaceTextEntry.add_attribute(replace_cell, 'text', 0)
		self.replaceTextEntry.set_text_column(0)
		self.replaceTextEntry.child.set_icon_from_stock(1, "gtk-clear")
		self.replaceTextEntry.child.connect('icon-press', self.replaceEntryIconPress)
		try:
			for replace_text in self._instance.replace_history:
				self.replaceTextEntry.prepend_text(replace_text)
		except:
			pass
			
		self.filterComboboxentry = ui.get_object("filterComboboxentry")
		self.filterComboboxentry.set_text_column(0)
		self.filterComboboxentry.child.set_text("*")
		#self.filterComboboxentry.prepend_text("*")
		self.filterComboboxentry.child.set_icon_from_stock(1, "gtk-clear")
		self.filterComboboxentry.child.connect('icon-press', self.filterEntryIconPress)
		try:
			for file_filter in self._instance.file_type_history:
				self.filterComboboxentry.prepend_text(file_filter)
		except:
			pass
			
		self.selectPathFilechooserdialog = ui.get_object("selectPathFilechooserdialog")
		
		self.pathComboboxentry = ui.get_object("pathComboboxentry")
		self.pathComboboxentry.set_text_column(0)
		self.pathComboboxentry.child.set_icon_from_stock(1, "gtk-clear")
		self.pathComboboxentry.child.connect('icon-press', self.pathEntryIconPress)
		filebrowser_root = self.get_filebrowser_root()
		if filebrowser_root != None and self._instance.find_options['ROOT_FOLLOW_FILEBROWSER'] == True:
			self.pathComboboxentry.child.set_text(filebrowser_root)
		else:
			self.pathComboboxentry.child.set_text(self.selectPathFilechooserdialog.get_filename())
			
		try:
			for path in self._instance.file_path_history:
				self.pathComboboxentry.prepend_text(path)
		except:
			pass
		
		self.pathExpander = ui.get_object("pathExpander")
		self.pathExpander.set_expanded(self._instance.find_dlg_setting['PATH_EXPANDED'])		
		
		self.matchWholeWordCheckbutton = ui.get_object("matchWholeWordCheckbutton")
		self.matchCaseCheckbutton = ui.get_object("matchCaseCheckbutton")
		self.wrapAroundCheckbutton = ui.get_object("wrapAroundCheckbutton")
		self.followCurrentDocCheckbutton = ui.get_object("followCurrentDocCheckbutton")
		self.includeSubfolderCheckbutton = ui.get_object("includeSubfolderCheckbutton")
		self.regexSearchCheckbutton = ui.get_object("regexSearchCheckbutton")
		
		self.optionsExpander = ui.get_object("optionsExpander")
		self.optionsExpander.set_expanded(self._instance.find_dlg_setting['OPTIONS_EXPANDED'])

		self.forwardRadiobutton = ui.get_object("forwardRadiobutton")
		self.backwardRadiobutton = ui.get_object("backwardRadiobutton")
		if self._instance.forwardFlg == True:
			self.forwardRadiobutton.set_active(True)
		else:
			self.backwardRadiobutton.set_active(True)

		self.currentFileRadiobutton = ui.get_object("currentFileRadiobutton")
		self.allFilesRadiobutton = ui.get_object("allFilesRadiobutton")
		self.allFilesInPathRadiobutton = ui.get_object("allFilesInPathRadiobutton")
		self.currentSelectionRadiobutton = ui.get_object("currentSelectionRadiobutton")
		if self._instance.scopeFlg == 0:
			self.currentFileRadiobutton.set_active(True)
		elif self._instance.scopeFlg == 1:
			self.allFilesRadiobutton.set_active(True)
		elif self._instance.scopeFlg == 2:
			self.allFilesInPathRadiobutton.set_active(True)
		elif self._instance.scopeFlg == 3:
			self.currentSelectionRadiobutton.set_active(True)

		self.findButton = ui.get_object("findButton")
		self.replaceButton = ui.get_object("replaceButton")
		self.findAllButton = ui.get_object("findAllButton")
		self.replaceAllButton = ui.get_object("replaceAllButton")
		self.closeButton = ui.get_object("closeButton")
		self.selectPathButton = ui.get_object("selectPathButton")

		self.findDialog.show()

		self.matchWholeWordCheckbutton.set_active(self._instance.find_options['MATCH_WHOLE_WORD'])
		self.matchCaseCheckbutton.set_active(self._instance.find_options['MATCH_CASE'])
		self.wrapAroundCheckbutton.set_active(self._instance.find_options['WRAP_AROUND'])
		self.followCurrentDocCheckbutton.set_active(self._instance.find_options['FOLLOW_CURRENT_DOC'])
		self.includeSubfolderCheckbutton.set_active(self._instance.find_options['INCLUDE_SUBFOLDER'])
		self.regexSearchCheckbutton.set_active(self._instance.find_options['REGEX_SEARCH'])

		if self._instance.find_options['FOLLOW_CURRENT_DOC'] == True:
			self.pathComboboxentry.child.set_text(os.path.dirname(self._instance._window.get_active_document().get_uri_for_display()))
			
	def on_findDialog_destroy_action(self, object):
		try:
			self._instance.find_dlg_setting['PATH_EXPANDED'] = self.pathExpander.get_expanded()
			self._instance.find_dlg_setting['OPTIONS_EXPANDED'] = self.optionsExpander.get_expanded()
			self._instance.find_ui = None
		except:
			pass
			
	def findEntryIconPress(self, object, icon_pos, event):
		self.findTextEntry.get_model().clear()
		self._instance.find_history = []

	def replaceEntryIconPress(self, object, icon_pos, event):
		self.replaceTextEntry.get_model().clear()
		self._instance.replace_history = []
		
	def filterEntryIconPress(self, object, icon_pos, event):
		self.filterComboboxentry.get_model().clear()
		self._instance.file_type_history = []
		
	def pathEntryIconPress(self, object, icon_pos, event):
		self.pathComboboxentry.get_model().clear()
		self._instance.file_path_history = []
			
	def on_findDialog_focus_in_event_action(self, object, event):
		object.set_opacity(1)

	def on_findDialog_focus_out_event_action(self, object, event):
		object.set_opacity(0.5)
		
	#def esc_accel_action(self, accelgroup, window, key, modifier):
		#window.hide()
		
	def return_accel_action(self, accelgroup, window, key, modifier):
		#self.on_findButton_clicked_action(None)
		self.on_findAllButton_clicked_action(None)
		
	def main(self):
		gtk.main()

	def do_events(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
			
	def add_combobox_list(self):
		find_text = self.findTextEntry.get_active_text()
		replace_text = self.replaceTextEntry.get_active_text()
		file_pattern = self.filterComboboxentry.get_active_text()
		path = self.pathComboboxentry.get_active_text()
		self._instance.current_search_pattern = find_text
		self._instance.current_replace_text = replace_text
		#self._instance.current_file_pattern = file_pattern
		#self._instance.current_path = path
		
		if find_text != "" and find_text not in self._instance.find_history:
			#if len(self.findTextEntry.get_model()) == 10:
			if len(self._instance.find_history) == 10:
				self._instance.find_history[0:1] = []
				self.findTextEntry.remove_text(9)
			self._instance.find_history.append(find_text)
			self.findTextEntry.prepend_text(find_text)
			
		if replace_text != "" and replace_text not in self._instance.replace_history:
			#if len(self.replaceTextEntry.get_model()) == 10:
			if len(self._instance.replace_history) == 10:
				self._instance.replace_history[0:1] = []
				self.replaceTextEntry.remove_text(9)
			self._instance.replace_history.append(replace_text)
			self.replaceTextEntry.prepend_text(replace_text)
			
		if self._instance.scopeFlg == 2: #files in directory
			if file_pattern != "" and file_pattern not in self._instance.file_type_history:
				#if len(self.filterComboboxentry.get_model()) == 10:
				if len(self._instance.file_type_history) == 10:
					self._instance.file_type_history[0:1] = []
					self.filterComboboxentry.remove_text(9)
				self._instance.file_type_history.append(file_pattern)
				self.filterComboboxentry.prepend_text(file_pattern)
			
			if path != "" and path not in self._instance.file_path_history:
				#if len(self.pathComboboxentry.get_model()) == 10:
				if len(self._instance.file_path_history) == 10:
					self._instance.file_path_history[0:1] = []
					self.pathComboboxentry.remove_text(9)
				self._instance.file_path_history.append(path)
				self.pathComboboxentry.prepend_text(path)

	# button actions       
	def on_findButton_clicked_action(self, object):
		doc = self._instance._window.get_active_document()
		if not doc:
			return
		
		search_pattern = self.findTextEntry.get_active_text()
		if search_pattern == "":
			return
		
		self.add_combobox_list()
		self._instance.advanced_find_in_doc(doc, search_pattern, self._instance.find_options, self._instance.forwardFlg)
		
	def on_replaceButton_clicked_action(self, object):
		doc = self._instance._window.get_active_document()
		if not doc:
			return
			
		search_pattern = self.findTextEntry.get_active_text()
		if search_pattern == "":
			return
		
		self.add_combobox_list()
		self._instance.advanced_find_in_doc(doc, search_pattern, self._instance.find_options, self._instance.forwardFlg, True)

	def on_findAllButton_clicked_action(self, object):
		search_pattern = self.findTextEntry.get_active_text()
		if search_pattern == "":
			return
			
		doc = self._instance._window.get_active_document()
		if not doc:
			return
		
		self._instance.set_bottom_panel_label(_('Finding...'), gtk.gdk.PixbufAnimation(os.path.join(os.path.dirname(__file__), 'loading.gif')))
		self._instance._results_view.set_sensitive(False)
		self._instance.show_bottom_panel()
		self.findDialog.hide()
		self.do_events()
			
		self.add_combobox_list()
		
		it = self._instance._results_view.append_find_pattern(search_pattern)
		
		if self._instance.scopeFlg == 0: #current document
			self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options)
			self._instance._results_view.show_find_result()
		elif self._instance.scopeFlg == 1: #all opened documents
			docs = self._instance._window.get_documents()
			for doc in docs:
				self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options)
				self.do_events()
			self._instance._results_view.show_find_result()
		elif self._instance.scopeFlg == 2: #files in directory
			dir_path = self.pathComboboxentry.get_active_text()
			file_pattern = self.filterComboboxentry.get_active_text()
			self._instance.find_all_in_dir(it, dir_path, file_pattern, search_pattern, self._instance.find_options)
			self._instance._results_view.show_find_result()
		elif self._instance.scopeFlg == 3: #current selected text
			self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options, False, True)
			self._instance._results_view.show_find_result()

		self._instance.set_bottom_panel_label()
		self._instance._results_view.set_sensitive(True)

	def on_replaceAllButton_clicked_action(self, object):
		search_pattern = self.findTextEntry.get_active_text()
		if search_pattern == "":
			return
			
		doc = self._instance._window.get_active_document()
		if not doc:
			return
			
		self._instance.set_bottom_panel_label(_('Replacing...'), gtk.gdk.PixbufAnimation(os.path.join(os.path.dirname(__file__), 'loading.gif')))
		self._instance._results_view.set_sensitive(False)
		self._instance.show_bottom_panel()
		self.findDialog.hide()
		self.do_events()
		
		self.add_combobox_list()

		it = self._instance._results_view.append_find_pattern(search_pattern, True, self.replaceTextEntry.child.get_text())
		
		if self._instance.scopeFlg == 0: #current document
			self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options, True)
			self._instance._results_view.show_find_result()
		elif self._instance.scopeFlg == 1: #all opened documents
			docs = self._instance._window.get_documents()
			for doc in docs:
				self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options, True)
			self._instance._results_view.show_find_result()
		elif self._instance.scopeFlg == 2: #files in directory
			path = str(self._instance._results_view.findResultTreemodel.iter_n_children(None) - 1)
			it = self._instance._results_view.findResultTreemodel.get_iter(path)
			self._instance._results_view.show_find_result()
			self._instance._results_view.findResultTreemodel.set_value(it, 2, _("Replace in this scope is not supported."))
		elif self._instance.scopeFlg == 3: #current selected text
			self._instance.advanced_find_all_in_doc(it, doc, search_pattern, self._instance.find_options, True, True)
			self._instance._results_view.show_find_result()
		
		self._instance.set_bottom_panel_label()
		self._instance._results_view.set_sensitive(True)

	def on_closeButton_clicked_action(self, object):
		self.findDialog.destroy()
		
	def on_selectPathButton_clicked_action(self, object):
		self.selectPathFilechooserdialog.show()

	# select path file chooserr dialog actions
	def on_selectPathDialogOkButton_clicked_action(self, object):
		folder_path = self.selectPathFilechooserdialog.get_filename()
		self.selectPathFilechooserdialog.select_filename(folder_path)
		self.pathComboboxentry.child.set_text(folder_path)
		self.add_combobox_list()
		self.selectPathFilechooserdialog.hide()
		
	def on_selectPathDialogCancelButton_clicked_action(self, object):
		self.selectPathFilechooserdialog.hide()
		
	# find_options    
	def on_matchWholeWordCheckbutton_toggled_action(self, object):
		self._instance.find_options['MATCH_WHOLE_WORD'] = object.get_active()

	def on_matchCaseCheckbutton_toggled_action(self, object):
		self._instance.find_options['MATCH_CASE'] = object.get_active()

	def on_wrapAroundCheckbutton_toggled_action(self, object):
		self._instance.find_options['WRAP_AROUND'] = object.get_active()
		
	def on_followCurrentDocCheckbutton_toggled_action(self, object):
		self._instance.find_options['FOLLOW_CURRENT_DOC'] = object.get_active()
		if object.get_active() == True:
			self.pathComboboxentry.child.set_text(os.path.dirname(self._instance._window.get_active_document().get_uri_for_display()))
		else:
			filebrowser_root = self.get_filebrowser_root()
			if filebrowser_root != None and self._instance.find_options['ROOT_FOLLOW_FILEBROWSER'] == True:
				self.pathComboboxentry.child.set_text(filebrowser_root)
			else:
				self.pathComboboxentry.child.set_text(self.selectPathFilechooserdialog.get_filename())
			
	def on_includeSubfolderCheckbutton_toggled_action(self, object):
		self._instance.find_options['INCLUDE_SUBFOLDER'] = object.get_active()
		
	def on_regexSearchCheckbutton_toggled_action(self, object):
		self._instance.find_options['REGEX_SEARCH'] = object.get_active()


	# radiobutton
	def directionRadiobuttonGroup_action(self, object):
		self._instance.forwardFlg = self.forwardRadiobutton.get_active()

	def scopeRadiobuttonGroup_action(self, object):
		if self.currentFileRadiobutton.get_active() == True:
			self._instance.scopeFlg = 0
		elif self.allFilesRadiobutton.get_active() == True:
			self._instance.scopeFlg = 1
		elif self.allFilesInPathRadiobutton.get_active() == True:
			self._instance.scopeFlg = 2
		elif self.currentSelectionRadiobutton.get_active() == True:
			self._instance.scopeFlg = 3

	# filebrowser integration
	def get_filebrowser_root(self):
		base = u'/apps/gedit-2/plugins/filebrowser/on_load'
		if is_mate:
			base = u'/apps/pluma/plugins/filebrowser/on_load'
		client = gconf.client_get_default()
		client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
		path = os.path.join(base, u'virtual_root')
		val = client.get(path)
		if val != None:
			path_string = val.get_string()
			idx = path_string.find('://') + 3
			return val.get_string()[idx:]
		return None
	


if __name__ == "__main__":
	app = AdvancedFindUI(None)
	app.main()

