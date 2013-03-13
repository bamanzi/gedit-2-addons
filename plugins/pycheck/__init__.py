#-*- coding:utf-8 -*-

try:
    import gedit
except:
    import pluma as gedit
from pycheck import PyCheckInstance


class PyCheckPlugin(gedit.Plugin):

    def __init__(self):
        self._instances = {}

        super(PyCheckPlugin, self).__init__()

    def activate(self, window):
        self._instances[window] = PyCheckInstance(self, window)

    def deactivate(self, window):
        if window in self._instances:
            self._instances[window].deactivate()
            del self._instances[window]

    def update_ui(self, window):
        pass
