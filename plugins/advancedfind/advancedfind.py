# -*- encoding:utf-8 -*-


# findadvance.py
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



import gtk
import gtk.glade
try:
	import gedit
except:
	import pluma as gedit
import os.path
import os
import fnmatch
import subprocess
import urllib
import re
#import pango
#import mimetypes


from advancedfind_ui import AdvancedFindUI
from find_result import FindResultView
import config_manager

#import time


import gettext
APP_NAME = 'advancedfind'
#LOCALE_DIR = '/usr/share/locale'
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')
if not os.path.exists(LOCALE_DIR):
	LOCALE_DIR = '/usr/share/locale'
try:
	t = gettext.translation(APP_NAME, LOCALE_DIR)
	_ = t.gettext
	gtk.glade.bindtextdomain(APP_NAME, LOCALE_DIR)
except:
	pass
#gettext.install(APP_NAME, LOCALE_DIR, unicode=True)


# Menu item example, insert a new item in the Edit menu
ui_str = """<ui>
	<menubar name="MenuBar">
		<menu name="SearchMenu" action="Search">
			<placeholder name="SearchOps_0">
				<menuitem name="advanced_find_active" action="advanced_find_active"/>
				<menuitem name="find_next" action="find_next"/>
				<menuitem name="find_previous" action="find_previous"/>
				<menuitem name="select_find_next" action="select_find_next"/>
				<menuitem name="select_find_previous" action="select_find_previous"/>
			</placeholder>
		</menu>
	</menubar>
</ui>
"""


class AdvancedFindWindowHelper:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		self.find_ui = None
		self.find_history = []
		self.replace_history = []
		self.file_type_history = []
		self.file_path_history = []
		self.current_search_pattern = ""
		self.current_replace_text = ""
		#self.current_file_pattern = ""
		#self.current_path = ""
		self.forwardFlg = True
		self.scopeFlg = 0
		
		'''
		self.result_highlight_tag = gtk.TextTag('result_highlight')
		self.result_highlight_tag.set_properties(foreground='yellow',background='red')
		self.result_highlight_tag.set_property('family', 'Serif')
		self.result_highlight_tag.set_property('size-points', 12)
		self.result_highlight_tag.set_property('weight', pango.WEIGHT_BOLD)
		self.result_highlight_tag.set_property('underline', pango.UNDERLINE_DOUBLE)
		self.result_highlight_tag.set_property('style', pango.STYLE_ITALIC)
		#'''
		
		configfile = os.path.join(os.path.dirname(__file__), "config.xml")
		self.config_manager = config_manager.ConfigManager(configfile)
		self.find_options = self.config_manager.load_configure('FindOption')
		self.config_manager.to_bool(self.find_options)
		
		self.find_dlg_setting = self.config_manager.load_configure('FindGUI')
		self.config_manager.to_bool(self.find_dlg_setting)

		self.shortcuts = self.config_manager.load_configure('Shortcut')
		self.result_highlight = self.config_manager.load_configure('ResultDisplay')
		
		self.result_gui_settings = self.config_manager.load_configure('ResultGUI')
		self.config_manager.to_bool(self.result_gui_settings)
		
		self.find_history = self.config_manager.load_list('FindHistory')
		self.replace_history = self.config_manager.load_list('ReplaceHistory')
		self.file_type_history = self.config_manager.load_list('FilterHistory')
		self.file_path_history = self.config_manager.load_list('PathHistory')

		self._results_view = FindResultView(window, self.result_gui_settings)
		self._window.get_bottom_panel().add_item(self._results_view, _("Advanced Find/Replace"), "gtk-find-and-replace")
		
		self.msgDialog = gtk.MessageDialog(self._window, 
						gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
						gtk.MESSAGE_INFO,
						gtk.BUTTONS_CLOSE,
						None)
		
		# Insert menu items
		self._insert_menu()

	def deactivate(self):
		# Remove any installed menu items
		self._remove_menu()

		self.config_manager.update_configure('FindOption', self.find_options)
		self.config_manager.update_configure('FindGUI', self.find_dlg_setting)
		#self.config_manager.update_configure('Shortcut', self.shortcuts)
		self.config_manager.update_configure('ResultDisplay', self.result_highlight)
		self.result_gui_settings.update(self._results_view.get_show_button_option())
		self.config_manager.update_configure('ResultGUI', self.result_gui_settings)
		self.config_manager.update_list('FindHistory', self.find_history)
		self.config_manager.update_list('ReplaceHistory', self.replace_history)
		self.config_manager.update_list('FilterHistory', self.file_type_history)
		self.config_manager.update_list('PathHistory', self.file_path_history)
		self.config_manager.update_config_file(self.config_manager.config_file)
		
		self._window = None
		self._plugin = None
		self.find_ui = None
		self.find_history = None
		self.replace_history = None
		self.file_type_history = None
		self.file_path_history = None
		self._result_view = None
	
	def _insert_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Create a new action group
		self._action_group = gtk.ActionGroup("AdvancedFindReplaceActions")
		self._action_group.add_actions( [("advanced_find_active", None, _("Advanced Find/Replace"), self.shortcuts['ACTIVATE'], _("Advanced Find/Replace"), self.advanced_find_active),
										("find_next", None, _("Find Next"), self.shortcuts['FIND_NEXT'], _("Find Next"), self.find_next),
										("find_previous", None, _("Find Previous"), self.shortcuts['FIND_PREVIOUS'], _("Find Previous"), self.find_previous),
										("select_find_next", None, _("Select and Find Next"), self.shortcuts['SELECT_FIND_NEXT'], _("Select and Find Next"), self.select_find_next),
										("select_find_previous", None, _("Select and Find Previous"), self.shortcuts['SELECT_FIND_PREVIOUS'], _("Select and Find Previous"), self.select_find_previous)]) 

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

	def show_message_dialog(self, dlg, text):
		dlg.set_property('text', text)
		dlg.run()
		dlg.hide()
		
	def advanced_find_active(self, action):
		doc = self._window.get_active_document()
		if not doc:
			return
			
		try:
			start, end = doc.get_selection_bounds()
			search_text = unicode(doc.get_text(start,end))
		except:
			search_text = self.current_search_pattern

		if self.find_ui == None:
			self.find_ui = AdvancedFindUI(self._plugin)
		else:
			self.find_ui.findDialog.present()
			self.find_ui.findTextEntry.grab_focus()
			
		if search_text != "":
			self.find_ui.findTextEntry.child.set_text(search_text)
		
		if self.current_replace_text != "":
			self.find_ui.replaceTextEntry.child.set_text(self.current_replace_text)
		'''	
		if self.current_file_pattern != "":
			self.find_ui.filterComboboxentry.child.set_text(self.current_file_pattern)
			
		if self.current_path != "":
			self.find_ui.pathComboboxentry.child.set_text(self.current_path)
		#'''

	def create_regex(self, pattern, find_options):
		if find_options['REGEX_SEARCH'] == False:
			pattern = re.escape(unicode(r'%s' % pattern, "utf-8"))
		else:
			pattern = unicode(r'%s' % pattern, "utf-8")
		
		if find_options['MATCH_WHOLE_WORD'] == True:
			pattern = r'\b%s\b' % pattern
			
		if find_options['MATCH_CASE'] == True:
			regex = re.compile(pattern, re.MULTILINE)
		else:
			regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
		
		return regex
		
	def advanced_find_in_doc(self, doc, search_pattern, find_options, forward_flg = True, replace_flg = False, around_flg = False):
		if search_pattern == "":
			return
		
		regex = self.create_regex(search_pattern, find_options)
		
		if doc.get_has_selection():
			sel_start, sel_end = doc.get_selection_bounds()
			match = regex.search(doc.get_text(sel_start, sel_end))
			if match and replace_flg == True:
				if find_options['REGEX_SEARCH'] == False:
					replace_text = unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8')
				else:
					replace_text = match.expand(unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8'))
				doc.delete_selection(False, False)
				doc.insert_at_cursor(replace_text)
				replace_flg = False
			else:
				if forward_flg == True:
					doc.place_cursor(sel_end)
				else:
					doc.place_cursor(sel_start)
			
		view = self._window.get_active_view()
		start, end = doc.get_bounds()
		text = unicode(doc.get_text(start, end), 'utf-8')
		around_flg = False
		
		if forward_flg == True:
			start_pos = doc.get_iter_at_mark(doc.get_insert()).get_offset()
			end_pos = doc.get_end_iter().get_offset()
			match = regex.search(text, start_pos, end_pos)
			if match:
				result_start = doc.get_iter_at_offset(match.start())
				result_end = doc.get_iter_at_offset(match.end())
				doc.select_range(result_start, result_end)
				view.scroll_to_cursor()
		else:
			start_pos = doc.get_start_iter().get_offset()
			end_pos = doc.get_iter_at_mark(doc.get_insert()).get_offset()
			results = []
			match = regex.search(text, start_pos, end_pos)
			while match:
				results.append(match.span())
				start_pos = match.end() + 1
				match = regex.search(text, start_pos, end_pos)
			results_len = len(results)
			if results_len > 0:
				result_start = doc.get_iter_at_offset(results[results_len-1][0])
				result_end = doc.get_iter_at_offset(results[results_len-1][1])
				doc.select_range(result_start, result_end)
				view.scroll_to_cursor()
				
		if not doc.get_has_selection():
			if find_options['WRAP_AROUND'] == True and around_flg == False:
				if forward_flg == True:
					doc.place_cursor(doc.get_start_iter())
				else:
					doc.place_cursor(doc.get_end_iter())
				self.advanced_find_in_doc(doc, search_pattern, find_options, forward_flg, replace_flg, True)
			else:
				self.show_message_dialog(self.msgDialog, _("Nothing is found."))
				
		if replace_flg == True and doc.get_has_selection():
			if find_options['REGEX_SEARCH'] == False:
				replace_text = unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8')
			else:
				replace_text = match.expand(unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8'))
			doc.delete_selection(False, False)
			doc.insert_at_cursor(replace_text)
			replace_end = doc.get_iter_at_mark(doc.get_insert())
			replace_start = doc.get_iter_at_offset(replace_end.get_offset() - len(replace_text))
			doc.select_range(replace_start, replace_end)
			view.scroll_to_cursor()

	def auto_select_word(self, pattern=r'[_a-zA-Z][_a-zA-Z0-9]*'):
		doc = self._window.get_active_document()
		if doc.get_has_selection():
			start, end = doc.get_selection_bounds()
			return doc.get_text(start, end)
		else:
			current_iter = doc.get_iter_at_mark(doc.get_insert())
			line_num = current_iter.get_line()
			line_start = doc.get_iter_at_line(line_num)
			line_text = doc.get_text(line_start, doc.get_iter_at_line(line_num + 1))
			line_start_pos = line_start.get_offset()
			matches = re.finditer(pattern, line_text)
			for match in matches:
				if current_iter.get_offset() in range(line_start_pos + match.start(), line_start_pos + match.end() + 1):
					return match.group(0)
			return ''
					
	def find_next(self, action):
		self.advanced_find_in_doc(self._window.get_active_document(), self.current_search_pattern, self.find_options, True, False, False)
	
	def find_previous(self, action):	
		self.advanced_find_in_doc(self._window.get_active_document(), self.current_search_pattern, self.find_options, False, False, False)
		
	def select_find_next(self, action):
		#print self.auto_select_word()
		self.advanced_find_in_doc(self._window.get_active_document(), self.auto_select_word(), self.find_options, True, False, False)

	def select_find_previous(self, action):
		#print self.auto_select_word()
		self.advanced_find_in_doc(self._window.get_active_document(), self.auto_select_word(), self.find_options, False, False, False)
		
	def advanced_find_all_in_doc(self, parent_it, doc, search_pattern, find_options, replace_flg = False, selection_only = False):
		if search_pattern == "":
			return
		
		regex = self.create_regex(search_pattern, find_options)

		self.result_highlight_off(doc)
		start, end = doc.get_bounds()
		text = unicode(doc.get_text(start, end), 'utf-8')
		
		start_pos = 0
		end_pos = end.get_offset()

		if selection_only == True:
			try:
				sel_start, sel_end = doc.get_selection_bounds()
			except:
				return
				
			if sel_start and sel_end:
				start_pos = sel_start.get_offset()
				end_pos = sel_end.get_offset()
			else:
				return

		tree_it = None
		match = regex.search(text, start_pos, end_pos)
		if match:
			if not tree_it:
				doc_uri = doc.get_uri()
				if doc_uri == None:
					uri = ''
				else:
					uri = urllib.unquote(doc.get_uri()).decode('utf-8')
				tab = gedit.tab_get_from_document(doc)
				tree_it = self._results_view.append_find_result_filename(parent_it, doc.get_short_name_for_display(), tab, uri)

			if replace_flg == False:
				while(match):
					line_num = doc.get_iter_at_offset(match.start()).get_line()
					line_start_pos = doc.get_iter_at_line(line_num).get_offset()
					'''
					line_end_pos = doc.get_iter_at_line(doc.get_iter_at_offset(match.end()).get_line()+1).get_offset()
					if line_end_pos == line_start_pos:
						line_end_pos = end_pos
					#'''
					match_end_line_cnt = doc.get_iter_at_offset(match.end()).get_line() + 1
					if match_end_line_cnt == doc.get_line_count():
						line_end_pos = end_pos
					else:
						line_end_pos = doc.get_iter_at_line(match_end_line_cnt).get_offset()
					line_text = text[line_start_pos:line_end_pos]
					self._results_view.append_find_result(tree_it, str(line_num+1), line_text, match.start(), match.end()-match.start(), "", line_start_pos)
					if match.start() == match.end():
						start_pos = match.end() + 1
					else:
						start_pos = match.end()
					if start_pos > end_pos:
						#print 'EOF'
						break
					match = regex.search(text, start_pos, end_pos)
			else:
				results = []
				replace_offset = 0
				doc.begin_user_action()
				while(match):
					if find_options['REGEX_SEARCH'] == False:
						replace_text = unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8')
					else:
						replace_text = match.expand(unicode(self.find_ui.replaceTextEntry.get_active_text(), 'utf-8'))
					if match.start() == match.end():
						break
					replace_start_pos = match.start() + replace_offset
					replace_end_pos = match.end() + replace_offset
					replace_start = doc.get_iter_at_offset(replace_start_pos)
					replace_end = doc.get_iter_at_offset(replace_end_pos)
					doc.delete(replace_start, replace_end)
					doc.insert(replace_start, replace_text)
					replace_text_len = len(replace_text)
					results.append([replace_start_pos, replace_text_len])
					replace_offset += replace_text_len - (match.end() - match.start())
					start_pos = match.end()
					if start_pos > end_pos:
						#print 'EOF'
						break
					match = regex.search(text, start_pos, end_pos)
				doc.end_user_action()
				
				start, end = doc.get_bounds()
				text = unicode(doc.get_text(start, end), 'utf-8')

				for result in results:
					line_num = doc.get_iter_at_offset(result[0]).get_line()
					line_start_pos = doc.get_iter_at_line(line_num).get_offset()
					#line_end_pos = result[0]+result[1]
					'''
					line_end_pos = doc.get_iter_at_line(doc.get_iter_at_offset(result[0]+result[1]).get_line()+1).get_offset()
					if line_end_pos == line_start_pos:
						line_end_pos = end_pos
					#'''
					match_end_line_cnt = doc.get_iter_at_offset(result[0]+result[1]).get_line() + 1
					if match_end_line_cnt == doc.get_line_count():
						line_end_pos = end_pos
					else:
						line_end_pos = doc.get_iter_at_line(match_end_line_cnt).get_offset()
					line_text = text[line_start_pos:line_end_pos]
					self._results_view.append_find_result(tree_it, str(line_num+1), line_text, result[0], result[1], "", line_start_pos, True)
			
		self.result_highlight_on(tree_it)
	
	def check_file_pattern(self, path, pattern_text):
		pattern_list = re.split('\s*\|\s*', pattern_text)
		for pattern in pattern_list:
			if fnmatch.fnmatch(os.path.basename(path).strip(), pattern):
				return True
		return False
		
	def find_all_in_dir(self, parent_it, dir_path, file_pattern, search_pattern, find_options, replace_flg = False):
		#start_time = time.time()
		if search_pattern == "":
			return
			
		#d_list = []
		file_list = []
		
		if find_options['INCLUDE_SUBFOLDER'] == True:
			grep_cmd = ['grep', '-E', '-l', '-R', search_pattern, dir_path]
		else:
			grep_cmd = ['grep', '-E', '-l', search_pattern, dir_path]
		p = subprocess.Popen(grep_cmd, stdout=subprocess.PIPE)
		for f in p.stdout:
			if self.check_file_pattern(f, unicode(file_pattern, 'utf-8')):
				file_list.append(f[:-1])
		
		'''
		for root, dirs, files in os.walk(unicode(dir_path, 'utf-8')):
			for d in dirs:
				d_list.append(os.path.join(root, d))
			for f in files:
				if self.check_file_pattern(f, unicode(file_pattern, 'utf-8')):
					if find_options['INCLUDE_SUBFOLDER'] == True:
						file_list.append(os.path.join(root, f))
					else:
						if os.path.dirname(f) not in d_list:
							file_list.append(os.path.join(root, f))
				self.find_ui.do_events()
		#'''
					
		#mid_time = time.time()
		#print 'Use ' + str(mid_time-start_time) + ' seconds to find files.'
					
		for file_path in file_list:
			if os.path.isfile(file_path):
				temp_doc = gedit.Document()
				#file_uri = "file://" + urllib.pathname2url(file_path.encode('utf-8'))
				file_uri = ('file://' + file_path).encode('utf-8')
				try:
					temp_doc.load(file_uri, gedit.encoding_get_from_charset('utf-8'), 0, False)
				except:
					print 'Can not open ' + file_uri + '.'
					continue
				f_temp = open(file_path, 'r')
				try:
					text = unicode(f_temp.read(), 'utf-8')
				except:
					text = f_temp.read()
				f_temp.close()
				temp_doc.set_text(text)
			
				self.advanced_find_all_in_doc(parent_it, temp_doc, search_pattern, find_options, replace_flg)
				self.find_ui.do_events()

		#end_time = time.time()						
		#print 'Use ' + str(end_time-mid_time) + ' seconds to find results.'
		#print 'Total use ' + str(end_time-start_time) + ' seconds.'
						
	def result_highlight_on(self, file_it):
		if file_it == None:
			return

		if self._results_view.findResultTreemodel.iter_has_child(file_it):
			tab = self._results_view.findResultTreemodel.get_value(file_it, 3)
			if not tab:
				return
			for n in range(0,self._results_view.findResultTreemodel.iter_n_children(file_it)):
				it = self._results_view.findResultTreemodel.iter_nth_child(file_it, n)
				
				result_start = self._results_view.findResultTreemodel.get_value(it, 4)
				result_len = self._results_view.findResultTreemodel.get_value(it, 5)
				doc = tab.get_document()
				if doc.get_tag_table().lookup('result_highlight') == None:
					tag = doc.create_tag("result_highlight", foreground=self.result_highlight['FOREGROUND_COLOR'], background=self.result_highlight['BACKGROUND_COLOR'])
				doc.apply_tag_by_name('result_highlight', doc.get_iter_at_offset(result_start), doc.get_iter_at_offset(result_start + result_len))
		
	def result_highlight_off(self, doc):
		start, end = doc.get_bounds()
		if doc.get_tag_table().lookup('result_highlight') == None:
			tag = doc.create_tag("result_highlight", foreground=self.result_highlight['FOREGROUND_COLOR'], background=self.result_highlight['BACKGROUND_COLOR'])
		doc.remove_tag_by_name('result_highlight', start, end)

	def show_bottom_panel(self):
		panel = self._window.get_bottom_panel()
		if panel.get_property("visible") == False:
			panel.set_property("visible", True)
		panel.activate_item(self._results_view)
		
	def set_bottom_panel_label(self, text = None, icon = None):
		tab = self._results_view
		if text:
			tab.get_parent().get_tab_label(tab).get_children()[0].get_child().get_children()[1].set_text(_(text))
		else:
			tab.get_parent().get_tab_label(tab).get_children()[0].get_child().get_children()[1].set_text(_("Advanced Find/Replace"))
		if icon:
			tab.get_parent().get_tab_label(tab).get_children()[0].get_child().get_children()[0].set_from_animation(icon)
		else:
			tab.get_parent().get_tab_label(tab).get_children()[0].get_child().get_children()[0].set_from_icon_name('gtk-find-and-replace', gtk.ICON_SIZE_MENU)
		
		
		
