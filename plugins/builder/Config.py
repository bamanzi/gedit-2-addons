#    builder configuration
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


import gtk
try:
    import gconf
    GCONF_ROOT = '/apps/gedit-2/plugins/builder'
except:
    import mateconf as gconf
    GCONF_ROOT = '/apps/pluma/plugins/builder'
import logging
import logging.config
import os.path



GCONF_PROJECTS = GCONF_ROOT + '/projects'
# Project names are the 'Project Manager' plugin's project file.
# I'm assuming that no one is going to have a filename
# '<no project/default>'.
DEFAULT_PROJECT = '<no project/default>'

# Define values to be used if no defaults exist in gconf
INIT_COMPILE = 'make %s.o'
INIT_BUILD = 'make'
INIT_ROOT = '%d'

class Config(object):
    """ Wraps configuration data
    
        The abstract data seen by clients of Config is a dictionary with
        keys of the project file fullpath to a tuple of compile command,
        build command, and build root directory.
        
        Currently, this is a wrapper around GConf.  Data is placed in 
        GCONF_ROOT/projects/n/name, compile, build, root.  Where
        n is an arbitary integer.
    """
    def __init__(self, data_dir):
        self._l = logging.getLogger('plugin.builder')
        self._data_dir = data_dir
        gconfc = gconf.client_get_default()
        #gconfc.recursive_unset(GCONF_ROOT, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
        gconfc.add_dir(GCONF_ROOT, gconf.CLIENT_PRELOAD_RECURSIVE)
        gconfc.notify_add(GCONF_ROOT, self._key_changed)
        
        self._gconf_dirs = {}
        for gdir in gconfc.all_dirs(GCONF_PROJECTS):
            gdir_num = int(os.path.basename(gdir))
            n = gconfc.get_string(gdir + '/name')
            if n is not None:
                self._gconf_dirs[n] = gdir
            
        if DEFAULT_PROJECT not in self._gconf_dirs.keys():
            self._save_project(
                DEFAULT_PROJECT, (INIT_COMPILE, INIT_BUILD, INIT_ROOT))
    
    def get_data_dir(self):
        return self._data_dir
        
    def _key_changed(self, client, connection_id, entry, args):
        self._l.debug('Entered')
        v = entry.get_value()
        if v and v.type == gconf.VALUE_BOOL:
            new_setting = entry.get_value().get_bool()
            
    def get_default_project_name(self):
        return DEFAULT_PROJECT
    
    def _get_next_free_gdir(self):
        self._l.debug('Entered')
        gconfc = gconf.client_get_default()
        ints=[int(os.path.basename(x)) for x in gconfc.all_dirs(GCONF_PROJECTS)]
        self._l.debug('Used ints=%r' % ints)
        ints.sort()
        next_int=0
        for i in ints:
            if next_int == i:
                next_int += 1
            else:
                break
        self._l.debug('Next free is %d' % next_int)
        return '%s/projects/%03d' % (GCONF_ROOT, next_int)
            
    def _save_project(self, n, (c, b, r)):
        if n in self._gconf_dirs.keys():
            gdir = self._gconf_dirs[n]
            op = 'Updat'
        else:
            gdir = self._get_next_free_gdir()
            self._gconf_dirs[n] = gdir
            op = 'Add'
            
        self._l.info('%sing project in gdir [%s]' % (op, gdir))
        self._l.debug('       name=[%s]' % n)
        self._l.debug('    compile=[%s]' % c)
        self._l.debug('      build=[%s]' % b)
        self._l.debug('    rootdir=[%s]' % r)
        gconfc = gconf.client_get_default()
        gconfc.set_string(gdir + '/name', n)
        gconfc.set_string(gdir + '/compile', c)
        gconfc.set_string(gdir + '/build', b)
        gconfc.set_string(gdir + '/build_root', r)
        
    def get_project_names(self):
        return  self._gconf_dirs.keys()

    def get_project(self, name=DEFAULT_PROJECT):
        if name not in self._gconf_dirs.keys():
            # Of course, _gconf_dirs should always have DEFAULT_PROJECT
            # but this potential recursive call makes me nervous
            if DEFAULT_PROJECT not in self._gconf_dirs.keys():
                return (INIT_COMPILE, INIT_BUILD, INIT_ROOT)
            else:
                return self.get_project()
        
        gdir = self._gconf_dirs[name]
        gconfc = gconf.client_get_default()
        c = gconfc.get_string(gdir + '/compile') or INIT_COMPILE
        b = gconfc.get_string(gdir + '/build') or INIT_BUILD
        r = gconfc.get_string(gdir + '/build_root') or INIT_ROOT
        return (c, b, r)
        
    def reset(self, projects):
        self._l.debug('Entered')
        gconfc = gconf.client_get_default()

        # TODO Should really use a gconf.ChangeSet to avoid multiple
        # update signals being generated
        # First look for projects that have been deleted
        cur_set = set(self._gconf_dirs.keys())
        new_set = set(projects.keys())
        removed = cur_set - new_set
        for p in removed:
            if p != DEFAULT_PROJECT:
                gdir = self._gconf_dirs[p]
                self._l.info('Removing project [%s] in gdir [%s]' % (p, gdir))
                if not gconfc.recursive_unset(
                    gdir,
                    gconf.UNSET_INCLUDING_SCHEMA_NAMES):
                    self._l.warning(
                        'Failed to completely remove gdir [%s]' % gdir)
                del(self._gconf_dirs[p])
            
        # Now update/add the rest
        for name in projects.keys():
            self._save_project(name, projects[name])
            
    def _get_project_and_uri(self, doc):
        self._l.debug('Entered')
        project = (doc and doc.get_data('BelongsToProject')) or DEFAULT_PROJECT
        if project not in self._gconf_dirs.keys():
            self._l.info('No config for doc project [%s]' % project)
            project = DEFAULT_PROJECT

        uri = (doc and doc.get_uri_for_display()) or ''
        return (project, uri)

    def compile_cmd(self, doc):
        (project, uri) = self._get_project_and_uri(doc)
        cmd = self.get_project(project)[0]
        self._l.info('Compiling [%s] which is in project [%s] with [%s]' % \
            (uri, project, cmd))
        return _subst(uri, cmd)

    def build_cmd(self, doc):
        (project, uri) = self._get_project_and_uri(doc)
        cmd = self.get_project(project)[1]
        self._l.info('Building [%s] which is in project [%s] with [%s]' % \
            (uri, project, cmd))
        return _subst(uri, cmd)

    def build_root(self, doc):
        (project, uri) = self._get_project_and_uri(doc)
        rootdir = self.get_project(project)[2]
        self._l.info('build dir for [%s] which is in project [%s] is [%s]' % \
                         (uri, project, rootdir))
        return _subst(uri, rootdir)
    

def _subst(fullpath, cmd):
    (directory, filename) = os.path.split(fullpath)
    (stem, extension) = os.path.splitext(filename)
    if len(extension) > 0: extension = extension[1:]
    cmd = cmd.replace('%%', '\0\0')
    cmd = cmd.replace('%s', stem)
    cmd = cmd.replace('%e', extension)
    cmd = cmd.replace('%f', filename)
    cmd = cmd.replace('%d', directory)
    cmd = cmd.replace('%p', fullpath)
    cmd = cmd.replace('\0\0', '%')
    return cmd
        


