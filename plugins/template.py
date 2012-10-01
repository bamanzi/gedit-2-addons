# -*- coding: utf-8 -*-
#  New File From a Template 1.04
#
# 
#  Eckhard M. Jäger <Bart@neeneenee.de>
#  Copyright @ 2007 area42 - Agentur & Systempartner
#  http://www.area42.de
#   
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#   
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import gedit
import gtk
import gtk.glade
import re
import os
from os.path import *
import mimetypes
from time import gmtime, strftime

# Puts a "Open From Template" menu item into the file menu
ui_str = """<ui>
  <menubar name="MenuBar">
    <menu name="FileMenu" action="File">
      <placeholder name="FileOps_1">
        <menuitem name="FileOpenFromTemplate" action="open_from_template"/>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""

this_lang = os.getenv("LANG")

#
## A class
class OpenFileFromTemplateHelper:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		
		# Insert menu items
		self._insert_menu()

	def deactivate(self):
		self._window = None
		self._plugin = None

	def update_ui(self):
		# Called whenever the window has been updated (active tab
		# changed, etc.)
		x = 1
        
	def _insert_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Create a new action group
		if this_lang.split('.')[0] == "de_DE":
			self._action_group = gtk.ActionGroup("OpenFromTemplateActions")
			self._action_group.add_actions([("open_from_template", None, _("Neu von Vorlage"),
				                              None, _("Ein neues Dokument aus einer eigenen Vorlage erstellen"),
				                              self.on_open_from_template_activate)])
		else:
			self._action_group = gtk.ActionGroup("OpenFromTemplateActions")
			self._action_group.add_actions([("open_from_template", None, _("New From Template"),
				                              None, _("Create a new file based on a custom defined template"),
				                              self.on_open_from_template_activate)])

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

	# Menu activate handlers.
	# 1. provide a file chooser dialog
	#		chooser = gtk.FileChooserDialog("Choose Template File",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
	# 2. parse the file chosen and extract all $$.*$$ strings
	# 3. construct a dialog that displays the extracted vars and a text entry
	# 4. write the new file to a new blank document.
	#		new_tab = self._window.create_tab(True)
	#		doc = new_tab.get_document()
	#		doc.set_text(parsed_text)
	def on_open_from_template_activate(self, action):
		# create and display a file chooser dialog
		if this_lang.split('.')[0] == "de_DE":
			this_title = "Datei als Vorlage öffnen..."
		else:
			this_title = "Open Template File..."
		homedir = os.path.expanduser("~")
		chooser = gtk.FileChooserDialog(this_title,action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		chooser.set_current_folder(homedir+"/.gnome2/gedit/templates")
		chooser.set_default_response(gtk.RESPONSE_OK)
		response = chooser.run()

		# process the response
		if response == gtk.RESPONSE_OK:
			# create a template file object and find keywords
			template = TemplateFile(chooser.get_filename())
			
			# getting the extension to specify the mime 
			tpl_ext = os.path.splitext(chooser.get_filename())
			tpl_ext = "*"+tpl_ext[1]

			language_manager = gedit.get_language_manager()
			langs = language_manager.get_language_ids()
			got_it = 0
			for id in langs:
				if got_it == 1:
					break
				lang = language_manager.get_language(id)
				name = lang.get_name()
				all_ext = lang.get_globs()
				num_ext = len(all_ext)
				for ext in all_ext:
					if tpl_ext == ext:
						language = language_manager.guess_language(tpl_ext)
						got_it = 1
						break
					else:
						language = language_manager.guess_language("txt")	
			# create the new text	
			# print strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
			new_text = template.create_text()
			# create a new gedit tab
			new_tab = self._window.create_tab(True)
			doc = new_tab.get_document()
			doc.set_text(new_text)
			doc.set_language(language)
		elif response == gtk.RESPONSE_CANCEL:
			print 'Closed, no files selected'
		#print dict(gtk.ListStore(str))
		chooser.destroy()
		
#
## a class
class OpenFileFromTemplate(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._instances = {}

	def activate(self, window):
		self._instances[window] = OpenFileFromTemplateHelper(self, window)

	def deactivate(self, window):
		self._instances[window].deactivate()
		del self._instances[window]

	def update_ui(self, window):
		self._instances[window].update_ui()
		
#
## a class to hold template file info
class TemplateFile:
	def __init__(self, filename):
		self.filename = filename
		fileobj = open(self.filename)
		self.data = fileobj.read()
		fileobj.close()
		self.keywords = {}
		
	def __del__(self):
		del self.data
		del self.filename
	
	def create_text(self):
		
#		for key in self.keywords.keys():
#			pattern = "\$\$" + key + "\$\$"
#			self.data = re.sub(pattern, self.keywords[key], self.data)
		return self.data


