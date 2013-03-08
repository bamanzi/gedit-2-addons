
# -*- coding: utf-8 -*-

from os.path import split as Split
import CodeGoogleWikiParser as tmpl
import gtk

HTML_PREVIEW = '/tmp/preview_gedit_webbit_panel.html'

class Plugin(object):
    def __init__(self, parent, webview, window):
        '''
        @arg parent webkitpanel instance
        @arg webview WebkitWebView instance
        @arg window GeditWindow instance
        '''
        self.webview = webview
        self.window  = window
        self.parent  = parent
        self.parser  = tmpl.Parser()
    
    def shortcut_cb(self, shortcuts, doc):
        ''' Shortcut callback
        @arg shortcuts tuple of strings
        @arg doc Gedit.active_document
        '''
        uri  =  doc.get_uri_for_display()
        html = self.parser.parse(file(uri, 'r').read())
        all_html = tmpl.HTML_HEADERS + html + tmpl.HTML_FOOTER
        file(HTML_PREVIEW,'w').write(all_html)
        uri = 'file://'+HTML_PREVIEW
        self.parent.webkit_load_uri(*Split(uri))
        
    def get_submenuitem(self):
        ''' Return the menuitem to add to webkit contextmenu 
        (and it's submenus if any)
        '''
        item = gtk.MenuItem(label="Code-google wiki parser")
        item.connect('activate', self.menuitem_cb)
        return item
    
    def menuitem_cb(self, menuitem):
        self.shortcut_cb('menuitem', self.window.get_active_document())
    
    
    
