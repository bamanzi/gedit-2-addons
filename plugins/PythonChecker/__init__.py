try:
    import gedit
except:
    import pluma as gedit
import gtk
import os
from os import path


class PythonCheckerFile(gtk.VBox):

    def __init__(self, geditwindow):
        gtk.VBox.__init__(self)

        # We have to use .geditwindow specifically here (self.window won't work)
        self.geditwindow = geditwindow

        self.geditwindow.connect("active_tab_state_changed", self.__new_tab)
        self.geditwindow.connect("tab_removed", self.__close_tab)


        self.commands = {'pep8': 'pep8.py %s --repeat --ignore=E501',
                         'pyflakes': 'pyflakes %s',
                         'csschecker': 'csschecker.py %s'}

        self.extensions = {'.py': ['pep8', 'pyflakes'],
                           '.css': ['csschecker']}

        self.document_uris = {}

        # Save the document's encoding in a variable for later use (when opening new tabs)
        try:
            self.encoding = gedit.encoding_get_current()
        except:
            self.encoding = gedit.gedit_encoding_get_current()

        self.check_lines = gtk.ListStore(str, str, str)

        self.results_list = gtk.TreeView(self.check_lines)

        tree_selection = self.results_list.get_selection()

        tree_selection.set_mode(gtk.SELECTION_SINGLE)
        tree_selection.connect("changed", self.__change_line)


        cell_log = gtk.TreeViewColumn("Logs")

        # Now add the cell objects to the results_list treeview object
        self.results_list.append_column(cell_log)

        # Create text-rendering objects so that we can actually
        # see the data that we'll put into the objects
        text_renderer_row = gtk.CellRendererText()
        text_renderer_col = gtk.CellRendererText()
        text_renderer_log = gtk.CellRendererText()

        cell_log.pack_start(text_renderer_log, True)
        cell_log.add_attribute(text_renderer_log, "text", 2)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled_window.add(self.results_list)

        # Pack in the scrolled window object
        self.pack_start(scrolled_window)

        # Show all UI elements
        self.show_all()


    def __change_line(self, widget):
        # Get the selection object
        tree_selection = self.results_list.get_selection()

        # Get the model and iterator for the row selected
        (model, iterator) = tree_selection.get_selected()

        if (iterator):
            # Get number line
            if model.get_value(iterator, 0).isdigit():
                row_number = int(model.get_value(iterator, 0))-1
            else:
                row_number = -1

#            if model.get_value(iterator, 1).isdigit():
#                col_number = int()-1
#            else:
#                col_number = 0
            # Get active document
            if row_number >= 0:
                self.__active_document.goto_line(row_number)
                self.geditwindow.get_active_view().scroll_to_cursor()

    def __new_tab(self, widget, tab=None):

        self.__tab = tab
        self.__active_tab = self.geditwindow.get_active_tab()
        uri = self.__active_tab.get_document().get_uri()
        self.__active_document = self.__active_tab.get_document()
        if not uri:
            return

        extension = path.splitext(uri)[1]
        if extension in self.extensions and not uri in self.document_uris:
            sid = self.__active_document.connect("saved", self.__runtest)
            self.document_uris[uri] = sid

    def __close_tab(self, widget, tab=None):
        doc = tab.get_document()
        uri = doc.get_uri()
        if uri and uri in self.document_uris:
            del self.document_uris[uri]

    def __runtest(self, widget, tab=None):

        print "running tests"
        self.check_lines.clear()

        filepath = self.__active_document.get_uri()
        if filepath.startswith('file://'):
            #filepath = filepath[7:]
            try:
                import gnomevfs
            except:
                import matevfs as gnomevfs
            filepath = gnomevfs.get_local_path_from_uri(filepath)

        doc = self.__active_document
        command_lines = []

        extension = path.splitext(filepath)[1]
        if extension in self.extensions:
            for command in self.extensions[extension]:
                command_os = self.commands[command]
                print "--> Running test: %s" % (command_os % filepath)
                command_out = os.popen(command_os % filepath)
                command_lines = command_out.readlines()
                self.check_lines.append((-1, -1, "--> Running test: %s" % (command_os % filepath)))
                for line in command_lines:
                    if ':' in line:
                        line = line.strip()
                        splitted_line = line.split(":")
                        if len(splitted_line) >= 3:
                            col_number = -1
                            row_number = -1
                            filename = splitted_line[0]
                            if splitted_line[1].strip().isdigit():
                                row_number = splitted_line[1].strip()
                            if splitted_line[2].strip().isdigit():
                                col_number = splitted_line[2].strip()
                            show_text = ':'.join(splitted_line[1:])
                            self.check_lines.append((row_number, col_number, show_text))
                        else:
                            self.check_lines.append((-1, -1, line))


class PluginHelper:

    def __init__(self, plugin, window):
        self.window = window
        self.plugin = plugin

        self.ui_id = None

        self.add_panel(window)

    def deactivate(self):
        self.remove_menu_item()

        self.window = None
        self.plugin = None

    def update_ui(self):
        pass

    def add_panel(self, window):
        panel = self.window.get_bottom_panel()

        self.results_view = PythonCheckerFile(window)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_DND_MULTIPLE, gtk.ICON_SIZE_BUTTON)
        self.ui_id = panel.add_item(self.results_view, "PythonChecker", image)

    def remove_menu_item(self):
        panel = self.window.get_side_panel()

        panel.remove_item(self.results_view)


class PythonCheckerPlugin(gedit.Plugin):

    def __init__(self):
        gedit.Plugin.__init__(self)
        self.instances = {}

    def activate(self, window):
        self.instances[window] = PluginHelper(self, window)

    def deactivate(self, window):
        self.instances[window].deactivate()

    def update_ui(self, window):
        self.instances[window].update_ui()
