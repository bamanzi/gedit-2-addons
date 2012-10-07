# gconf_py

# Use ConfigParser to make a substitue of GConf,
# in hope that it would be easier to port plugin to Windows

from ConfigParser import ConfigParser

import json
import os.path

_conffile_ = os.path.expanduser("~/.gconf_py.ini")
_config_   = ConfigParser()


if os.path.exists(_conffile_):
    _config_.read(_conffile_)

CLIENT_PRELOAD_NONE = None

VALUE_INT    = 'int'
VALUE_BOOL   = 'bool'
VALUE_STRING = 'string'
VALUE_LIST   = 'list'
VALUE_FLOAT  = 'float'
VALUE_SCHEMA = 'schema'
VALUE_INVALID = 'invalid'

UNSET_INCLUDING_SCHEMA_NAMES = 42



class GConfPyValue():
    def __init__(self, value):
        self.value = value

    def get_string(self):
        return self.value

    def get_int(self):
        return int(self.value)

class GConfPy():
    def unref(self):
        # ...
        self._save()

    def _save(self):
        fp = file(_conffile_, "wb")
        _config_.write(fp)
        fp.close()

    def add_dir(self, base, options):
        if not _config_.has_section(base):
            _config_.add_section(base)

    def dir_exists(self, path):
        return _config_.has_section(path)

    def all_dirs(self, path):
        return _config_.sections()

    def get(self, keypath):
        base = os.path.dirname(keypath)
        key  = os.path.basename(keypath)
        try:
            return GConfPyValue(_config_.get(base, key))
        except:   #NoSectionError, NoOptionError
            return None

    def get_string(self, keypath):
        v = self.get(keypath)
        if v:
            return v.get_string()
        else:
            return ""

    def set_string(self, keypath, value):
        base = os.path.dirname(keypath)
        key  = os.path.basename(keypath)
        if not _config_.has_section(base):
            _config_.add_section(base)
        _config_.set(base, key, value)
        self._save()

    def set_bool(self, keypath, value):
        if value:
            self.set_string(keypath, 'true')
        else:
            self.set_string(keypath, 'false')

    def get_bool(self, keypath):
        base = os.path.dirname(keypath)
        key  = os.path.basename(keypath)
        try:
            return _config_.getboolean(base, key)
        except:   #NoSectionError, NoOptionError, ValueError
            return False

    def get_int(self, keypath):
        base = os.path.dirname(keypath)
        key  = os.path.basename(keypath)
        try:
            return _config_.getint(base, key)
        except:   #NoSectionError, NoOptionError, ValueError
            return 0

    def set_int(self, keypath, value):
        self.set_string(keypath, "%d" % value)

    
    def set_list(self, keypath, vtype, values):
        json_values = json.dumps(values)
        self.set_string(keypath, json_values)

    def get_list(self, keypath, vtype):    
        v = self.get(keypath)
        if v:
            try:
                ret = json.loads(v.get_string())
            except:
                return []
        else:
            return []

    
    def recursive_unset(self, path, options):
        pass


    def notify_add(self, path, callback):
        # TODO: not implemented yet
        pass

def client_get_default():
    return GConfPy()

