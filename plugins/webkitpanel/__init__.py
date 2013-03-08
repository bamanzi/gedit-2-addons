
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

try:
    import gedit
except:
    import pluma as gedit
import os
import os.path
import urllib
import time
from lib.webkitpanel import WebKitPanel

main_path = os.path.realpath(os.path.dirname(__file__))

class HttpServerPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = WebKitPanel(self, window)
        #~FIXME windows icompatible
        diruri = 'file://'+urllib.quote(main_path)+'/www'
        self._instances[window].webkit_load_uri(diruri, 'index.html')

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()
        
