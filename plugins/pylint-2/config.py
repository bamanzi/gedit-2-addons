# -*- coding: utf-8 -*-

#  Copyright © 2008, 2011  B. Clausius <barcc@gmx.de>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

import gtk
import gconf


class Config (object):
    _ui_file = os.path.join(os.path.dirname(__file__) ,'config.ui')
    _gconfDir = "/apps/gedit-2/plugins/gedit_pylint"

    def __init__(self, plugin):
        super(Config, self).__init__()
        
        self._plugin = plugin
        self.dialog = None
        
        self.word_errors = True
        self.line_errors = True
        self.color_highlight = "#ffc0c0"
        self.pylint_shortcut = 'F5'
        
        client = gconf.client_get_default()
        if not client.dir_exists(self._gconfDir):
            client.add_dir(self._gconfDir, gconf.CLIENT_PRELOAD_NONE)
        
        try:
            self.word_errors = client.get(self._gconfDir+"/word_errors").get_bool()
        except:
            pass
        try:
            self.line_errors = client.get(self._gconfDir+"/line_errors").get_bool()
        except:
            pass
        try:
            self.color_highlight = client.get(self._gconfDir+"/color_highlight").get_string()
        except:
            pass
        try:
            self.pylint_shortcut = client.get(self._gconfDir+"/pylint_shortcut").get_string()
        except:
            pass
        
    def create_dialog(self):
        if self.dialog:
            return self.dialog
            
        builder = gtk.Builder()
        builder.add_from_file(self._ui_file)
        builder.connect_signals(self)
        
        button = builder.get_object("checkbutton_worderrors")
        button.set_active(self.word_errors)
        button = builder.get_object("checkbutton_lineerrors")
        button.set_active(self.line_errors)
        button = builder.get_object("colorbutton_highlight")
        button.set_color(gtk.gdk.color_parse(self.color_highlight))
        
        self.dialog = builder.get_object("dialog_config")
        
        return self.dialog
        
    def on_checkbutton_worderrors_toggled(self, button):
        self.word_errors = button.get_active()
        self.update_tags()
        
    def on_checkbutton_lineerrors_toggled(self, button):
        self.line_errors = button.get_active()
        self.update_tags()
        
    def on_colorbutton_highlight_color_set(self, button):
        self.color_highlight = button.get_color().to_string()
        self.update_tags()
        
    def on_button_close_clicked(self, button):
        self.on_dialog_config_delete_event()
        
    def on_dialog_config_delete_event(self, *args):
        self.dialog.destroy()
        self.dialog = None
        client = gconf.client_get_default()
        client.set_bool(self._gconfDir+"/word_errors", self.word_errors)
        client.set_bool(self._gconfDir+"/line_errors", self.line_errors)
        client.set_string(self._gconfDir+"/color_highlight", self.color_highlight)
        client.set_string(self._gconfDir+"/pylint_shortcut", self.pylint_shortcut)
        
    def update_tags(self):
        for window in self._plugin._instances.keys():
            instance = self._plugin._instances[window]
            for doc in window.get_documents():
                instance._remove_tags (doc)
                instance._hightlight_errors (instance._errors[doc])
                instance._line_error_tags[doc].props.background = self.color_highlight

