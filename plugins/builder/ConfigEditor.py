#    builder configuration editor
#    Copyright (C) 2009 Mike Reed <gedit@amadron.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os.path

import gtk
import gconf
try:
    import gedit
except:
    import mateconf as gedit


class ConfigEditor(object):
    def __init__(self, config):
        self._l = logging.getLogger('plugin.builder')
        self._l.debug('Entered: data_dir[%s]' % config.get_data_dir())
        self._ui_builder = None
        self._glade_file = os.path.join(config.get_data_dir(), 'ConfigEditor.glade')
        self._config = config
        
    def dialog(self):
        self._l.debug('Entered')

        self._active_doc_project = None
        active_window = gedit.app_get_default().get_active_window()
        if active_window:
            active_doc = active_window.get_active_document()
            if active_doc:
                p = active_doc.get_data('BelongsToProject')
                if p:
                    self._active_doc_project = p
        self._l.debug('Current active doc project is [%s]' %
                        self._active_doc_project)

        if not self._ui_builder:
            self._l.info('Creating new dialog')
            self._ui_builder = gtk.Builder()
            self._ui_builder.add_from_file(self._glade_file)
            self._ui_builder.connect_signals({
                'destroy_event': self._destroy_event_cb,
                'response': self._response_cb,
                'project_changed_cb': self._project_changed_cb
            })
        self._setup_combo_from_config()
        return self._ui_builder.get_object('builder_config_dialog')
    
    def _setup_combo_from_config(self):
        self._l.debug('Entered')
        project_combo = self._ui_builder.get_object('project')
        project_combo.get_model().clear()
        self._projects = {}       # local copy of build/compile cmds and dir
        self._combo_to_full = {}  # converts name in project combo to fullpath
        for name in self._config.get_project_names():
            self._l.info('Adding project [%s]' % name)
            combo_name = self._get_project_display_name(name)
            self._projects[name] = self._config.get_project(name)
            self._combo_to_full[combo_name] = name
            project_combo.append_text(combo_name)

        # Set project combo active item
        project_combo = self._ui_builder.get_object('project')
        self._current_project = None
        project_combo.set_active(0)
        for row in project_combo.get_model():
            if self._combo_to_full[row[0]] == self._active_doc_project:
                project_combo.set_active_iter(row.iter)
                break
                
        # Set add and remove project buttons sensitivity
        add_button = self._ui_builder.get_object('add_project')
        if self._active_doc_project:
            if project_combo.get_active():
                add_button.set_sensitive(False)
            else:
                add_button.set_sensitive(True)
        else:
            add_button.set_sensitive(False)

    def _get_project_display_name(self, longname):
        if longname == self._config.get_default_project_name():
            return longname
        else:
            return os.path.splitext(os.path.basename(longname))[0]
    
    def _save_current_entries(self):
        if self._current_project:
            ui = self._ui_builder
            c = ui.get_object('entry_compile_cmd').get_text()
            b = ui.get_object('entry_build_cmd').get_text()
            r = ui.get_object('entry_build_root').get_text()
            self._projects[self._current_project] = (c, b, r)

    def _project_changed_cb(self, combo):
        self._l.debug("Entered")
        combo_text = combo.get_active_text()
        if combo_text is None:
            return

        self._save_current_entries()
        self._current_project = self._combo_to_full[combo_text]
        (compile_cmd, build_cmd, build_root) = \
            self._config.get_project(self._current_project)
        ui = self._ui_builder
        ui.get_object('entry_compile_cmd').set_text(compile_cmd)
        ui.get_object('entry_build_cmd').set_text(build_cmd)
        ui.get_object('entry_build_root').set_text(build_root)
        
        remove_button = ui.get_object('remove_project')
        if combo.get_active():
            remove_button.set_sensitive(True)
        else:
            remove_button.set_sensitive(False)
    
    def _destroy_event_cb(self, dialog):
        self._l.debug('Entered')
        self._ui_builder = None
        
    def _response_cb(self, dialog, response_id):
        self._l.debug('Entered: %r' % response_id)
        if response_id == 1:
            self._l.info("Add project")
            ui = self._ui_builder
            project_combo = ui.get_object('project')
            short_name = self._get_project_display_name(
                self._active_doc_project)
            project_combo.append_text(short_name)
            self._combo_to_full[short_name] = self._active_doc_project
            self._projects[self._active_doc_project] = \
                self._config.get_project(self._active_doc_project)
            ui.get_object('add_project').set_sensitive(False)
            project_combo.set_active(len(project_combo.get_model())-1)
        elif response_id == 2:
            self._l.info("Remove project")
            ui = self._ui_builder
            project_combo = ui.get_object('project')
            short_name = project_combo.get_active_text()
            index = project_combo.get_active()
            project_combo.set_active(0)
            project_combo.remove_text(index)
            del(self._projects[self._combo_to_full[short_name]])
            del(self._combo_to_full[short_name])
            if self._active_doc_project:
                ui.get_object('add_project').set_sensitive(True)
        elif response_id == gtk.RESPONSE_DELETE_EVENT:
            self._l.debug('    DELETE_EVENT')
            self._setup_combo_from_config()
            self._destroy_event_cb(dialog)
        elif response_id == gtk.RESPONSE_OK:
            self._l.debug('    OK')
            self._save_current_entries()
            self._config.reset(self._projects)
            self._ui_builder.get_object('builder_config_dialog').hide()
        elif response_id == gtk.RESPONSE_CANCEL:
            self._l.debug('    CANCEL')
            self._setup_combo_from_config()
            self._ui_builder.get_object('builder_config_dialog').hide()


