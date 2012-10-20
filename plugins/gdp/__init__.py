# Copyright (C) 2009-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""GDP Gedit Developer Plugins."""

__metaclass__ = type

__all__ = [
    'GDPWindow'
    'PluginMixin',
    ]


import mimetypes
import os

import pango as Pango
import gobject as GObject
import gtk as Gtk
try:
    import gedit
    import gnomevfs
except:
    import pluma as gedit
    import matevfs as gnomevfs


# Initialise the mimetypes for document type inspection.
mimetypes.init()
mimetypes.add_type('application/x-zope-configuation', '.zcml')
mimetypes.add_type('application/x-zope-page-template', '.pt')
mimetypes.add_type('text/x-python-doctest', '.doctest')


# Signals shared in GDP.

GObject.signal_new(
    'syntax-error-python', gedit.Document, GObject.SIGNAL_RUN_LAST,
    GObject.TYPE_NONE, ())


GObject.signal_new(
    'bzr-branch-open', gedit.Window, GObject.SIGNAL_RUN_LAST,
    GObject.TYPE_NONE, (GObject.TYPE_STRING, ))


# Common GDP classes.

class GDPWindow:
    """Decorate a `GeditWindow` with GDP state"""

    def __init__(self, window, controller, plugin):
        self.window = window
        self.controller = controller
        self.signal_ids = {}
        self.document = None
        self.ui_id = None
        if plugin.action_group_name is None:
            return
        self.action_group = Gtk.ActionGroup(name=plugin.action_group_name)
        self.action_group.set_translation_domain('gedit')
        self.action_group.add_actions(plugin.actions(controller))
        manager = self.window.get_ui_manager()
        manager.insert_action_group(self.action_group, -1)
        self.ui_id = manager.add_ui_from_string(plugin.menu_xml)

    def deactivate(self):
        """Deactivate the plugin for the window."""
        if self.ui_id is None:
            return
        manager = self.window.get_ui_manager()
        manager.remove_ui(self.ui_id)
        manager.remove_action_group(self.action_group)
        manager.ensure_update()
        self.controller.deactivate()

    def connect_signal(self, obj, signal, method):
        """Connect the signal from the provided object to a method."""
        if obj is None:
            return
        self.signal_ids[signal] = obj.connect(signal, method)

    def disconnect_signal(self, obj, signal):
        """Disconnect the signal from the provided object."""
        if obj is None:
            return
        if signal in self.signal_ids:
            obj.disconnect(self.signal_ids[signal])
            del self.signal_ids[signal]

    @property
    def active_document(self):
        """The active document in the window."""
        self.window.get_active_document()


class PluginMixin:
    """Provide common features to plugins"""

    def deactivate(self):
        """Clean up resources before deactivation."""
        raise NotImplementedError

    @staticmethod
    def is_editable(mime_type):
        """ Only search mime-types that gedit can open.

        A fuzzy match of text/ or +xml is good, but some files types are
        unknown or described as application data.
        """
        editable_types = (
            'application/javascript',
            'application/sgml',
            'application/xml',
            'application/x-httpd-eruby',
            'application/x-httpd-php',
            'application/x-latex',
            'application/x-ruby',
            'application/x-sh',
            'application/x-zope-configuation',
            'application/x-zope-page-template',
            'text/x-python-doctest',
            )
        return (
            mime_type is None
            or 'text/' in mime_type
            or mime_type.endswith('+xml')
            or mime_type in editable_types)

    def is_doc_open(self, uri):
        """Return True if the window already has a document opened for uri."""
        for doc in self.window.get_documents():
            if doc.get_uri() == uri:
                return True
        return False

    def open_doc(self, uri, jump_to=None):
        """Open document at uri if it can be, and is not already, opened."""
        if self.is_doc_open(uri):
            return
        mime_type, charset_ = mimetypes.guess_type(uri)
        if self.is_editable(mime_type):
            jump_to = jump_to or 0
            self.window.create_tab_from_uri(uri, None, jump_to, False, False)
            self.window.get_active_view().scroll_to_cursor()

    def activate_open_doc(self, uri, jump_to=None):
        """Activate (or open) a document and jump to the line number."""
        self.open_doc(uri, jump_to)
        self.window.set_active_tab(self.window.get_tab_from_uri(uri))
        if jump_to is not None:
            self.window.get_active_document().goto_line(jump_to)
            self.window.get_active_view().scroll_to_cursor()

    @property
    def active_document(self):
        """The active document in the window."""
        return self.window.get_active_document()

    @property
    def text(self):
        """The text of the active gedit.Document or None."""
        document = self.window.get_active_document()
        start_iter = document.get_start_iter()
        end_iter = document.get_end_iter()
        return document.get_text(start_iter, end_iter, True)


def set_file_line(column, cell, model, piter, cell_type):
    """Set the value as file or line information."""
    file_path = model.get_value(piter, 0)
    icon = model.get_value(piter, 1)
    line_no = model.get_value(piter, 2)
    text = model.get_value(piter, 3)
    if text is None:
        if cell_type == 'text':
            cell.props.text = file_path
        else:
            # cell_type == 'line_no'
            cell.props.text = ''
    else:
        if cell_type == 'text':
            cell.props.text = text
        else:
            # cell_type == 'line_no'
            cell.props.text = str(line_no)


def on_file_lines_row_activated(treeview, path, view_column, plugin):
    """Open the file and jump to the line."""
    treestore = treeview.get_model()
    piter = treestore.get_iter(path)
    base_dir = treestore.get_value(piter, 4)
    path = treestore.get_value(piter, 0)
    if base_dir is None or path is None:
        # There is not enough information to open a document.
        return
    #uri = 'file://%s' % os.path.abspath(os.path.join(base_dir, path))
    uri = gnomevfs.get_uri_from_local_path(os.path.abspath(os.path.join(base_dir, path)))
    line_no = treestore.get_value(piter, 2) - 1
    if line_no < 0:
        line_no = 0
    plugin.activate_open_doc(uri, jump_to=line_no)


def on_file_lines_resize(treeview, allocation, column, cell):
    """Set the width of the column to update text wrapping."""
    new_width = allocation.width - 60
    if cell.props.wrap_width == new_width:
        return
    cell.props.wrap_width = new_width
    store = treeview.get_model()
    iter = store.get_iter_first()
    while iter and store.iter_is_valid(iter):
        store.row_changed(store.get_path(iter), iter)
        iter = store.iter_next(iter)
        treeview.set_size_request(0, -1)


def setup_file_lines_view(file_lines_view, plugin, column_title):
    """Setup a TreeView to displau files and their lines."""
    treestore = Gtk.TreeStore(
        GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_INT,
        GObject.TYPE_STRING, GObject.TYPE_STRING)
    treestore.append(None, ('', None, 0, None, None))
    column = Gtk.TreeViewColumn(column_title)
    # icon.
    cell = Gtk.CellRendererPixbuf()
    cell.set_property('stock-size', Gtk.ICON_SIZE_MENU)
    cell.props.yalign = 0
    column.pack_start(cell, False)
    column.add_attribute(cell, 'icon-name', 1)
    # line number.
    cell = Gtk.CellRendererText()
    cell.props.yalign = 0
    cell.props.xalign = 1
    cell.props.alignment = Pango.ALIGN_RIGHT
    cell.props.family = 'Monospace'
    column.pack_start(cell, False)
    column.set_cell_data_func(cell, set_file_line, 'line_no')
    # line text.
    cell = Gtk.CellRendererText()
    cell.props.wrap_mode = Pango.WRAP_WORD
    cell.props.wrap_width = 310
    column.pack_start(cell, False)
    column.set_cell_data_func(cell, set_file_line, 'text')
    file_lines_view.set_model(treestore)
    file_lines_view.set_level_indentation(-18)
    file_lines_view.append_column(column)
    file_lines_view.set_search_column(0)
    file_lines_view.connect(
        'row-activated', on_file_lines_row_activated, plugin)
    file_lines_view.connect_after(
        'size-allocate', on_file_lines_resize, column, cell)
