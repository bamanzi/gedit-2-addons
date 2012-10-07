import gtk
from ipython_view import *
import pango
try:
  import gconf
  is_mate = False
except:
  import pluma as gconf
  is_mate = True

class iPythonConsole(gtk.ScrolledWindow):
  def __init__(self, namespace = {}):
    gtk.ScrolledWindow.__init__(self)

    # Get font from gedit's entries in gconf
    client = gconf.client_get_default()
    APP_KEY = "gedit-2" if not is_mate else "pluma"
    default_question = client.get_bool('/apps/%s/preferences/editor/font/use_default_font' % APP_KEY)
    if default_question == True:
      userfont = client.get_string('/desktop/%s/interface/font_name' % ("gnome" if not is_mate else "mate"))
    else:
      userfont = client.get_string('/apps/%s/preferences/editor/font/editor_font' % APP_KEY)

    self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC);
    self.set_shadow_type(gtk.SHADOW_IN)

    self.view = IPythonView()
    self.view.modify_font(pango.FontDescription(userfont))
    self.view.set_editable(True)
    self.view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
    self.add(self.view)
    self.view.show()

    self.view.updateNamespace(namespace)
