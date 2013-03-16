# -*- coding: utf-8 -*-
#  Browser plugin
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

import gtk
import sys, os, string
try:
	import gedit
except:
	import pluma as gedit

ui_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="ViewMenu" action="View">
			<placeholder name="ViewOps_3">
				<separator name="BrowserSep"/>
				<menu action='browserpreview'>
					<menuitem name="Browser" action="Browser"/>
					<menuitem name="Opera" action="Opera"/>
					<menuitem name="Webkit" action="Webkit"/>
					<menuitem name="Internet Explorer 6" action="Internet Explorer 6"/>
				</menu>\
			</placeholder>
		</menu>
		</menubar>
</ui>
"""

class BrowserPluginInstance:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		self._activate_id = 0
		
		self.insert_menu()
		self.update()
		
		self._activate_id = self._window.connect('focus-in-event', \
				self.on_window_activate)

	def stop(self):
		self.remove_menu()

		if self._activate_id:
			self._window.handler_disconnect(self._activate_id)
		
		self._window = None
		self._plugin = None
		self._action_group = None
		self._activate_id = 0
		
	def insert_menu(self):
		manager = self._window.get_ui_manager()
		
		self._action_group = gtk.ActionGroup("GeditBrowserPluginActions")
		self._action_group.add_actions( \
				[("browserpreview",None,"Ansehen in",None,None),
				("Browser", None, _("Firefox"), None, \
				_("Das aktuelle Dokument in Firefox ansehen."), \
				lambda a: self._plugin.on_browser_activate(self._window)),
				("Opera", None, _("Opera"), None, \
				_("Das aktuelle Dokument in Opera ansehen."), \
				lambda a: self._plugin.on_opera_activate(self._window)),
				("Webkit", None, _("Webkit"), None, \
				_("Das aktuelle Dokument in einem Webkit-Browser ansehen."), \
				lambda a: self._plugin.on_webkit_activate(self._window)),
				("Internet Explorer 6", None, _("Internet Explorer 6"), None, \
				_("Das aktuelle Dokument im Internet Explorer 6 ansehen."), \
				lambda a: self._plugin.on_ie6_activate(self._window)),
				])
		
		manager.insert_action_group(self._action_group, -1)
		self._ui_id = manager.add_ui_from_string(ui_str)

	def remove_menu(self):
		manager = self._window.get_ui_manager()
		
		manager.remove_ui(self._ui_id)
		manager.remove_action_group(self._action_group)
		manager.ensure_update()

	def update(self):
		tab = self._window.get_active_tab()
	
	def on_window_activate(self, window, event):
		self._plugin.dialog_transient_for(window)

class BrowserPlugin(gedit.Plugin):
	DATA_TAG = "BrowserPluginInstance"
	
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._dialog = None

	def get_instance(self, window):
		return window.get_data(self.DATA_TAG)
	
	def set_instance(self, window, instance):
		window.set_data(self.DATA_TAG, instance)
	
	def activate(self, window):
		self.set_instance(window, BrowserPluginInstance(self, window))
	
	def deactivate(self, window):
		self.get_instance(window).stop()
		self.set_instance(window, None)
		
	def update_ui(self, window):
		self.get_instance(window).update()

	def dialog_transient_for(self, window):
		if self._dialog:
			self._dialog.set_transient_for(window)
			
	def on_browser_activate(self, window):
		doc = window.get_active_document()
		url = doc.get_uri()
		parts = string.split(url,"//")
		if parts[0]=="ftp:":
			parts[0] = "http:"
		command = "firefox " + parts[0] + "//" + parts[1] +" &"
		os.system(command)

	def on_opera_activate(self, window):
		doc = window.get_active_document()
		url = doc.get_uri()
		parts = string.split(url,"//")
		if parts[0]=="ftp:":
			parts[0] = "http:"
		command = "opera " + parts[0] + "//" + parts[1] +" &"
		os.system(command)	
		
	def on_webkit_activate(self, window):
		doc = window.get_active_document()
		url = doc.get_uri()
		parts = string.split(url,"//")
		if parts[0]=="ftp:":
			parts[0] = "http:"
		try:
			command = "midori " + parts[0] + "//" + parts[1] +" &"
			os.system(command)
		except OSError:
			none = 0
		try:
			command = "kfmclient openProfile webbrowsing " + parts[0] + "//" + parts[1] +" &"
			os.system(command)
		except OSError:
			none = 0
		
	def on_ie6_activate(self, window):
		webUrl = 0
		homedir = os.path.expanduser("~")
		doc = window.get_active_document()
		url = doc.get_uri()
		parts = string.split(url,"//")
		if parts[0]=="ftp:":
			parts[0] = "http:"
			webUrl = 1
		url =  parts[0] + "//" + parts[1]
		if webUrl == 0:
			normUrl = os.path.normpath(url)
			parts = string.split(url,"/")
			winUrl = ""
			numParts = len(parts)
			for i in range(numParts):
				if i > 2:
					winUrl = winUrl + "\\" + parts[i]
			winUrl = "z:" + winUrl
		else:
			winUrl = url

		if os.path.isfile(homedir+"/.ies4linux/bin/ie6"):
			command = homedir+"/.ies4linux/bin/ie6 \"" + winUrl + "\" &"
			os.system(command)		
		elif os.path.isfile(homedir+"/.wine/drive_c/Program Files/Internet Explorer/iexplore.exe"):
			command = homedir+"/.wine/drive_c/Program Files/Internet Explorer/iexplore.exe \"" + winUrl + "\" &"
			os.system(command)

