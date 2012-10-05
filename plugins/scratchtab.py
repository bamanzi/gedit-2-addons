# -*- coding: utf-8 -*-

import os
try:
    import gedit
    SCRATCH_FILE = os.path.expanduser('~/.gnome2/gedit/plugins/scratchtab.txt')
except:
    import pluma as gedit
    SCRATCH_FILE = os.path.expanduser('~/.config/pluma/plugins/scratchtab.txt')
import gtk
from os import path


if not os.access(SCRATCH_FILE, os.F_OK):
	os.system('touch "%s"' % SCRATCH_FILE)


class scratchTabHelper:

    def __init__(self, plugin, window):

        self._window = window
        self._plugin = plugin

        self._tab = gtk.ScrolledWindow()
        self._tab.set_property("hscrollbar-policy",gtk.POLICY_AUTOMATIC)
        self._tab.set_property("vscrollbar-policy",gtk.POLICY_AUTOMATIC)
        self._tab.set_property("shadow-type",gtk.SHADOW_IN)

        area = gtk.TextView()
        area.set_wrap_mode(gtk.WRAP_WORD)
        area.set_left_margin(5)
        area.set_right_margin(5)

        self.buff = area.get_buffer()
        self.buff.set_text(self.loadFile())

        self._tab.add(area)
        self._tab.show_all()

        image = gtk.Image()
        image.set_from_stock("gtk-edit", gtk.ICON_SIZE_MENU)

        side = window.get_side_panel()
        side.add_item(self._tab, "ScratchTab", image)

    def deactivate(self):
        self.saveFile()
        side = self._window.get_side_panel()
        side.remove_item(self._tab)
        self._window = None
        self._plugin = None

    def update_ui(self):
        self.saveFile()

    # charger le brouillon
    def loadFile(self):
        fhd = open(SCRATCH_FILE,'r')
        texte = fhd.read()
        fhd.close()
        return texte

    # enregistrer le brouillon
    def saveFile(self):
        start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        fhd = open(SCRATCH_FILE,'w')
        fhd.write(self.buff.get_text(start,end))
        fhd.close()

class scratchTab(gedit.Plugin):

    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = scratchTabHelper(self, window)

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()
