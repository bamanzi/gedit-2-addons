"""SyntaxCompleterPlugin enabled word and symbol completion."""
# Copyright (C) 2007-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).

__metaclass__ = type

__all__ = [
    'SyntaxCompleterPlugin',
    ]

from gettext import gettext as _

try:
    import gedit
except:
    import pluma as gedit

from gdp import GDPWindow
from gdp.syntaxcompleter import SyntaxController


class SyntaxCompleterPlugin(gedit.Plugin):
    """Automatically complete words from the list of words in the document."""

    action_group_name = 'PythonPluginActions'
    menu_path = '/MenuBar/PythonMenu/ToolsOps_2/CompleteWord'
    menu_xml = """
        <ui>
          <menubar name="MenuBar">
            <menu name='PythonMenu' action='Python'>
              <placeholder name="ToolsOps_2">
                <separator />
                <menuitem action="CompleteWord"/>
                <separator />
              </placeholder>
            </menu>
          </menubar>
        </ui>
        """

    def actions(self, syntaxer):
        """Return a list of action tuples.

        (name, stock_id, label, accelerator, tooltip, callback)
        """
        return  [
            ('CompleteWord', None, _("Complete _word (GDP)"),
                '<Alt>slash',
                _("Complete the word at the cursor."),
                syntaxer.show_syntax_view),
            ]

    def __init__(self):
        """Initialize the plugin the whole Gedit application."""
        gedit.Plugin.__init__(self)
        self.windows = {}

    def activate(self, window):
        """Activate the plugin in the current top-level window.

        Add a SyntaxControler to every view.
        """
        self.windows[window] = GDPWindow(
            window, SyntaxController(window), self)
        self.update_ui(window)

    def deactivate(self, window):
        """Deactivate the plugin in the current top-level window.

        Remove the SyntaxControler from every view.
        """
        self.windows[window].deactivate()
        del self.windows[window]

    def update_ui(self, window):
        """Toggle the plugin's sensativity in the top-level window.

        Set the current controler.
        """
        view = window.get_active_view()
        if not isinstance(view, gedit.View):
            return
        self.windows[window].controller.set_view(view)
        self.windows[window].controller.correct_language(
            window.get_active_document())
        gdp_window = self.windows[window]
        manager = gdp_window.window.get_ui_manager()
        if view.get_editable():
            sensitive = True
        else:
            sensitive = False
        manager.get_action(self.menu_path).props.sensitive = sensitive
