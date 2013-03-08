# -*- coding: utf-8 -*-

#  Copyright © 2008, 2011  B. Clausius <barcc@gmx.de>
#  Copyright © 2007  P. Henrique Silva <ph.silva@gmail.com>
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

try:
	import gedit
except:
	import pluma as gedit

from gedit_pylint import PylintInstance
import config

class PylintPlugin (gedit.Plugin):

    def __init__(self):
        self._instances = {}
        
        super(PylintPlugin, self).__init__ ()
        self.config = config.Config(self)
        
    def activate(self, window):
        self._instances[window] = PylintInstance (self, window)

    def deactivate(self, window):
        if self._instances.has_key(window):
            self._instances[window].deactivate()
            del self._instances[window]

    def update_ui(self, window):
        if self._instances.has_key(window):
            self._instances[window].update_ui()

    def is_configurable(self):
        return True
    
    def create_configure_dialog(self):
        return self.config.create_dialog()

