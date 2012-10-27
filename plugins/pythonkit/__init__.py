# -*- coding: utf-8 -*-

# Gedit PythonKit plugin
# Copyright 2011 Isman Firmansyah <izman.romli@gmail.com>

try:
    import gedit
except:
    import pluma as gedit
from completion import PythonProvider


class PythonKitWindow:

    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        self._provider = PythonProvider(plugin)
        for view in self._window.get_views():
            self.add_provider(view)
        self._tab_added_id = self._window.connect('tab-added',
            self.on_tab_added)
        self._tab_removed_id = self._window.connect('tab-removed',
            self.on_tab_removed)

    def deactivate(self):
        for view in self._window.get_views():
            self.remove_provider(view)
        self._window.disconnect(self._tab_added_id)
        self._window.disconnect(self._tab_removed_id)
        self._window = None
        self._plugin = None

    def update_ui(self):
        pass

    def add_provider(self, view):
        """ Add provider to the new view. """
        view.get_completion().add_provider(self._provider)

    def remove_provider(self, view):
        """ Remove provider from the view. """
        view.get_completion().remove_provider(self._provider)

    def on_tab_added(self, window, tab):
        self.add_provider(tab.get_view())

    def on_tab_removed(self, window, tab):
        self.remove_provider(tab.get_view())


class PythonKitPlugin(gedit.Plugin):

    WINDOW_DATA_KEY = "PythonKitData"

    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
        helper = PythonKitWindow(self, window)
        window.set_data(self.WINDOW_DATA_KEY, helper)

    def deactivate(self, window):
        window.get_data(self.WINDOW_DATA_KEY).deactivate()
        window.set_data(self.WINDOW_DATA_KEY, None)

    def update_ui(self, window):
        window.get_data(self.WINDOW_DATA_KEY).update_ui()
