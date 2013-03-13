#-*- coding:utf-8 -*-

import sys
import traceback
import tempfile

install_flg = {'pep8': True, 'pyflakes': True}
try:
    import pep8
except:
    install_flg['pep8'] = False
try:
    import ast
    from pyflakes import checker
except:
    install_flg['pyflakes'] = False

import gtk


def msgbox(text):
    dlg = gtk.MessageDialog(None,
                            gtk.DIALOG_MODAL,
                            gtk.MESSAGE_WARNING,
                            gtk.BUTTONS_OK,
                            text)
    dlg.run()
    dlg.destroy()


class PyCheckListStore(gtk.ListStore):

    def __init__(self):
        super(PyCheckListStore, self).__init__(int, str)

    def add(self, lineno, msg):
        self.append([lineno, msg])


class PyCheckTreeView(gtk.TreeView):

    def __init__(self, panel):
        super(PyCheckTreeView, self).__init__()

        self._panel = panel

        lin = gtk.TreeViewColumn("Line")
        lin_cell = gtk.CellRendererText()
        lin.pack_start(lin_cell)
        lin.add_attribute(lin_cell, 'text', 0)
        lin.set_sort_column_id(1)
        self.append_column(lin)

        msg = gtk.TreeViewColumn("Message")
        msg.pack_start(lin_cell)
        msg.add_attribute(lin_cell, 'text', 1)
        msg.set_sort_column_id(2)
        self.append_column(msg)


class PyCheckResultsPanel(gtk.ScrolledWindow):

    def __init__(self, window):
        super(PyCheckResultsPanel, self).__init__()

        self._window = window
        self._view = PyCheckTreeView(self)

        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.add(self._view)
        self._view.show()

    def set_model(self, model):
        self._view.set_model(model)


class PyCheckInstance(object):

    def __init__(self, plugin, window):
        self._plugin = plugin
        self._window = window

        self._merge_id = None
        self._action_group = None

        self._results = {}

        self._insert_menu()
        self._insert_panel()

    def deactivate(self):
        self._remove_menu()
        self._remove_panel()

        self._merge_id = None
        self._action_group = None

        self._panel = None
        self._results = {}

        self._window = None
        self._plugin = None

    def _insert_menu(self):
        self._action_group = gtk.ActionGroup("PythonPluginActions")
        #self._action_group.set_translation_domain('pycheck')

        self._action_group.add_actions([(
            'pycheck',
            None,
            'Python Check',
            None,
            'pep8 & pyflakes for the current document',
            self.on_action_pycheck_activate
        )])

        ui_str = """<ui>
            <menubar name="MenuBar">
                <menu name="PythonMenu" action="Python">
                    <placeholder name="ToolsOps_2">
                        <menuitem name="Python Check" action="pycheck"/>
                    </placeholder>
                </menu>
            </menubar>
        </ui>"""

        manager = self._window.get_ui_manager()
        manager.insert_action_group(self._action_group, -1)
        self._merge_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._merge_id)
        manager.remove_action_group(self._action_group)
        manager.ensure_update()

    def _insert_panel(self):
        self._panel = PyCheckResultsPanel(self._window)

        image = gtk.Image()
        image.set_from_icon_name(
            'gnome-mime-text-x-python',
            gtk.ICON_SIZE_MENU
        )

        bottom_panel = self._window.get_bottom_panel()
        bottom_panel.add_item(self._panel, 'Python Check', image)

    def _remove_panel(self):
        bottom_panel = self._window.get_bottom_panel()
        bottom_panel.remove_item(self._panel)

    def on_action_pycheck_activate(self, action):
        doc = self._window.get_active_document()

        if not doc.get_language():
            msgbox('not a python file.')
            return

        if doc.get_language().get_id().lower() != "python":
            msgbox('not a python file.')
            return

        self._window.get_bottom_panel().set_property("visible", True)
        self._window.get_bottom_panel().activate_item(self._panel)

        self._action_group.set_sensitive(doc != None)
        self._results[doc] = PyCheckListStore()
        self._results[doc].clear()
        self._panel.set_model(self._results[doc])

        try:
            self._check(doc)
        except:
            s = traceback.format_exc(sys.exc_info()[2])
            msgbox(s)

    def _check(self, doc):
        uri = doc.get_uri()
        
        #path = uri.replace('file://', '')
        try:
            import gnomevfs
        except:
            import matevfs as gnomevfs
        path = gnomevfs.get_local_path_from_uri(uri)

        res = []
        res += self._check_pep8(path)
        res += self._check_pyflakes(path)

        for e in sorted(res, key=lambda x: x['line']):
            self._results[doc].add(e['line'], e['msg'])

        return

    def _check_pep8(self, path):
        if not install_flg['pep8']:
            return [{'line': 0, 'msg': 'no install pep8'}]

        pep8.process_options([''])
        t = tempfile.TemporaryFile()
        sys.stdout = t
        pep8.input_file(path)
        t.seek(0)
        s = t.read()
        sys.stdout.close()
        sys.stdout = sys.__stdout__

        res = []
        arr = s.split('\n')
        for e in arr:
            if e.strip() == '':
                continue
            cols = e.split(':')
            res.append({
                'line': int(cols[1]),
                'msg': ':'.join(cols[3:])
            })
        return res

    def _check_pyflakes(self, path):
        if not install_flg['pyflakes']:
            return [{'line': 0, 'msg': 'no install pyflakes'}]

        arr = []
        with open(path, 'r') as f:
            for line in f:
                arr.append(line)

        res = []
        tree = ast.parse(''.join(arr), path)
        w = checker.Checker(tree, path)
        for m in w.messages:
            res.append({
                'line': m.lineno,
                'msg': m.message % m.message_args
            })

        return res
