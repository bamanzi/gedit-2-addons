import gedit
import gconf

class EncodingsHelper:

  shown_in_menu = "/apps/gedit-2/preferences/encodings/shown_in_menu"

  def gedit_prefs_manager_get_shown_in_menu_encodings(self):
    list = gconf.client_get_default().get_list(self.shown_in_menu, gconf.VALUE_STRING)
    encs = []
    for enc in list:
      encs.append(gedit.encoding_get_from_charset(enc))
    return encs

  def gedit_prefs_manager_set_shown_in_menu_encodings(self, encs):
    list = []
    for enc in encs:
      list.append(enc.get_charset())
    gconf.client_get_default().set_list(self.shown_in_menu, gconf.VALUE_STRING, list)
    
  def gedit_get_all_encodings(self):
    encs = []
    i = 0
    enc = gedit.encoding_get_from_index(i)
    
    while(enc != None):
      encs.append(enc)
      i = i + 1
      enc = gedit.encoding_get_from_index(i)
      
    return encs
