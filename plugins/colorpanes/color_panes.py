# -*- coding: utf8 -*-
#  Color Panes plugin for Gedit
#
#  Copyright (C) 2010-2011 Derek Veit
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

"""
Version history:
2011-05-22  Version 2.3.0
    Minimize work done when a tab is added to a panel by only updating widgets
     of the new notebook page.
    Keep the scheme colors as ColorPanesWindowHelper attributes so that they
     only need to be determined when the ColorPanesWindowHelper starts or when
     the scheme changes, and not when a tab is added to a panel.
2010-10-13  Version 2.2.0
    Replaced log methods with logger module.
    Fixed Issue 3: The cursor in the Python Console plugin pane is invisible
     with the Cobalt color scheme.
2010-05-10  Version 2.1.1
    Fixed Issue 2: Gedit crash caused by getting text colors from terminal.
2010-03-26  Version 2.1.0
    Added recoloring of prelight (hover) state.
    Added font and some tag color matching of Python Console plugin.
2010-03-07  Version 2.0.1
    Minor updates to docstrings, names, etc.  No functional change.
2010-03-07  Version 2.0.0
    Added immediate response to desktop theme changes.
    Removed dependency on the document by using GConf instead.
    Further simplified widget selection.
    Moved terminal widget search to a separate function.
    Improved method of getting colors for Embedded Terminal.
    Added restoration of colors and terminal font when plugin is deactivated.
2010-03-01  Version 1.6.0
    Changed to default to system colors instead of black-on-white.
    Added applying editor font to Embedded Terminal.
    Simplified widget selection.
2010-02-25  Version 1.5.0
    Added response to color scheme change.
    Added response to pane additions.
    Eliminated redundant color updates.
    Eliminated most redundant widget searching.
2010-02-21  Version 1.0.1
    Added coloring of Embedded Terminal and Character Map table.
2010-02-20  Version 1.0
    Initial release

Classes:
ColorPanesPlugin -- object is loaded once by an instance of Gedit
ColorPanesWindowHelper -- object is constructed for each Gedit window

"""

TERMINAL_MATCH_COLORS = True
TERMINAL_MATCH_FONT = True

PYTERM_MATCH_COLORS = True
PYTERM_MATCH_FONT = True

import os
import sys

import gedit
import gconf
import gtk
import gtksourceview2
import pango

from .logger import Logger
LOGGER = Logger(level=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')[2])

class ColorPanesPlugin(gedit.Plugin):
    
    """
    An object of this class is loaded once by a Gedit instance.
    
    It creates a ColorPanesWindowHelper object for each Gedit main window.
    
    Public methods:
    activate -- Gedit calls this to start the plugin.
    deactivate -- Gedit calls this to stop the plugin.
    update_ui -- Gedit calls this, typically for a change of document.
    is_configurable -- Gedit calls this to check if the plugin is configurable.
    
    """
    
    def __init__(self):
        """Initialize plugin attributes and start logging."""
        LOGGER.log()
        
        gedit.Plugin.__init__(self)
        
        self.gconf_client = None
        """GConfClient for responding to changes in Gedit preferences."""
        self._gconf_cnxn = None
        """GConf connection ID for the preferences change notification."""
        
        self._instances = {}
        """Each Gedit window will get a ColorPanesWindowHelper instance."""
        
        self.terminal_colors = {}
        """Original Embedded Terminal colors before changing."""
        self.terminal_font = {}
        """Original Embedded Terminal font before changing."""
        
        self.pyterm_colors = {}
        """Original Python Terminal colors before changing."""
        self.pyterm_font = {}
        """Original Python Terminal font before changing."""
    
    def activate(self, window):
        """Start a ColorPanesWindowHelper instance for this Gedit window."""
        LOGGER.log()
        if not self._instances:
            LOGGER.log('Color Panes activating.')
            self._connect_gconf()
        self._instances[window] = ColorPanesWindowHelper(self, window)
        self._instances[window].activate()
    
    def deactivate(self, window):
        """End the ColorPanesWindowHelper instance for this Gedit window."""
        LOGGER.log()
        self._instances[window].deactivate()
        self._instances.pop(window)
        if not self._instances:
            self._disconnect_gconf()
            self.terminal_colors = {}
            self.terminal_font = {}
            LOGGER.log('Color Panes deactivated.')
    
    def update_ui(self, window):
        """(Gedit calls update_ui for each window.)"""
        LOGGER.log()
    
    def is_configurable(self):
        """Identify for Gedit that this plugin is not configurable."""
        LOGGER.log()
        return False
    
    # Respond to a change of the Gedit preferences.
    
    def _connect_gconf(self):
        """Have GConf call if the Gedit preferences change."""
        LOGGER.log()
        if not self.gconf_client:
            self.gconf_client = gconf.client_get_default()
            gconf_dir = '/apps/gedit-2/preferences'
            self.gconf_client.add_dir(gconf_dir, gconf.CLIENT_PRELOAD_NONE)
            gconf_key = gconf_dir + '/editor'
            self._gconf_cnxn = self.gconf_client.notify_add(
                gconf_key,
                lambda client, cnxn_id, entry, user_data:
                    self._on_gedit_prefs_changed())
            LOGGER.log('Connected to GConf, connection ID: %r' %
                self._gconf_cnxn)
    
    def _disconnect_gconf(self):
        """Stop having GConf call if the Gedit preferences change."""
        LOGGER.log()
        if self.gconf_client and self._gconf_cnxn:
            self.gconf_client.notify_remove(self._gconf_cnxn)
            LOGGER.log('Disconnected from GConf, connection ID: %r' %
                self._gconf_cnxn)
        self._gconf_cnxn = None
        self.gconf_client = None
    
    def _on_gedit_prefs_changed(self):
        """Respond to a change in Gedit's editor preferences."""
        LOGGER.log()
        for window in self._instances:
            self._instances[window].get_gedit_text_colors()
            self._instances[window].get_gedit_cursor_colors()
            self._instances[window].update_pane_colors()

class ColorPanesWindowHelper(object):
    
    """
    ColorPanesPlugin creates a ColorPanesWindowHelper object for each Gedit
    window.
    
    Public methods:
    activate -- ColorPanesPlugin calls this when Gedit calls activate for this
                window.
    deactivate -- ColorPanesPlugin calls this when Gedit calls deactivate for
                  this window.
    update_pane_colors -- Applies the editor colors to widgets in the side and
                          bottom panes.
    
    The plugin will update the colors in these cases:
        When the plugin is activated for the window (activate).
        When Gedit's editor preferences are changed (_on_gedit_prefs_changed).
        When the desktop theme is changed (_on_style_set).
        When a tab is added to one of the panes (_on_page_added).
    
    It does not handle the event of a view being added to an existing tab.
    
    """
    
    def __init__(self, plugin, window):
        """Initialize attributes for this window."""
        LOGGER.log()
        
        self._window = window
        """The window this ColorPanesWindowHelper runs on."""
        self._plugin = plugin
        """The ColorPanesPlugin that spawned this ColorPanesWindowHelper."""
        
        # The side and bottom panes are gtk.Notebook instances.
        # They will signal if a new tabbed view ("page") is added.
        self._handlers_per_notebook = {}
        """Signal handlers for each gtk.Notebook in the Gedit window."""
        self._notebooks = None
        """The container widgets corresponding to the side and bottom panes."""
        
        self._window_style_handler = None
        """Signal handler for when the desktop theme changes."""
        
        self._text_color = None
        self._base_color = None
        """Normal foreground and background colors per color scheme."""
        
        self._cursor_color_1 = None
        self._cursor_color_2 = None
        """Cursor colors per color scheme."""
    
    def activate(self):
        """Start this instance of Color Panes."""
        LOGGER.log()
        LOGGER.log('Color Panes activating for %s' % self._window)
        self._notebooks = self._get_notebooks(self._window)
        self.get_gedit_text_colors()
        self.get_gedit_cursor_colors()
        self.update_pane_colors()
        self._connect_window()
        self._connect_notebooks()
    
    def deactivate(self):
        """End this instance of Color Panes."""
        LOGGER.log()
        self._disconnect_notebooks()
        self._disconnect_window()
        self._restore_pane_colors()
        self._notebooks = None
        LOGGER.log('Color Panes deactivated for %s\n' % self._window)
    
    # Color widgets.
    
    def update_pane_colors(self, widget=None):
        """Apply the color scheme to appropriate widgets in the Gedit panes."""
        LOGGER.log()
        self._recolor_pane_widgets(widget)
        if widget:
            if widget.__class__.__name__ == 'GeditTerminal':
                self._update_terminals()
            elif widget.__class__.__name__ == 'PythonConsole':
                self._update_pyterms()
        else:
            self._update_terminals()
            self._update_pyterms()
    
    def _restore_pane_colors(self):
        """Restore original widget colors and terminal font."""
        LOGGER.log()
        self._text_color, self._base_color = None, None
        self._cursor_color_1, self._cursor_color_2 = None, None
        self._recolor_pane_widgets()
        self._restore_terminals()
        self._restore_pyterms()
    
    def _recolor_pane_widgets(self, widget=None):
        """Apply the color scheme to appropriate widgets in the Gedit panes."""
        LOGGER.log()
        
        widgets_to_color = set()
        if widget:
            widgets_to_color |= self._get_widgets_to_color(widget)
        else:
            for notebook in self._notebooks:
                widgets_to_color |= self._get_widgets_to_color(notebook)
        for widget in widgets_to_color:
            #LOGGER.log('Recoloring widget:\n %r' % widget)
            for state in (gtk.STATE_NORMAL, gtk.STATE_PRELIGHT):
                widget.modify_text(state, self._text_color)
                widget.modify_base(state, self._base_color)
                widget.modify_cursor(self._cursor_color_1, self._cursor_color_2)
        
    def _update_terminals(self):
        """Apply the color scheme and editor font to any terminal widgets."""
        LOGGER.log()
        terminals = set()
        for notebook in self._notebooks:
            terminals |= self._get_terminals(notebook)
        for terminal in terminals:
            if TERMINAL_MATCH_COLORS:
                if terminal not in self._plugin.terminal_colors:
                    self._store_terminal_colors(terminal)
                # If the colors are None, the other widgets will default to
                # system colors.  For the terminal widget, we need to get those
                # default colors from the widget and apply them explicitly.
                state = gtk.STATE_NORMAL
                term_fg = self._text_color or terminal.get_style().text[state]
                term_bg = self._base_color or terminal.get_style().base[state]
                terminal.set_color_foreground(term_fg)
                terminal.set_color_background(term_bg)
            if TERMINAL_MATCH_FONT:
                if terminal not in self._plugin.terminal_font:
                    self._store_terminal_font(terminal)
                gedit_font = self._get_gedit_font()
                terminal.set_font_from_string(gedit_font)
    
    def _restore_terminals(self):
        """Restore original terminal colors and font."""
        LOGGER.log()
        terminals = set()
        for notebook in self._notebooks:
            terminals |= self._get_terminals(notebook)
        for terminal in terminals:
            if TERMINAL_MATCH_COLORS:
                if terminal in self._plugin.terminal_colors:
                    term_fg, term_bg = self._plugin.terminal_colors[terminal]
                    if term_fg:
                        LOGGER.log('Restoring terminal fg color: %s' %
                                            term_fg.to_string())
                        terminal.set_color_foreground(term_fg)
                    if term_bg:
                        LOGGER.log('Restoring terminal bg color: %s' %
                                            term_bg.to_string())
                        terminal.set_color_background(term_bg)
            if TERMINAL_MATCH_FONT:
                if terminal in self._plugin.terminal_font:
                    font_string = self._plugin.terminal_font[terminal]
                    if font_string:
                        LOGGER.log('Restoring terminal font: %s' %
                                            font_string)
                        terminal.set_font_from_string(font_string)
    
    def _update_pyterms(self):
        """
        Apply the editor font and certain colors to the Python Console plugin.
        
        The Python Console is based on a gtk.TextView rather than a
        gtksourceview2.View, so it cannot directly match the color scheme of
        the Gedit editor.  But it uses gtk.TextTag objects to set coloring of
        normal text, error messages (red), and past command line entries
        (blue).  The normal text is recolored by the normal widget recoloring,
        but the assigned colors for 'error' and 'command' can clash with the
        Gedit color scheme background, e.g. past commands are blue-on-blue if
        you use the Cobalt scheme.  This function translates gtksourceview
        styles to gtk.TextTag properties to apply to the Python Console.
        """
        LOGGER.log()
        pyterms = set()
        for notebook in self._notebooks:
            pyterms |= self._get_pyterms(notebook)
        for pyterm in pyterms:
            if PYTERM_MATCH_COLORS:
                tag_styles = {
                    'error': 'def:error',
                    'command': 'def:statement',
                    }
                if pyterm not in self._plugin.pyterm_colors:
                    self._store_pyterm_colors(pyterm, tag_styles)
                for tag, style_name in tag_styles.iteritems():
                    pyc_tag = getattr(pyterm, tag)
                    style = self._get_gedit_style(style_name)
                    if style:
                        for prop in ('foreground', 'background'):
                            propset = prop + '-set'
                            style_propset = style.get_property(propset)
                            if style_propset:
                                style_prop = style.get_property(prop)
                                pyc_tag.set_property(prop, style_prop)
                            pyc_tag.set_property(propset, style_propset)
                        if style.get_property('bold'):
                            pyc_tag.set_property('weight',
                                                    pango.WEIGHT_SEMIBOLD)
                        else:
                            pyc_tag.set_property('weight', pango.WEIGHT_LIGHT)
            if PYTERM_MATCH_FONT:
                if pyterm not in self._plugin.pyterm_font:
                    self._store_pyterm_font(pyterm)
                gedit_font = self._get_gedit_font()
                gedit_font_desc = pango.FontDescription(gedit_font)
                pyterm_textview = pyterm.get_children()[0]
                pyterm_textview.modify_font(gedit_font_desc)
    
    def _restore_pyterms(self):
        """Restore original Python Console font and colors."""
        LOGGER.log()
        pyterms = set()
        for notebook in self._notebooks:
            pyterms |= self._get_pyterms(notebook)
        for pyterm in pyterms:
            if PYTERM_MATCH_COLORS:
                if pyterm in self._plugin.pyterm_colors:
                    for tag in self._plugin.pyterm_colors[pyterm]:
                        pyc_tag = getattr(pyterm, tag)
                        for prop in ('foreground', 'background'):
                            propset = prop + '-set'
                            tag_propset = (self._plugin.
                                    pyterm_colors[pyterm][tag][propset])
                            if tag_propset:
                                tag_prop = (self._plugin.
                                        pyterm_colors[pyterm][tag][prop])
                                pyc_tag.set_property(prop, tag_prop)
                            pyc_tag.set_property(propset, tag_propset)
                        weight = (self._plugin.
                                pyterm_colors[pyterm][tag]['weight'])
                        pyc_tag.set_property('weight', weight)
            if PYTERM_MATCH_FONT:
                if pyterm in self._plugin.pyterm_font:
                    font = self._plugin.pyterm_font[pyterm]
                    font_string = font.to_string()
                    if font:
                        LOGGER.log('Restoring Python Console font: %s' %
                                            font_string)
                        pyterm_textview = pyterm.get_children()[0]
                        pyterm_textview.modify_font(font)
    
    # Collect widgets
    
    def _get_notebooks(self, widget, original=True):
        """Return a set of all gtk.Notebook widgets in the Gedit window."""
        if original:
            LOGGER.log()
        notebooks = set()
        if hasattr(widget, 'get_children'):
            if (isinstance(widget, gtk.Notebook) and
                'GeditNotebook' not in type(widget).__name__):
                notebooks.add(widget)
            for child in widget.get_children():
                notebooks |= self._get_notebooks(child, False)
        if original:
            for notebook in notebooks:
                LOGGER.log('Found notebook: %r' % notebook)
        return notebooks
    
    def _get_widgets_to_color(self, widget, original=True):
        """Return a set of widgets likely to need re-coloring."""
        if original:
            LOGGER.log()
        widgets_to_color = set()
        if hasattr(widget, 'modify_text') and hasattr(widget, 'modify_base'):
            widgets_to_color.add(widget)
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                widgets_to_color |= self._get_widgets_to_color(child, False)
        return widgets_to_color
    
    def _get_terminals(self, widget, original=True):
        """Return a set of terminals."""
        if original:
            LOGGER.log()
        terminals = set()
        if (hasattr(widget, 'set_color_foreground') and
                hasattr(widget, 'set_color_background')):
            terminals.add(widget)
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                terminals |= self._get_terminals(child, False)
        return terminals
    
    def _get_pyterms(self, widget, original=True):
        """Return a set of Python Consoles (probably one)."""
        if original:
            LOGGER.log()
        pyterms = set()
        if widget.__class__.__name__ == 'PythonConsole':
            pyterms.add(widget)
        if hasattr(widget, 'get_children'):
            for child in widget.get_children():
                pyterms |= self._get_pyterms(child, False)
        return pyterms
    
    # Respond to change of the system/desktop Gnome theme.
    
    def _connect_window(self):
        """Connect to the Gedit window's signal for desktop theme change."""
        LOGGER.log()
        self._window_style_handler = self._window.connect(
                'style-set',
                lambda widget, previous_style: self._on_style_set())
        LOGGER.log('Connected to %r' % self._window)
    
    def _disconnect_window(self):
        """Disconnect signal handler from the Gedit window."""
        LOGGER.log()
        if self._window_style_handler:
            self._window.disconnect(self._window_style_handler)
            LOGGER.log('Disconnected from %r' % self._window)
    
    def _on_style_set(self):
        """Propogate the color scheme because system colors changed."""
        LOGGER.log()
        self.get_gedit_text_colors()
        self.get_gedit_cursor_colors()
        self.update_pane_colors()
        return False
    
    # Respond to addition of paned views (gtk.Notebook pages).
    
    def _connect_notebooks(self):
        """Connect to the 'add' signal of each gtk.Notebook widget."""
        LOGGER.log()
        LOGGER.log('notebooks:\n %s' %
            '\n '.join([repr(x) for x in self._notebooks]))
        for notebook in self._notebooks:
            self._handlers_per_notebook[notebook] = notebook.connect(
                'page-added', self._on_page_added)
            LOGGER.log('Connected to %r' % notebook)
    
    def _disconnect_notebooks(self):
        """Disconnect signal handlers from gtk.Notebook widgets."""
        LOGGER.log()
        for notebook in self._handlers_per_notebook:
            notebook.disconnect(self._handlers_per_notebook[notebook])
            LOGGER.log('Disconnected from %r' % notebook)
        self._handlers_per_notebook = {}
    
    def _on_page_added(self, notebook, child, page_num):
        """Propogate the color scheme because a page was added to a pane."""
        LOGGER.log()
        LOGGER.log(var='notebook')
        LOGGER.log(var='child')
        LOGGER.log(var='page_num')
        self.update_pane_colors(child)
    
    # Get the colors and font to apply.
    
    def _get_gedit_scheme(self):
        """Return Gedit's color scheme."""
        LOGGER.log()
        scheme_name = self._plugin.gconf_client.get_string(
            '/apps/gedit-2/preferences/editor/colors/scheme') or 'classic'
        LOGGER.log('Gedit color scheme: %s' % scheme_name)
        scheme_manager = self._get_gedit_style_scheme_manager()
        style_scheme = scheme_manager.get_scheme(scheme_name)
        return style_scheme
    
    def _get_gedit_style(self, style_name):
        """Return style from Gedit's color scheme."""
        LOGGER.log()
        style_scheme = self._get_gedit_scheme()
        if style_scheme:
            style = style_scheme.get_style(style_name)
        return style
    
    def _get_gedit_style_colors(self, style_name):
        """Return style colors from Gedit's color scheme."""
        LOGGER.log()
        fg_color, bg_color = None, None
        style = self._get_gedit_style(style_name)
        if style:
            fg_color, bg_color = self._get_style_colors(style)
        return fg_color, bg_color
    
    def get_gedit_text_colors(self):
        """Return foreground and background colors of Gedit's color scheme."""
        LOGGER.log()
        text_color, base_color = self._get_gedit_style_colors('text')
        if text_color and base_color:
            LOGGER.log('Gedit text color: %s' % text_color.to_string())
            LOGGER.log('Gedit base color: %s' % base_color.to_string())
        else:
            gtk_theme = self._plugin.gconf_client.get_string(
                '/desktop/gnome/interface/gtk_theme')
            LOGGER.log('GTK theme: %s' % gtk_theme)
            state = gtk.STATE_NORMAL
            gtk_theme_text_color = self._window.get_style().text[state]
            gtk_theme_base_color = self._window.get_style().text[state]
            LOGGER.log('GTK theme text color: %s' %
                gtk_theme_text_color.to_string())
            LOGGER.log('GTK theme base color: %s' %
                gtk_theme_base_color.to_string())
        self._text_color, self._base_color = text_color, base_color
    
    def get_gedit_cursor_colors(self):
        """
        Return primary and secondary cursor colors of the active Gedit view.

        Alternatively, the colors could be found this way:
            view = self._window.get_active_view()
            primary_color = view.style_get_property('cursor-color')
            secondary_color = view.style_get_property(
                              'secondary-cursor-color')
        But it would depend on the view being available and updated.
        """
        LOGGER.log()
        
        # The cursor color typically matches the (normal) text color.
        primary_color = self._get_gedit_style_colors('cursor')[0]
        if primary_color:
            LOGGER.log('Gedit scheme primary cursor color: %s' %
                             primary_color.to_string())
            calc_primary_color = primary_color
        else:
            calc_primary_color = (
                self._window.style_get_property('cursor-color') or
                self._window.get_style().text[gtk.STATE_NORMAL])
            if calc_primary_color:
                LOGGER.log('Default primary cursor color: %s' %
                             calc_primary_color.to_string())
        
        # The secondary cursor color is for a secondary insertion cursor when
        # editing mixed right-to-left and left-to-right text.
        secondary_color = self._get_gedit_style_colors('secondary-cursor')[0]
        if not secondary_color:
            # If the secondary color is not defined, and it typically isn't,
            #  then, to match gedit, it should be calculated as an average of
            #  the primary color and the base color.
            #     See gtksourcestylescheme.c:update_cursor_colors
            base_color = (self._base_color or
                          self._window.get_style().base[gtk.STATE_NORMAL])
            secondary_color = gtk.gdk.Color(
                red=(calc_primary_color.red + base_color.red) / 2,
                green=(calc_primary_color.green + base_color.green) / 2,
                blue=(calc_primary_color.blue + base_color.blue) / 2)
        LOGGER.log('Gedit secondary cursor color: %s' %
                         secondary_color.to_string())
        
        self._cursor_color_1 = primary_color
        self._cursor_color_2 = secondary_color
    
    def _get_gedit_style_scheme_manager(self):
        """Return a gtksourceview2.StyleSchemeManager imitating Gedit's."""
        LOGGER.log()
        scheme_manager = gtksourceview2.style_scheme_manager_get_default()
        gedit_styles_path = os.path.expanduser('~/.gnome2/gedit/styles')
        scheme_manager.append_search_path(gedit_styles_path)
        return scheme_manager
    
    def _get_style_colors(self, style):
        """Return GDK colors for the gtksourceview2.Style."""
        LOGGER.log()
        text_color = None
        if style and style.get_property('foreground-set'):
            text_color_desc = style.get_property('foreground')
            if text_color_desc:
                text_color = gtk.gdk.color_parse(text_color_desc)
        base_color = None
        if style and style.get_property('background-set'):
            base_color_desc = style.get_property('background')
            if base_color_desc:
                base_color = gtk.gdk.color_parse(base_color_desc)
        return text_color, base_color
    
    def _get_gedit_font(self):
        """Return the font string for the font used in Gedit's editor."""
        LOGGER.log()
        gedit_uses_system_font = self._plugin.gconf_client.get_bool(
            '/apps/gedit-2/preferences/editor/font/use_default_font')
        if gedit_uses_system_font:
            gedit_font = self._plugin.gconf_client.get_string(
                '/desktop/gnome/interface/monospace_font_name')
            LOGGER.log('System font: %s' % gedit_font)
        else:
            gedit_font = self._plugin.gconf_client.get_string(
                '/apps/gedit-2/preferences/editor/font/editor_font')
            LOGGER.log('Gedit font: %s' % gedit_font)
        return gedit_font
    
    # Record original terminal colors and font for restoring on deactivation.
    
    def _store_terminal_colors(self, terminal):
        """Record the original terminal colors before changing them."""
        LOGGER.log()
        term_fg, term_bg = self._get_term_colors_from_gconf()
        LOGGER.log('Storing terminal fg color: %s' % term_fg.to_string())
        LOGGER.log('Storing terminal bg color: %s' % term_bg.to_string())
        self._plugin.terminal_colors[terminal] = term_fg, term_bg
    
    def _get_term_colors_from_gconf(self):
        """Get the text colors from the Gnome Terminal profile in GConf."""
        LOGGER.log()
        profile = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/global/default_profile')
        # The Embedded Terminal plugin has 'Default' hard coded.
        profile = 'Default'
        term_fg_desc = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/profiles/%s/foreground_color' % profile)
        term_fg = gtk.gdk.color_parse(term_fg_desc)
        term_bg_desc = self._plugin.gconf_client.get_string(
            '/apps/gnome-terminal/profiles/%s/background_color' % profile)
        term_bg = gtk.gdk.color_parse(term_bg_desc)
        return term_fg, term_bg
    
    def _store_terminal_font(self, terminal):
        """Record the original terminal font before changing it."""
        LOGGER.log()
        self._plugin.terminal_font[terminal] = None
        pango_font = terminal.get_font()
        if pango_font:
            font_string = pango_font.to_string()
            LOGGER.log('Storing terminal font: %s' % font_string)
            self._plugin.terminal_font[terminal] = font_string
    
    def _store_pyterm_colors(self, pyterm, tag_styles):
        """Record the original Python Console colors before changing them."""
        LOGGER.log()
        self._plugin.pyterm_colors[pyterm] = {}
        tag_props = tag_styles
        for tag in tag_props:
            pyc_tag = getattr(pyterm, tag)
            self._plugin.pyterm_colors[pyterm][tag] = {}
            for prop in ('foreground', 'background'):
                propset = prop + '-set'
                tag_propset = pyc_tag.get_property(propset)
                if tag_propset:
                    tag_color = pyc_tag.get_property(prop + '-gdk')
                    tag_prop = tag_color.to_string()
                    self._plugin.pyterm_colors[pyterm][tag][prop] = tag_prop
                self._plugin.pyterm_colors[pyterm][tag][propset] = tag_propset
            weight = pyc_tag.get_property('weight')
            self._plugin.pyterm_colors[pyterm][tag]['weight'] = weight
    
    def _store_pyterm_font(self, pyterm):
        """Record the original Python Console font before changing it."""
        LOGGER.log()
        self._plugin.pyterm_font[pyterm] = None
        pango_font = pyterm.rc_get_style().font_desc
        if pango_font:
            font_string = pango_font.to_string()
            LOGGER.log('Storing Python Console font: %s' % font_string)
            self._plugin.pyterm_font[pyterm] = pango_font

