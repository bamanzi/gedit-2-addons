# -*- encoding:utf-8 -*-


# find_result.py
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
except:
    sys.exit(1)

try:
	import gedit
except:
	import pluma as gedit
import os.path
import urllib
import re
import config_manager

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


class FindResultView(gtk.HBox):
	def __init__(self, window, show_button_option):
		gtk.HBox.__init__(self)
		self._window = window
		self.show_button_option = show_button_option
		
		# initialize find result treeview
		self.findResultTreeview = gtk.TreeView()
		self.findResultTreeview.append_column(gtk.TreeViewColumn("line", gtk.CellRendererText(), markup=1))
		self.findResultTreeview.append_column(gtk.TreeViewColumn("content", gtk.CellRendererText(), markup=2))
		#self.findResultTreeview.append_column(gtk.TreeViewColumn("result_start", gtk.CellRendererText(), text=4))
		#self.findResultTreeview.append_column(gtk.TreeViewColumn("result_len", gtk.CellRendererText(), text=5))
		self.findResultTreeview.append_column(gtk.TreeViewColumn("uri", gtk.CellRendererText(), text=6))
		self.findResultTreeview.set_headers_visible(False)
		self.findResultTreeview.set_rules_hint(True)
		self.findResultTreemodel = gtk.TreeStore(int, str, str, object, int, int, str)
		self.findResultTreemodel.set_sort_column_id(0, gtk.SORT_ASCENDING)
		self.findResultTreeview.connect("cursor-changed", self.on_findResultTreeview_cursor_changed_action)
		self.findResultTreeview.connect("button-press-event", self.on_findResultTreeview_button_press_action)
		self.findResultTreeview.set_model(self.findResultTreemodel)

		# initialize scrolled window
		scrollWindow = gtk.ScrolledWindow()
		scrollWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		scrollWindow.add(self.findResultTreeview)
		
		# put a separator
		v_separator1 = gtk.VSeparator()
		
		# initialize button box
		v_box = gtk.VBox()
		v_buttonbox = gtk.VButtonBox()
		v_buttonbox.set_layout(gtk.BUTTONBOX_END)
		v_buttonbox.set_spacing(5)
		self.selectNextButton = gtk.Button(_("Next"))
		self.selectNextButton.set_no_show_all(True)
		self.selectNextButton.connect("clicked", self.on_selectNextButton_clicked_action)
		self.expandAllButton = gtk.Button(_("Expand All"))
		self.expandAllButton.set_no_show_all(True)
		self.expandAllButton.connect("clicked", self.on_expandAllButton_clicked_action)
		self.collapseAllButton = gtk.Button(_("Collapse All"))
		self.collapseAllButton.set_no_show_all(True)
		self.collapseAllButton.connect("clicked", self.on_collapseAllButton_clicked_action)
		self.clearHighlightButton = gtk.Button(_("Clear Highlight"))
		self.clearHighlightButton.set_no_show_all(True)
		self.clearHighlightButton.connect("clicked", self.on_clearHightlightButton_clicked_action)
		self.clearButton = gtk.Button(_("Clear"))
		self.clearButton.set_no_show_all(True)
		self.clearButton.connect("clicked", self.on_clearButton_clicked_action)

		v_buttonbox.pack_start(self.selectNextButton, False, False, 5)
		v_buttonbox.pack_start(self.expandAllButton, False, False, 5)
		v_buttonbox.pack_start(self.collapseAllButton, False, False, 5)
		v_buttonbox.pack_start(self.clearHighlightButton, False, False, 5)
		v_buttonbox.pack_start(self.clearButton, False, False, 5)
		v_box.pack_end(v_buttonbox, False, False, 5)
		
		#self._status = gtk.Label()
		#self._status.set_text('test')
		#self._status.hide()
		#v_box.pack_end(self._status, False)
		
		self.pack_start(scrollWindow, True, True, 5)
		self.pack_start(v_separator1, False, False)
		self.pack_start(v_box, False, False, 5)
		
		self.show_all()
		
		#initialize context menu
		self.contextMenu = gtk.Menu()
		self.expandAllItem = gtk.MenuItem(_('Expand All'))
		self.collapseAllItem = gtk.MenuItem(_('Collapse All'))
		self.clearHighlightItem = gtk.MenuItem(_('Clear Highlight'))
		self.clearItem = gtk.MenuItem(_('Clear'))
		self.markupItem = gtk.MenuItem(_('Markup'))
		
		self.contextMenu.append(self.expandAllItem)
		self.contextMenu.append(self.collapseAllItem)
		self.contextMenu.append(self.clearHighlightItem)
		self.contextMenu.append(self.clearItem)
		self.contextMenu.append(self.markupItem)
		
		self.expandAllItem.connect('activate', self.on_expandAllItem_activate)
		self.collapseAllItem.connect('activate', self.on_collapseAllItem_activate)
		self.clearHighlightItem.connect('activate', self.on_clearHighlightItem_activate)
		self.clearItem.connect('activate', self.on_clearItem_activate)
		self.markupItem.connect('activate', self.on_markupItem_activate)

		self.expandAllItem.show()
		self.collapseAllItem.show()
		self.clearHighlightItem.show()
		self.clearItem.show()
		#self.markupItem.show()
		
		self.contextMenu.append(gtk.SeparatorMenuItem())
		
		self.showButtonsItem = gtk.MenuItem(_('Show Buttons'))
		self.contextMenu.append(self.showButtonsItem)
		self.showButtonsItem.show()
		
		self.showButtonsSubmenu = gtk.Menu()
		self.showNextButtonItem = gtk.CheckMenuItem(_('Next'))
		self.showExpandAllButtonItem = gtk.CheckMenuItem(_('Expand All'))
		self.showCollapseAllButtonItem = gtk.CheckMenuItem(_('Collapse All'))
		self.showClearHighlightButtonItem = gtk.CheckMenuItem(_('Clear Highlight'))
		self.showClearButtonItem = gtk.CheckMenuItem(_('Clear'))
		
		self.showButtonsSubmenu.append(self.showNextButtonItem)
		self.showButtonsSubmenu.append(self.showExpandAllButtonItem)
		self.showButtonsSubmenu.append(self.showCollapseAllButtonItem)
		self.showButtonsSubmenu.append(self.showClearHighlightButtonItem)
		self.showButtonsSubmenu.append(self.showClearButtonItem)
		
		self.showNextButtonItem.connect('activate', self.on_showNextButtonItem_activate)
		self.showExpandAllButtonItem.connect('activate', self.on_showExpandAllButtonItem_activate)
		self.showCollapseAllButtonItem.connect('activate', self.on_showCollapseAllButtonItem_activate)
		self.showClearHighlightButtonItem.connect('activate', self.on_showClearHighlightButtonItem_activate)
		self.showClearButtonItem.connect('activate', self.on_showClearButtonItem_activate)
		
		self.showNextButtonItem.show()
		self.showExpandAllButtonItem.show()
		self.showCollapseAllButtonItem.show()
		self.showClearHighlightButtonItem.show()
		self.showClearButtonItem.show()
		
		self.showButtonsItem.set_submenu(self.showButtonsSubmenu)
		
		self.show_buttons()

		format_file = os.path.join(os.path.dirname(__file__), "result_format.xml")
		self.result_format = config_manager.ConfigManager(format_file).load_configure('result_format')
		
	def do_events(self):
		while gtk.events_pending():
			gtk.main_iteration(False)
			
	def to_xml_text(self, text):
		return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
		
	def remove_markup(self, text):
		regex = re.compile(r'<.+>([^ <>]+)</.+>')
		return regex.sub(r'\1', text)
		
	def on_findResultTreeview_cursor_changed_action(self, object):
		model, it = object.get_selection().get_selected()
		if not it:
			return
		
		try:
			m = re.search('.+(<.+>)+([0-9]+)(<.+>)+.*', model.get_value(it, 1))
			line_num = int(m.group(2))
		except:
			return
		
		result_start = model.get_value(it, 4)
		result_len = model.get_value(it, 5)
		
		parent_it = model.iter_parent(it)
		if parent_it:
			uri = urllib.quote(model.get_value(parent_it, 6).encode('utf-8')).replace('%3A//', '://')
			tab = model.get_value(parent_it, 3)
		else:
			return
			
		# Tab wasn't passed, try to find one		
		if not tab:
			docs = self._window.get_documents()
			for doc in docs:
				if doc.get_uri() == uri:
					tab = gedit.tab_get_from_document(doc)					
			
		# Still nothing? Open the file then
		if not tab:
			tab = self._window.create_tab_from_uri(uri, None, line_num, False, False)
			self.do_events()
			
		if tab:
			self._window.set_active_tab(tab)
			doc = tab.get_document()
			doc.select_range(doc.get_iter_at_offset(result_start), doc.get_iter_at_offset(result_start + result_len))
			view = tab.get_view()
			view.scroll_to_cursor()
				
	def on_findResultTreeview_button_press_action(self, object, event):
		if event.button == 3:
			#right button click
			self.contextMenu.popup(None, None, None, event.button, event.time)
		
	def on_expandAllItem_activate(self, object):
		self.findResultTreeview.expand_all()
		
	def on_collapseAllItem_activate(self, object):
		self.findResultTreeview.collapse_all()
		
	def on_clearHighlightItem_activate(self, object):
		self.clear_highlight()
		
	def on_clearItem_activate(self, object):
		self.clear_find_result()
		
	def on_markupItem_activate(self, object):
		model, it = self.findResultTreeview.get_selection().get_selected()
		if not it:
			return

		self.markup_row(model, it)
	
	def markup_row(self, model, it):
		if not it:
			return
		
		mark_head = '<span background="gray">'
		mark_foot = '</span>'
		line_str = model.get_value(it, 1)
		text_str = model.get_value(it, 2)
		if line_str.startswith(mark_head) and line_str.endswith(mark_foot):
			model.set_value(it, 1, line_str[len(mark_head):-1*len(mark_foot)])
		else:
			model.set_value(it, 1, mark_head + line_str + mark_foot)
		if text_str.startswith(mark_head) and text_str.endswith(mark_foot):
			model.set_value(it, 2, text_str[len(mark_head):-1*len(mark_foot)])
		else:
			model.set_value(it, 2, mark_head + text_str + mark_foot)
			
		if self.findResultTreemodel.iter_has_child(it):
			for i in range(0, self.findResultTreemodel.iter_n_children(it)):
				self.markup_row(model, self.findResultTreemodel.iter_nth_child(it, i))
				
	def on_showNextButtonItem_activate(self, object):
		if self.showNextButtonItem.get_active() == True:
			self.show_button_option['NEXT_BUTTON'] = True
			self.selectNextButton.show()
		else:
			self.show_button_option['NEXT_BUTTON'] = False
			self.selectNextButton.hide()

	def on_showExpandAllButtonItem_activate(self, object):
		if self.showExpandAllButtonItem.get_active() == True:
			self.show_button_option['EXPAND_ALL_BUTTON'] = True
			self.expandAllButton.show()
		else:
			self.show_button_option['EXPAND_ALL_BUTTON'] = False
			self.expandAllButton.hide()
		
	def on_showCollapseAllButtonItem_activate(self, object):
		if self.showCollapseAllButtonItem.get_active() == True:
			self.show_button_option['COLLAPSE_ALL_BUTTON'] = True
			self.collapseAllButton.show()
		else:
			self.show_button_option['COLLAPSE_ALL_BUTTON'] = False
			self.collapseAllButton.hide()
		
	def on_showClearHighlightButtonItem_activate(self, object):
		if self.showClearHighlightButtonItem.get_active() == True:
			self.show_button_option['CLEAR_HIGHLIGHT_BUTTON'] = True
			self.clearHighlightButton.show()
		else:
			self.show_button_option['CLEAR_HIGHLIGHT_BUTTON'] = False
			self.clearHighlightButton.hide()
		
	def on_showClearButtonItem_activate(self, object):
		if self.showClearButtonItem.get_active() == True:
			self.show_button_option['CLEAR_BUTTON'] = True
			self.clearButton.show()
		else:
			self.show_button_option['CLEAR_BUTTON'] = False
			self.clearButton.hide()

	def on_selectNextButton_clicked_action(self, object):
		path, column = self.findResultTreeview.get_cursor()
		it = self.findResultTreemodel.get_iter(path)
		if self.findResultTreemodel.iter_has_child(it):
			self.findResultTreeview.expand_row(path, True)
			it1 = self.findResultTreemodel.iter_children(it)
		else:
			it1 = self.findResultTreemodel.iter_next(it)
			
		if not it1:
			it1 = self.findResultTreemodel.iter_parent(it)
			it2 = self.findResultTreemodel.iter_next(it1)
			if not it2:
				it2 = self.findResultTreemodel.iter_parent(it1)
				it3 = self.findResultTreemodel.iter_next(it2)
				if not it3:
					return
				else:
					path = self.findResultTreemodel.get_path(it3)
			else:
		 		path = self.findResultTreemodel.get_path(it2)
		else:
			path = self.findResultTreemodel.get_path(it1) 
		self.findResultTreeview.set_cursor(path, column, False)

	def on_clearHightlightButton_clicked_action(self, object):
		self.clear_highlight()
		
	def on_expandAllButton_clicked_action(self, object):
		self.findResultTreeview.expand_all()
		
	def on_collapseAllButton_clicked_action(self, object):
		self.findResultTreeview.collapse_all()
		
	def on_clearButton_clicked_action(self, object):
		self.clear_find_result()

	def append_find_pattern(self, pattern, replace_flg = False, replace_text = None):
		self.findResultTreeview.collapse_all()
		idx = self.findResultTreemodel.iter_n_children(None)
		header = '#' + str(idx) + ' - '
		if replace_flg == True:
			mode = self.result_format['MODE_REPLACE'] %{'HEADER' : header, 'PATTERN' : self.to_xml_text(pattern), 'REPLACE_TEXT' : self.to_xml_text(replace_text)}
			it = self.findResultTreemodel.append(None, [idx, mode, '', None, 0, 0, ''])
		else:
			mode = self.result_format['MODE_FIND'] %{'HEADER' : header, 'PATTERN' : self.to_xml_text(pattern)}
			it = self.findResultTreemodel.append(None, [idx, mode, '', None, 0, 0, ''])
		return it
	
	def append_find_result_filename(self, parent_it, filename, tab, uri):
		filename_str = self.result_format['FILENAME'] % {'FILENAME' : self.to_xml_text(filename)}
		it = self.findResultTreemodel.append(parent_it, [0, filename_str, '', tab, 0, 0, uri])
		return it
		
	def append_find_result(self, parent_it, line, text, result_offset_start = 0, result_len = 0, uri = "", line_start_pos = 0, replace_flg = False):
		result_line = self.result_format['LINE'] % {'LINE_NUM' : line}
		markup_start = result_offset_start - line_start_pos
		markup_end = markup_start + result_len
		
		text_header = self.to_xml_text(text[0:markup_start])
		text_marked = self.to_xml_text(text[markup_start:markup_end])
		text_footer = self.to_xml_text(text[markup_end:])

		if replace_flg == False:
			result_text = (text_header + self.result_format['FIND_RESULT_TEXT'] % {'RESULT_TEXT' : text_marked} + text_footer).rstrip()
			self.findResultTreemodel.append(parent_it, [int(line), result_line, result_text, None, result_offset_start, result_len, uri])
		else:
			result_text = (text_header + self.result_format['REPLACE_RESULT_TEXT'] % {'RESULT_TEXT' : text_marked} + text_footer).rstrip()
			self.findResultTreemodel.append(parent_it, [int(line), result_line, result_text, None, result_offset_start, result_len, uri])
		
	def show_find_result(self):
		path = str(self.findResultTreemodel.iter_n_children(None) - 1)
		self.findResultTreeview.expand_row(path, True)
		pattern_it = self.findResultTreemodel.get_iter(path)
		self.findResultTreeview.set_cursor(self.findResultTreemodel.get_path(pattern_it))
		
		file_cnt = self.findResultTreemodel.iter_n_children(pattern_it)
		total_hits = 0
		for i in range(0, file_cnt):
			it1 = self.findResultTreemodel.iter_nth_child(pattern_it, i)
			hits_cnt = self.findResultTreemodel.iter_n_children(it1)
			total_hits += hits_cnt
			hits_str = self.result_format['HITS_CNT'] % {'HITS_CNT' : str(hits_cnt)}
			self.findResultTreemodel.set_value(it1, 2, hits_str)
		total_hits_str = self.result_format['TOTAL_HITS'] % {'TOTAL_HITS': str(total_hits), 'FILES_CNT' : str(file_cnt)}
		self.findResultTreemodel.set_value(pattern_it, 2, total_hits_str)

	def clear_highlight(self):
		for doc in self._window.get_documents():
			start, end = doc.get_bounds()
			if doc.get_tag_table().lookup('result_highlight') == None:
				tag = doc.create_tag("result_highlight", foreground='yellow', background='red')
			doc.remove_tag_by_name('result_highlight', start, end)
		
	def clear_find_result(self):
		self.findResultTreemodel.clear()
		
	def get_show_button_option(self):
		return self.show_button_option
		
	def show_buttons(self):
		if self.show_button_option['NEXT_BUTTON'] == True:
			self.selectNextButton.show()
			self.showNextButtonItem.set_active(True)
		if self.show_button_option['EXPAND_ALL_BUTTON'] == True:
			self.expandAllButton.show()
			self.showExpandAllButtonItem.set_active(True)
		if self.show_button_option['COLLAPSE_ALL_BUTTON'] == True:
			self.collapseAllButton.show()
			self.showCollapseAllButtonItem.set_active(True)
		if self.show_button_option['CLEAR_HIGHLIGHT_BUTTON'] == True:
			self.clearHighlightButton.show()
			self.showClearHighlightButtonItem.set_active(True)
		if self.show_button_option['CLEAR_BUTTON'] == True:
			self.clearButton.show()
			self.showClearButtonItem.set_active(True)
		
	



if __name__ == "__main__":
	view = FindResultView(None)
	window = gtk.Window(gtk.WINDOW_TOPLEVEL)
	window.add(view)
	window.show_all()
	gtk.main()


