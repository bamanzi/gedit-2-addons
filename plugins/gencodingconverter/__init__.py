'''
Encoding converter plugin for gedit application
Copyright (C) 2009  Alexey Kuznetsov <ak@axet.ru>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import gedit
from gencodingconverter import EncodingConverterPluginHelper
from configuredialog import ConfigureDialog

class EncodingConverterPlugin(gedit.Plugin):
  def __init__(self):
    gedit.Plugin.__init__(self)
    self.instances = {}

  def activate(self, window):
    self.instances[window] = EncodingConverterPluginHelper(self, window)

  def deactivate(self, window):
    self.instances[window].close()
    del self.instances[window]

  def update_ui(self, window):
    self.instances[window].update_ui()

  def reload_ui(self):
    for enc in self.instances:
      self.instances[enc].load_menus()

  def create_configure_dialog(self):
    window = gedit.app_get_default().get_active_window()
    cd = ConfigureDialog(window, self)
    return cd["dialog"]
