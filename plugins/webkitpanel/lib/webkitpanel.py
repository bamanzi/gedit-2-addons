
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011  <ansuzpeorth@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import webkit
import pango
try:
    import gedit
except:
    import pluma as gedit
import os
import os.path
import sys
import subprocess
import urllib
import time
import ConfigParser

from inspector import Inspector

FILE_DIR  = os.path.realpath(os.path.dirname(__file__))
MAIN_DIR  = os.path.realpath(os.path.dirname(FILE_DIR))
CFG_FILE  = os.path.join(MAIN_DIR, 'ini.cfg')
IMG_PATH  = os.path.join(MAIN_DIR, 'www', 'img', 'network-transmit.png')
SERVER_PATH = os.path.join(MAIN_DIR, 'tools', 'little_server.py')

sys.path.append(os.path.join(MAIN_DIR, 'plugins'))

''' LOAD CONFIG '''
SHORTCUTS = {}
config = ConfigParser.ConfigParser()
config.read(CFG_FILE)
PORT = config.get('DEFAULT','port')
PANEL = config.get('DEFAULT','panel')
REFRESH = eval(config.get('DEFAULT','refresh'))
for section in config.sections():
    for function, shortcut in config.items(section):
        if function == "port" or function == "panel": continue
        shortcut = tuple(shortcut.split(' + '))
        SHORTCUTS[shortcut] = function

def write_cfg(section, key, value):
    config = ConfigParser.RawConfigParser()
    config.read(CFG_FILE)
    config.set(section, key, value)
    with file(CFG_FILE,'wb') as configfile:
        config.write(configfile)


class WebViewContextMenu(object):
    ''' ------ WebviewContextMenu ------'''
    def populate_popup_cb(self, webview, menu):
        item = gtk.MenuItem(label="Source Edition")
        menu.append(item)
        submenu  = gtk.Menu()
        menuitem = gtk.MenuItem(label="Loaded Source or File Source")
        menuitem.connect('activate', self.edit_source_activated_cb)
        submenu.append(menuitem)
        menuitem = gtk.MenuItem(label="Interpreted Source (JS useful)")
        menuitem.connect('activate', self.edit_loaded_activated_cb)
        submenu.append(menuitem)
        item.set_submenu(submenu)
        # -------------------------------
        menu.append(gtk.SeparatorMenuItem())
        # -------------------------------
        item = gtk.ImageMenuItem(stock_id=gtk.STOCK_HOME)
        item.connect('activate', self.go_home_activated_cb)
        item.set_property('label','Starting Page')
        menu.append(item)
        # -------------------------------
        menu.append(gtk.SeparatorMenuItem())
        # -------------------------------
        self.append_plugins_submenu(menu)
        item = gtk.MenuItem(label="Server Config")
        menu.append(item)
        submenu  = gtk.Menu()
        menuitem = gtk.CheckMenuItem(label="Enable Server")
        menuitem.connect('toggled', self.toggle_serveur_activated_cb)
        menuitem.set_property('active', self.flag_serveur)
        submenu.append(menuitem)
        menuitem = gtk.RadioMenuItem(None, "Localhost Acces Only")
        menuitem.connect('toggled', self.toggle_local_acces_activated_cb)
        menuitem.set_property('active', self.flag_local_acces)
        menuitem.set_property('sensitive', self.flag_serveur)
        submenu.append(menuitem)
        menuitem = gtk.RadioMenuItem(menuitem, "Global Acces")
        menuitem.connect('toggled', self.toggle_general_acces_activated_cb)
        menuitem.set_property('active', not self.flag_local_acces)
        menuitem.set_property('sensitive', self.flag_serveur)
        submenu.append(menuitem)
        item.set_submenu(submenu)
        # -------------------------------
        menu.append(gtk.SeparatorMenuItem())
        # -------------------------------
        item = gtk.CheckMenuItem(label="Auto Refresh")
        item.connect('toggled', self.toggle_auto_refresh_cb)
        item.set_property('active', self.auto_refresh)
        menu.append(item)
        item = gtk.MenuItem(label="Panel location")
        item.connect('activate', self.toggle_view_activated_cb)
        menu.append(item)
        menu.show_all()
    
    def append_plugins_submenu(self, menu):
        if not self.plugins_list: return
        base_item = gtk.MenuItem(label="Plugins")
        menu.append(base_item)
        submenu  = gtk.Menu()
        for plugin in self.plugins_list:
            item = getattr(self, plugin).get_submenuitem()
            submenu.append(item)
        base_item.set_submenu(submenu)
    
    ''' ------ WebViewContextMenu CB ------'''
    def toggle_view_activated_cb(self, menuitem):
        #~TODO
        # User other methode than remove_item & add_item
        self.panel.remove_item(self.mybox)
        if self.bottom:
            self.panel  = self.window.get_side_panel()
            self.bottom = False
            write_cfg('DEFAULT', 'panel', 'side')
        else:
            self.panel  = self.window.get_bottom_panel()
            self.bottom = True
            write_cfg('DEFAULT', 'panel', 'bottom')
        img = gtk.image_new_from_file(IMG_PATH)
        self.panel.add_item(self.mybox, 'Html Preview', img)
    
    def go_home_activated_cb(self, menuitem):
        self.dir_uri  = 'file://'+urllib.quote(MAIN_DIR)+'/www'
        self.base_uri = 'index.html'
        self.webkit_load_uri(self.dir_uri, self.base_uri)
    
    def toggle_serveur_activated_cb(self, widget):
        if not self.flag_serveur:
            uri = self.web_frame.get_uri()
            self.flag_serveur = widget.get_active()
            self.webkit_load_uri(*os.path.split(uri))
        self.flag_serveur = widget.get_active()
        self.modif_entry_background()
    
    def toggle_general_acces_activated_cb(self, widget):
        active = widget.get_active()
        if self.flag_local_acces == active and self.flag_serveur:
            self.flag_local_acces = not active
            self.webkit_load_uri(self.dir_uri, self.base_uri)
        self.flag_local_acces = not active
    
    def toggle_local_acces_activated_cb(self, widget):
        active = widget.get_active()
        if self.flag_local_acces != active and self.flag_serveur:
            self.flag_local_acces =  active
            self.webkit_load_uri(self.dir_uri, self.base_uri)
        self.flag_local_acces = active
    
    def edit_source_activated_cb(self, widget):
        tab = self.window.create_tab(True)
        doc = tab.get_document()
        if self.flag_serveur:
            text = self.web_frame.get_data_source().get_data()
            doc.set_text(text)
        else:
            uri = os.path.join(self.dir_uri, self.base_uri)
            doc.load(uri, self.encoding, 1, False)
    
    def edit_loaded_activated_cb(self, widget):
        tab = self.window.create_tab(True)
        doc = tab.get_document()
        js  = "document.title=document.documentElement.innerHTML;"
        self.webview.execute_script(js)
        text = self.web_frame.get_title()
        doc.set_text(text.replace('> <', '>\n<'))
    
    def toggle_auto_refresh_cb(self, widget):
        self.auto_refresh = widget.get_active()
        write_cfg('DEFAULT', 'refresh', str(self.auto_refresh))


class PluginWebView(WebViewContextMenu):
    ''' ----- Init Webkit ----- '''
    def init_webview(self):
        self.webview    = webkit.WebView()
        self.web_frame  = self.webview.get_main_frame()
        self.web_scroll = gtk.ScrolledWindow()
        self.web_scroll.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        self.webview.get_settings().set_property("enable-developer-extras", True)
        self.webview.connect("document-load-finished", self.webkit_loaded_cb)
        self.webview.connect("hovering-over-link", self.over_link_cb)
        self.webview.connect_after("populate-popup", self.populate_popup_cb)
        Inspector(self.webview.get_web_inspector())
        self.web_scroll.add(self.webview)
    
    def webkit_loaded_cb(self, webview, webframe):
        uri = webframe.get_uri()
        self.dir_uri, self.base_uri = os.path.split(uri)
        self.entry_navig.set_text(uri)
    
    ''' ----- Webkit Action ----- '''
    def webkit_load_current(self, arg=None, arg1=None, arg2=None):
        doc = self.window.get_active_document()
        uri = doc.get_uri()
        dir_uri, base_uri = os.path.split(uri)
        self.webkit_load_uri(dir_uri, base_uri)
    
    def webkit_load_uri(self, dir_uri, base_uri=None):
        self.gtk_widget_destroy()
        if base_uri is None: # enter clicked in entry
            self.webview.load_uri(dir_uri)
            return
        if self.flag_serveur:
            dir_uri = urllib.unquote(dir_uri).replace('file://','')
            sb = subprocess.Popen( [SERVER_PATH, PORT, 
                                    str(self.flag_local_acces), dir_uri])
            self.sb_PID = sb.pid
            time.sleep(0.5)
            uri = 'http://localhost:%s/%s' % (PORT, base_uri)
            dir_uri = 'http://localhost:%s' % PORT
        self.dir_uri  = dir_uri
        self.base_uri = base_uri
        self.webview.load_uri( os.path.join(dir_uri, base_uri) )
    
    def over_link_cb(self, webview, title, uri):
        if uri is None:
            uri = os.path.join(self.dir_uri, self.base_uri)
        self.entry_navig.set_text(uri)


class WebKitPanel(PluginWebView):
    def __init__(self, plugin, window):
        self.flag_local_acces = True
        self.flag_serveur = False
        self.flag_saving  = False
        self.control_key  = False
        self.alt_key      = False
        self.sb_PID       = False
        self.plugins_list = []
        self.connect_list = []
        self.current_keys = []
        self.auto_refresh = REFRESH
        self.window = window
        self.plugin = plugin
        self.init_cfg()
        self.init_webview()
        self.init_mybox()
        self.init_window(self.window)
        self.init_plugins()
        img = gtk.image_new_from_file(IMG_PATH)
        self.panel.add_item(self.mybox, 'WebKit Panel', img)
        try: self.encoding = gedit.encoding_get_current()
        except: self.encoding = gedit.gedit_encoding_get_current()
    
    def init_mybox(self):
        self.entry_navig = gtk.Entry()
        self.entry_navig.connect('activate', self.entry_navig_activate_cb)
        box = gtk.HBox()
        box.pack_start(self.entry_navig, True, True, 5)
        self.mybox = gtk.VBox()
        self.mybox.pack_start(box, expand=False, fill=False)
        self.mybox.pack_start(self.web_scroll)
        self.mybox.show_all()
    
    def init_window(self, window):
        id = window.connect('destroy', self.gtk_widget_destroy)
        self.connect_list.append(id)
        id = window.connect('key_press_event', self.key_press_event_cb)
        self.connect_list.append(id)
        id = window.connect('key_release_event', self.key_release_event_cb)
        self.connect_list.append(id)
        id = window.connect("active-tab-state-changed", self.state_changed_cb)
        self.connect_list.append(id)
    
    def init_cfg(self):
        if PANEL == 'bottom':
            self.panel  = self.window.get_bottom_panel()
            self.bottom = True
        else:
            self.panel  = self.window.get_side_panel()
            self.bottom = False
    
    def init_plugins(self):
        for plugin_name in os.listdir(os.path.join(MAIN_DIR, 'plugins')):
            if plugin_name.startswith('__init__'): continue
            self.plugins_list.append(plugin_name)
            exec('import %s as plug' % plugin_name)
            plugin = plug.Plugin(self, self.webview, self.window)
            setattr(self, plugin_name, plugin)
    
    ''' ----- gedit.Window CB ----- '''
    def state_changed_cb(self, arg=None):
        try:
            uri = self.window.get_active_document().get_uri()
            doc_base_uri = os.path.basename(uri)
        except: return
        if self.base_uri != doc_base_uri:
            return
        state = arg.get_active_tab().get_state()
        if self.auto_refresh:
            if state == gedit.TAB_STATE_SAVING:
                self.flag_saving = True
            elif state == gedit.TAB_STATE_NORMAL and self.flag_saving:
                self.webview.reload()
                self.flag_saving = False
    
    ''' ----- Entry CB ----- '''
    def entry_navig_activate_cb(self, entry):
        url = entry.get_text()
        self.webkit_load_uri(url)
    
    ''' ----- Key events -----'''
    def key_press_event_cb(self, window, event):
        key = gtk.gdk.keyval_name(event.keyval)
        if key not in self.current_keys: self.current_keys.append(key)
        cur_keys = tuple(self.current_keys)
        if cur_keys in SHORTCUTS:
            cmd = SHORTCUTS[cur_keys]
            if '.' in cmd:
                plugin, cmd = cmd.split('.')
                c = getattr(self, plugin)
                getattr(c, cmd)(cur_keys, self.window.get_active_document())
                return
            getattr(self, cmd)(cur_keys, self.window.get_active_document())
    
    def key_release_event_cb(self, window, event):
        self.current_keys = []
    
    ''' ----- Utils -----'''
    def gtk_widget_destroy(self, window=None):
        if self.sb_PID:
            try:
                os.kill(self.sb_PID, 3)
            except: pass
    
    def modif_entry_background(self):
        if self.flag_serveur:
            self.entry_navig.set_property('progress-fraction', 1)
        else:
            self.entry_navig.set_property('progress-fraction', 0)
            self.gtk_widget_destroy()
    
    ''' ----- Gedit Callbacks ---- '''
    def deactivate(self):
        for id in self.connect_list:
            self.window.disconnect(id)
        self.window = None
        self.plugin = None
        self.panel.remove_item(self.mybox)
        self.gtk_widget_destroy()
    
    def update_ui(self):
        pass

