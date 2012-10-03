# -*- coding: utf-8 -*-

# terminal.py - Embeded VTE terminal for gedit
# This file is part of gedit
#
# Copyright (C) 2005-2006 - Paolo Borelli
#
# gedit is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gedit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gedit; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, 
# Boston, MA  02110-1301  USA

try:
    import gedit
    import gedit.utils as gedit_utils
    import gconf
    import gnomevfs
    is_mate = False
    APP_KEY = 'gedit-2'
except:
    import pluma as gedit
    import pluma.utils as gedit_utils
    import mateconf as gconf
    import matevfs as gnomevfs
    is_mate = True
    APP_KEY = 'pluma'
    
import pango
import gtk
import gtk.gdk
import gobject
import vte
import gettext

import os
from gpdefs import *
from math import *
try:
    gettext.bindtextdomain(GETTEXT_PACKAGE, GP_LOCALEDIR)
    _ = lambda s: gettext.dgettext(GETTEXT_PACKAGE, s);
except:
    _ = lambda s: s
a = "123"


class ConfigDialog(gtk.Dialog):
    def __init__(self, parent, config):
        # Create config diaog window
        title = _("Runcible properties")
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)

        super(toggle_dlg, self).__init__(title, parent, 0, buttons)
        
        self.vbox.set_homogeneous(False)
        
        # Create diaog items
        self._msg = gtk.Label(_("Comment"))
        self._msg.set_property("xalign", 0.0)
        self.vbox.pack_start(self._msg, True, True, 5)
        
        self._input = gtk.Entry()
        self._input.connect("key-press-event", self._on_input_key)
        self.vbox.pack_start(self._input, True, True, 0)
        
        self._note = gtk.Label(_("(leave blank to use source line)"))
        self.vbox.pack_start(self._note, True, True, 5)
        
        self.vbox.show_all()
        
        # Setup configuration dictionary
        self._config = config

class GeditTerminal(gtk.HBox):
    """VTE terminal which follows gnome-terminal default profile options"""

    __gsignals__ = {
        "populate-popup": (
            gobject.SIGNAL_RUN_LAST,
            None,
            (gobject.TYPE_OBJECT,)
        )
    }

    GCONF_PROFILE_DIR = "/apps/%s/profiles/Default" % (
        'gnome-terminal' if not is_mate else 'mate-terminal')
    
    defaults = {
        'allow_bold'            : True,
        'audible_bell'          : False,
        'background'            : None,
        #'background_color'      : '#EEEEEE',
        'background_color'      : '#FFFFFF',
        'backspace_binding'     : 'ascii-del',
        'cursor_blinks'         : False,
        'emulation'             : 'xterm',
        #'font_name'             : 'Monospace 10',
        'font_name'             : 'Monospace 8',
        'foreground_color'      : '#000000',
        'scroll_on_keystroke'   : False,
        'scroll_on_output'      : False,
        'scrollback_lines'      : 100,
        'visible_bell'          : False
    }

    def __init__(self, window):
        gtk.HBox.__init__(self, False, 4)

        gconf_client.add_dir(self.GCONF_PROFILE_DIR,
                             gconf.CLIENT_PRELOAD_RECURSIVE)
        self._window = window
        self._encoding = gedit.encoding_get_current()
        self._vte = vte.Terminal()
        self.reconfigure_vte()
        self._vte.set_size(self._vte.get_column_count(), 5)
#        self._vte.set_size_request(200, 50)
        self._vte.show()
        self.pack_start(self._vte)
        
        self._scrollbar = gtk.VScrollbar(self._vte.get_adjustment())
        self._scrollbar.show()
        self.pack_start(self._scrollbar, False, False, 0)
        
        gconf_client.notify_add(self.GCONF_PROFILE_DIR,
                                self.on_gconf_notification)
        
        self._vte.connect("key-press-event", self.on_vte_key_press)
        self._vte.connect("button-press-event", self.on_vte_button_press)
        self._vte.connect("popup-menu", self.on_vte_popup_menu)
        self._vte.connect("child-exited", lambda term: term.fork_command())
        self._vte.fork_command()

    def reconfigure_vte(self):
        # Fonts
        desktop = 'gnome' if not is_mate else 'mate'
        if gconf_get_bool(self.GCONF_PROFILE_DIR + "/use_system_font"):
            font_name = gconf_get_str("/desktop/%s/interface/monospace_font" % desktop
                                      self.defaults['font_name'])
        else:
            font_name = gconf_get_str(self.GCONF_PROFILE_DIR + "/font",
                                      self.defaults['font_name'])

        try:
            self._vte.set_font(pango.FontDescription(font_name))
        except:
            pass

        # colors
        #~ fg_color = gconf_get_str(self.GCONF_PROFILE_DIR + "/foreground_color",
                                 #~ self.defaults['foreground_color'])
        #~ bg_color = gconf_get_str(self.GCONF_PROFILE_DIR + "/background_color",
                                 #~ self.defaults['background_color'])
        fg_color = self.defaults['foreground_color']
        bg_color = self.defaults['background_color']
        self._vte.set_colors(gtk.gdk.color_parse (fg_color),
                             gtk.gdk.color_parse (bg_color),
                             [])

        self._vte.set_cursor_blinks(gconf_get_bool(self.GCONF_PROFILE_DIR + "/cursor_blinks",
                                                   self.defaults['cursor_blinks']))

        self._vte.set_audible_bell(not gconf_get_bool(self.GCONF_PROFILE_DIR + "/silent_bell",
                                                      not self.defaults['audible_bell']))

        self._vte.set_scrollback_lines(gconf_get_int(self.GCONF_PROFILE_DIR + "/scrollback_lines",
                                                     self.defaults['scrollback_lines']))
        
        self._vte.set_allow_bold(gconf_get_bool(self.GCONF_PROFILE_DIR + "/allow_bold",
                                                self.defaults['allow_bold']))

        self._vte.set_scroll_on_keystroke(gconf_get_bool(self.GCONF_PROFILE_DIR + "/scroll_on_keystroke",
                                                         self.defaults['scroll_on_keystroke']))

        self._vte.set_scroll_on_output(gconf_get_bool(self.GCONF_PROFILE_DIR + "/scroll_on_output",
                                                      self.defaults['scroll_on_output']))

        self._vte.set_emulation(self.defaults['emulation'])
        self._vte.set_visible_bell(self.defaults['visible_bell'])
#define DINGUS1 "(((news|telnet|nntp|file|http|ftp|https)://)|(www|ftp)[-A-Za-z0-9]*\\.)[-A-Za-z0-9\\.]+(:[0-9]*)?"
#define DINGUS2 "(((news|telnet|nntp|file|http|ftp|https)://)|(www|ftp)[-A-Za-z0-9]*\\.)[-A-Za-z0-9\\.]+(:[0-9]*)?/[-A-Za-z0-9_\\$\\.\\+\\!\\*\\(\\),;:@&=\\?/~\\#\\%]*[^]'\\.}>\\) ,\\\"]"
#(((news|telnet|nntp|file|http|ftp|https)://)|(www|ftp)[-A-Za-z0-9]*\\.)[-A-Za-z0-9\\.]+(:[0-9]*)?
        id = self._vte.match_add("[A-Za-z0-9\\./\\_\\-~]+:([0-9]+):")
        self._vte.match_set_cursor_type(id,  gtk.gdk.HAND1)
        id = self._vte.match_add("File .+ line [0-9]+")
        self._vte.match_set_cursor_type(id,  gtk.gdk.HAND1)
        
    def on_gconf_notification(self, client, cnxn_id, entry, what):
        self.reconfigure_vte()

    def on_vte_key_press(self, term, event):
        modifiers = event.state & gtk.accelerator_get_default_mod_mask()
        if event.keyval in (gtk.keysyms.Tab, gtk.keysyms.KP_Tab, gtk.keysyms.ISO_Left_Tab):
            if modifiers == gtk.gdk.CONTROL_MASK:
                self.get_toplevel().child_focus(gtk.DIR_TAB_FORWARD)
                return True
            elif modifiers == gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK:
                self.get_toplevel().child_focus(gtk.DIR_TAB_BACKWARD)
                return True
        elif event.keyval == gtk.keysyms.F6:
            if modifiers == gtk.gdk.SHIFT_MASK:
                self.get_toplevel().child_focus(gtk.DIR_TAB_BACKWARD)
            else:
                self.get_toplevel().child_focus(gtk.DIR_TAB_FORWARD)
            return True
        elif event.keyval == gtk.keysyms.F5 and modifiers == gtk.gdk.CONTROL_MASK:
            self.reset()
            return True
        elif event.keyval == gtk.keysyms.F5:
            self.run(self.get_document_path())
            return True
        return False
    
    def on_vte_button_press(self, term, event):
        if event.button == 1:
            col, row = int(floor(event.x / self._vte.get_char_width())), int(floor(event.y / self._vte.get_char_height()))
            match = self._vte.match_check(col, row)
            if match:
                if match[1] == 0:
                    uri, line = match[0].split(":")[0:2]
                else:
                    details = match[0].split()
                    print details
                    uri, line = details[1].strip(",").strip("\""), details[3]
                os.chdir(self.current_directory())
                print self.current_directory()
                print os.path.abspath(uri), os.path.join(self.current_directory(), uri)
                uri = "file://" + os.path.join(self.current_directory(), uri)

                #uri = "file://" + os.path.expanduser(os.path.abspath(uri))
                #uri = "file://" + self.get_document_path()
                line = int(line)
                tab = self._window.get_tab_from_uri(uri) 
                if tab == None:
                    tab = self._window.create_tab_from_uri( uri, self._encoding, line, False, False )
                else:
                    doc = tab.get_document()
                    doc.begin_user_action()
                    it = doc.get_iter_at_line_offset(line-1,0)
                    doc.place_cursor(it)
                    (start, end) = doc.get_bounds()
                    self._window.get_active_view().scroll_to_iter(end,0.0)
                    self._window.get_active_view().scroll_to_iter(it,0.0)
                    self._window.get_active_view().grab_focus()
                    doc.end_user_action()
                self._window.set_active_tab( tab)                    

        elif event.button == 3:
            self.do_popup(event)
            return True

    def on_vte_popup_menu(self, term):
        self.do_popup()

    def create_popup_menu(self):
        menu = gtk.Menu()

        item = gtk.ImageMenuItem(gtk.STOCK_COPY)
        item.connect("activate", lambda menu_item: self._vte.copy_clipboard())
        item.set_sensitive(self._vte.get_has_selection())
        menu.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_PASTE)
        item.connect("activate", lambda menu_item: self._vte.paste_clipboard())
        menu.append(item)
        
        self.emit("populate-popup", menu)
        menu.show_all()
        return menu

    def do_popup(self, event = None):
        menu = self.create_popup_menu()
   
        if event is not None:
            menu.popup(None, None, None, event.button, event.time)
        else:
            menu.popup(None, None,
                       lambda m: gedit_utils.menu_position_under_widget(m, self),
                       0, gtk.get_current_event_time())
            menu.select_first(False)        

    def current_directory(self):        
        return os.path.expanduser(self._vte.get_window_title().split(':')[1].strip())
    
    def get_document_path(self):
        doc = self._window.get_active_document()
        if doc is None:
            return None
        uri = doc.get_uri()
        if uri is not None and gedit_utils.uri_has_file_scheme(uri):
            return gnomevfs.get_local_path_from_uri(uri)
        return None
    
    def change_directory(self, path):
        path = path.replace('\\', '\\\\').replace('"', '\\"')
        self._vte.feed_child('cd "%s"\n' % path)
    
    def reset(self):
        self._vte.feed_child("reset\n")
        
    def run(self, filename):
        self._window.get_active_document().save(True)
        self.change_directory(os.path.dirname(filename))
        basename = os.path.basename(filename)
        self._vte.feed_child('python "%s"\n' % basename)
        
    def goto_selected_line(self):
        self._vte.feed_child('"%s"' % self._vte.get_text_range())

ui_str = """
<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="ToolsOps_3">
            <menuitem name="Run" action="Run"/>
            <menuitem name="Reset Terminal" action="Reset Terminal"/>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""
class TerminalWindowHelper(object):
    def __init__(self, window):
        self._window = window

        self._panel = GeditTerminal(window)
        self._panel._window = window
        self._panel.connect("populate-popup", self.on_panel_populate_popup)
        self._panel.show()

        image = gtk.Image()
        image.set_from_icon_name("utilities-terminal", gtk.ICON_SIZE_MENU)
    
        bottom = window.get_bottom_panel()
        bottom.add_item(self._panel, _("Runcible"), image)
        pane = gtk.HPaned(); 
        #tab = window.get_active_tab(); 
            
        v = bottom.get_parent()
        h = v.get_parent()
        v.reparent(pane);
        #v.set_size_request(1300, 100)
        #self._panel.set_size_request(100, 100)
        #pane.add(self._panel)
        bottom = window.get_bottom_panel()
        bottom.reparent(pane)
        pane.add(bottom)
        h.add(pane);
        self.splitter = pane
        #self._panel.set_position(400)
        pane.show_all(); 
        gobject.timeout_add(500, self.resize)
        self._insert_menu()
        
    def resize(self):
        size = self._window.get_size()
        if size:
            self.splitter.set_position(size[0]-600)
            return False
        return True      
          
    def deactivate(self):
        self._remove_menu()
        bottom = self._window.get_bottom_panel()
        bottom.remove_item(self._panel)
     
    def _insert_menu(self):
        manager = self._window.get_ui_manager()
        self._action_group = gtk.ActionGroup("RuncibleActions")
        self._action_group.add_actions([("Run",
                                         None,
                                         _("R_un"),
                                         "F5",                                         
                                         _("Run Python code"),
                                         lambda a, w: self._panel.run(self._panel.get_document_path())),
                                         ("Reset Terminal",
                                         None,
                                         _("Re_set Terminal"),
                                         "<Control>F5",                                         
                                         _("Reset and clears terminal"),
                                         lambda a, w: self._panel.reset()),],
                                        self._window)
        manager.insert_action_group(self._action_group, -1)
        self._ui_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        manager.remove_action_group(self._action_group)
        manager.ensure_update()
        
    def update_ui(self):
        pass


    def on_panel_populate_popup(self, panel, menu):
        menu.prepend(gtk.SeparatorMenuItem())
        location = self._panel.get_document_path()
        path = os.path.dirname(location)
        item = gtk.MenuItem(_("C_hange Directory"))
        item.connect("activate", lambda menu_item: panel.change_directory(path))
        item.set_sensitive(path is not None)
        menu.prepend(item)
        
        item = gtk.MenuItem(_("Run"))
        item.connect("activate", lambda menu_item: panel.run(location))
        item.set_sensitive(path is not None)
        menu.prepend(item)
        
        item = gtk.MenuItem(_("Go to line"))
        item.connect("activate", lambda menu_item: panel.goto_selected_line())
        item.set_sensitive(path is not None)
        
        menu.prepend(item)
        

class TerminalPlugin(gedit.Plugin):
    WINDOW_DATA_KEY = "TerminalPluginWindowData"

    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
        helper = TerminalWindowHelper(window)
        window.set_data(self.WINDOW_DATA_KEY, helper)

    def deactivate(self, window):
        window.get_data(self.WINDOW_DATA_KEY).deactivate()
        window.set_data(self.WINDOW_DATA_KEY, None)

    #def update_ui(self, window):
    #    window.get_data(self.WINDOW_DATA_KEY).update_ui()

gconf_client = gconf.client_get_default()
def gconf_get_bool(key, default = False):
    val = gconf_client.get(key)
    
    if val is not None and val.type == gconf.VALUE_BOOL:
        return val.get_bool()
    else:
        return default

def gconf_get_str(key, default = ""):
    val = gconf_client.get(key)
    
    if val is not None and val.type == gconf.VALUE_STRING:
        return val.get_string()
    else:
        return default

def gconf_get_int(key, default = 0):
    val = gconf_client.get(key)
    
    if val is not None and val.type == gconf.VALUE_INT:
        return val.get_int()
    else:
        return default


# ex:ts=4:et: Let's conform to PEP8
