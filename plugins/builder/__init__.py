#    builder plugin interface
#    Copyright (C) 2009 Mike Reed <gedit@amadron.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os.path
import logging
import logging.config

import gtk
try:
    import gedit
except:
    import pluma as gedit

from Builder import Builder
from Config import Config
from ConfigEditor import ConfigEditor


class GeditPluginApi(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._config_editor = None
        self._config = Config(self.get_data_dir())
        self._instances = {}
        
        # Set up logging.  It was tempting to use gedit.debug but this
        # has three problems.
        # 1) Turning it on switches on all debug for the "PLUGIN" section
        #    creating an immense amount of irrelevent output
        # 2) You can't vary the level of debug, it is either on or off
        # 3) You have to import gedit which means some modules in this
        #    package that could be unit tested independently of gedit
        #    can't be if we use gedit.debug
        if os.path.exists('logging.conf'):
            try:
                logging.config.fileConfig('logging.conf')
                self._l = logging.getLogger('plugin.builder')
                self._l.info('Setup logging from logging.conf')
            except  Exception as inst:
                # Well, they wanted logging but something is wrong.
                # Give 'em everything
                self._init_logging(logging.INFO)
                self._l.error('Something wrong with logging.conf, '
                              'using INFO level logging to stderr')
                self._l.error(str(type(inst)))
                self._l.error(str(inst.args))
                self._l.error(str(inst))
        else:
            self._init_logging(logging.WARNING)

    def _init_logging(self, level):
        f = logging.Formatter(
            '%(asctime)s: %(levelname)8s: %(module)s: %(funcName)s: %(message)s')
        h = logging.StreamHandler()
        h.setLevel(level)
        h.setFormatter(f)
        self._l = logging.getLogger("plugin.builder")
        self._l.addHandler(h)
        self._l.setLevel(level)
    
    def activate(self, window):
        self._instances[window] = Builder(self._config, window)
            
        
    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]
        
    def update_ui(self, window):
        self._instances[window].update_ui()
        
    def is_configurable(self):
        return True
        
    def create_configure_dialog(self):
        if not self._config_editor:
            self._config_editor = ConfigEditor(self._config)
        dialog = self._config_editor.dialog()
        window = gedit.app_get_default().get_active_window()
        if window:
            dialog.set_transient_for(window)
        return dialog


               
