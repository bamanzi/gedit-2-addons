# Copyright (C) 2008-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""Find matching text in multiple files."""

__metaclass__ = type

__all__ = [
    'FindPlugin',
    ]


from gettext import gettext as _

try:
    import gedit
except:
    import pluma as gedit

from gdp import GDPWindow
from gdp.find import Finder


class FindPlugin(gedit.Plugin):
    """Find matching text in multiple files plugin."""
    # This is a new-style class that call and old-style __init__().
    # pylint: disable-msg=W0233

    action_group_name = 'GDPFindActions'
    menu_xml = """
        <ui>
          <menubar name="MenuBar">
            <menu name="SearchMenu" action='Search'>
              <placeholder name="SearchOps_5">
                <separator/>
                <menuitem action="FindFiles"/>
                <menuitem action="ReplaceFiles"/>
                <separator/>
              </placeholder>
            </menu>
          </menubar>
        </ui>
        """

    def actions(self, finder):
        """Return a list of action tuples.

        (name, stock_id, label, accelerator, tooltip, callback)
        """
        return [
            ('FindFiles', None, _('Find in files...'),
                '<Control><Shift>f', _('Fi_nd in files'),
                finder.show),
            ('ReplaceFiles', None, _('R_eplace in files...'),
                '<Control><Shift>h', _('Replace in files'),
                finder.show_replace),
            ]

    def __init__(self):
        """Initialize the plugin the whole Gedit application."""
        gedit.Plugin.__init__(self)
        self.windows = {}

    def activate(self, window):
        """Activate the plugin in the current top-level window.

        Add 'Find in files' to the menu.
        """
        finder = Finder(window)
        self.windows[window] = GDPWindow(window, finder, self)
        self.windows[window].connect_signal(
            window, 'bzr-branch-open', finder.on_file_path_added)

    def deactivate(self, window):
        """Deactivate the plugin in the current top-level window.

        Remove a 'Find in files' to the menu.
        """
        self.windows[window].deactivate()
        del self.windows[window]

    def update_ui(self, window):
        """Toggle the plugin's sensativity in the top-level window.

        'Find in files' is always active.
        """
        pass
