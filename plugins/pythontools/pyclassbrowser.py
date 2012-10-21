#   pyclassbrowser.py
#   A python class browser to use with gedit
#
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.

import sys
import os
try:
    import gedit
except:
    import pluma as gedit
import gtk
import re
import gobject
import pango

"""
TODO

[ ] allow correct display in two modes 

"""


#def treeViewTooltip( widget, e, tooltips, cell, emptyText="no information" ):
    #""" 
        #If emptyText is None, the cursor has to enter widget from a side that
        #contains an item, otherwise no tooltip will be displayed. """
    #try:
        #(path,col,x,y) = widget.get_path_at_pos( int(e.x), int(e.y) ) 
        #it = widget.get_model().get_iter(path)
        #value = widget.get_model().get_value(it,cell)
        #tooltips.set_tip(widget, value)
        #tooltips.enable()
    #except:
        #tooltips.set_tip(widget, emptyText)

#-------------------------------------------------------------------------------
def tokenFromString(string):
    """ Parse a string containing a function or class definition and return
        a tuple containing information about the function, or None if the
        parsing failed.

        Example: 
            "#def foo(bar):" would return :
            {'comment':True,'type':"def",'name':"foo",'params':"bar" } """

    try:
        e = r"([# ]*?)([a-zA-Z0-9_]+)( +)([a-zA-Z0-9_]+)(.*)"
        r = re.match(e,string).groups()
        #print r
        token = Token()
        token.comment = '#' in r[0]
        token.type = r[1]
        token.name = r[3]
        token.params = r[4]
        token.original = string
        return token
    except: return None # return None to skip if unable to parse

class Token:
    def __init__(self):
        self.type = None
        self.original = None # the line in the file, unparsed

        self.indent = 0
        self.name = None
        self.comment = False # if true, the token is commented, ie. inactive
        self.params = None   # string containing additional info
        self.expanded = False

        # start and end points
        self.start = 0
        self.end = 0

        self.pythonfile = None
        self.path = None # save the position in the browser

        self.parent = None
        self.children = []

    def printout(self):
        for r in range(self.indent): print "",
        print self.name,
        if self.parent: print " (parent: ",self.parent.name       
        else: print
        for tok in self.children: tok.printout()

#-------------------------------------------------------------------------------
class PythonFile(Token):
    """ A class that represents a python file.
        Manages "tokens", ie. classes and functions."""

    def __init__(self, doc):
        Token.__init__(self)
        self.doc = doc
        self.uri = doc.get_uri_for_display()
        self.type = "file"
        self.name = os.path.basename(self.uri)
        self.tokens = []

    def getTokenAtLine(self, line):
        """ get the token at the specified line number """
        for token in self.tokens:
            if token.start <= line and token.end > line:
                return token
        return None

    def parse(self, verbose=True):
        if verbose: print "parse ----------------------------------------------"
        newtokenlist = []

        indent = 0
        lastElement = None

        self.children = []

        lastToken = None
        indentDictionary = { 0: None, } # indentation level: token

        text = self.doc.get_text(*self.doc.get_bounds())
        linecount = -1
        for line in text.splitlines():
            linecount += 1
            lstrip = line.lstrip()
            ln = lstrip.split()
            if len(ln) == 0: continue

            if ln[0] in ("class","def","#class","#def"):

                token = tokenFromString(lstrip)
                if token is None: continue
                token.indent = len(line)-len(lstrip) 
                token.pythonfile = self

                # set start and end line of a token. The end line will get set
                # when the next token is parsed.
                token.start = linecount
                if lastToken: lastToken.end = linecount
                newtokenlist.append(token)

                if verbose: print "appending",token.name,
                if token.indent == indent:
                    # as deep as the last row: append the last e's parent
                    if verbose: print "(%i == %i)"%(token.indent,indent),
                    if lastToken: p = lastToken.parent
                    else: p = self
                    p.children.append(token)
                    token.parent = p
                    indentDictionary[ token.indent ] = token

                elif token.indent > indent:
                    # this row is deeper than the last, use last e as parent
                    if verbose: print "(%i > %i)"%(token.indent,indent),
                    lastToken.children.append(token)
                    token.parent = lastToken
                    indentDictionary[ token.indent ] = token

                elif token.indent < indent:
                    # this row is shallower than the last
                    if verbose: print "(%i < %i)"%(token.indent,indent),
                    if token.indent in indentDictionary.keys():
                        p = indentDictionary[ token.indent ].parent
                    else: p = self
                    p.children.append(token)
                    token.parent = p

                if verbose: print "to",token.parent.name
                idx = len(newtokenlist) - 1
                if idx < len(self.tokens):
                    if newtokenlist[idx].original == self.tokens[idx].original:
                        newtokenlist[idx].expanded = self.tokens[idx].expanded
                lastToken = token
                indent = token.indent

        # set the ending line of the last token
        if len(newtokenlist) > 0:
            newtokenlist[ len(newtokenlist)-1 ].end = linecount + 2 # don't ask

        # set new token list
        self.tokens = newtokenlist
        return True

#------------------------------------------------------------------------------------------------
class ClassBrowser( gtk.VBox ): 

    def __init__(self, window, options, brm=None):
        gtk.VBox.__init__(self)

        self.brm = brm
        self.lastDoc = None
        self.lastLines = 0
        self.lastCursor = 0
        self.filelist = {}

        #--------------- remember the window passed at init
        # this window will be used instead of passed window object, which I
        # experienced crashes with.
        self.geditwindow = window
        self.geditwindow.connect("tab_added",self.on_tab_added)
        self.geditwindow.connect("tab_removed",self.on_tab_removed)
        self.geditwindow.connect("active_tab_changed",self.on_active_tab_changed)

        #--------------- setup the browser treeview
        self.browsermodel = gtk.TreeStore(gobject.TYPE_PYOBJECT)
        self.browser = gtk.TreeView(self.browsermodel)
        self.browser.set_headers_visible(False)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(self.browser)
        col = gtk.TreeViewColumn()
        ctr = gtk.CellRendererText()
        col.pack_start(ctr,True)
        col.set_cell_data_func(ctr, self.__tokenRenderer)
        self.browser.append_column(col)

        self.browser.connect("row-activated",self.go_to_path)
        self.browser.connect("test-expand-row",self.on_expand_row)
        self.browser.connect("test-collapse-row",self.on_collapse_row)
        self.browser.connect("button_press_event",self.open_context_menu)

        #----------------------------------------------------------------------------------
        # token type, label, colour, indentation level, function name, line number, tooltip
        #tips = gtk.Tooltips()
        #tips.set_tip(self.browser, "")
        #self.browser.connect("motion-notify-event",treeViewTooltip,tips, 6, # <---
            #"point to an item to get more information")
        #self.browser.set_events( gtk.gdk.POINTER_MOTION_MASK )

        #--------------- connect to options
        self.options = options
        def refresh(w,ctr):
            ctr.set_property("scale",self.options.zoom_factor)
            self.browser.queue_draw()
        options.connect("options-changed",refresh,ctr)

        #--------------- show widget
        self.pack_start(sw)
        self.show_all()

        gobject.timeout_add(100,self.__timeout)


    def __tokenRenderer(self, column, ctr, model, it):
        """ Render the browser cell according to the token it represents. """
        tok = model.get_value(it,0)

        weight = 400
        style = pango.STYLE_NORMAL

        if tok.type == "file":
            name = tok.name
            colour = self.options.file_colour
            if tok.doc.get_modified(): style = pango.STYLE_ITALIC
        else:          
            name = tok.name+tok.params
            if tok.type == "class": name = "class "+name
            if tok.comment: name = "#"+name
            if tok.type == "class":
                weight = 600
                colour = self.options.class_colour      
            elif tok.name[:2] == "__": colour = self.options.private_colour
            else: colour = self.options.def_colour
            if tok.comment: colour = self.options.comment_colour

        ctr.set_property("text", name)
        ctr.set_property("style", style)
        #ctr.set_property("wei()ght",weight)
        ctr.set_property("foreground-gdk", colour)

    #---------------------------------------------------------------------------
    def register_document(self, doc):
        if not self.__checkPythonDoc(doc): return
        uri = doc.get_uri()
        if uri not in self.filelist.keys():
            self.filelist[uri] = PythonFile(doc)
            it = self.browsermodel.append(None,(self.filelist[uri],))
            self.filelist[uri].it = it
            if self.options.verbose: print "added:", uri

    def on_tab_added(self, window, tab):
        doc = tab.get_document()
        if not self.__checkPythonDoc(doc): return
        self.register_document(doc)

    def on_tab_removed(self, window, tab):
        doc = tab.get_document()
        if not doc: return
        if not self.__checkPythonDoc(doc): return
        uri = doc.get_uri()
        self.browsermodel.remove( self.browsermodel.get_iter(self.filelist[uri].path) )
        del self.filelist[uri]
        if self.lastDoc == doc: self.lastDoc = None
        if self.options.verbose: print "removed:", uri

    def on_active_tab_changed(self, window, tab):
        doc = tab.get_document()
        if not doc: return
        if not self.__checkPythonDoc(doc): return
        uri = doc.get_uri()
        if uri not in self.filelist.keys(): self.register_document(doc)
        if self.options.verbose: print "activated:", uri

        # hide all other files
        if self.options.fold_other_files:
            for key, pf in self.filelist.iteritems():
                if key != uri:
                    self.browser.collapse_row(pf.path)

        self.update()

    #---------------------------------------------------------------------------
    def on_expand_row(self, treeview, it, path):
        tok = self.browsermodel.get_value(it,0)
        tok.expanded = True

    def on_collapse_row(self, treeview, it, path):
        tok = self.browsermodel.get_value(it,0)
        tok.expanded = False

    def go_to_path(self, widget, path, column=None):
        it = self.browsermodel.get_iter(path)
        tok = self.browsermodel.get_value(it,0)

        # get the document
        if tok.pythonfile is None: doc = tok.doc
        else: doc = tok.pythonfile.doc

        # scroll to the correct position
        tab = gedit.gedit_tab_get_from_document(doc)
        self.geditwindow.set_active_tab(tab)
        doc.begin_user_action()
        it = doc.get_iter_at_line_offset(tok.start,0)
        doc.place_cursor(it)
        (start, end) = doc.get_bounds()
        self.geditwindow.get_active_view().scroll_to_iter(end,0.0)
        self.geditwindow.get_active_view().scroll_to_iter(it,0.0)
        self.geditwindow.get_active_view().grab_focus()
        doc.end_user_action()

    def update(self,w=None):
        doc = self.geditwindow.get_active_document()
        if doc is None: return
        uri = doc.get_uri()   
        if not self.__checkPythonDoc(doc): return
        if uri not in self.filelist.keys(): return
        self.filelist[uri].parse(False)

        def appendTokenToBrowser( token, parentit):
            it = self.browsermodel.append(parentit,(token,))
            token.path = self.browsermodel.get_path(it)
            if token.parent:
                if token.parent.expanded:
                    self.browser.expand_row(token.parent.path,False)
            for child in token.children:
                appendTokenToBrowser(child, it)

        self.browsermodel.clear()
        for uri, pf in self.filelist.iteritems():
            appendTokenToBrowser(pf, None)

        self.lastDoc = doc
        self.lastLines = doc.get_line_count()   

    def __timeout(self):
        """ Note: When a tab is added, the document is still empty. """

        #print "a",

        # get the current document
        doc = self.geditwindow.get_active_document()
        if not doc: return True
        uri = doc.get_uri()
        if uri not in self.filelist.keys():
            self.register_document(doc)
            return True

        #print "b",

        if self.lastDoc:
            # update if the active document changed
            if doc != self.lastDoc:
                if self.options.verbose: print "update trigger (active document changed)"
                self.update()
                return True

            # update if line difference at least n
            if abs(self.lastLines - doc.get_line_count()) > 5:
                if self.options.verbose: print "update trigger (line difference):",self.lastLines,doc.get_line_count()
                self.update()
                return True

            if self.lastLines != doc.get_line_count():
                it = doc.get_iter_at_mark(doc.get_insert())
                a = it.copy(); b = it.copy()
                a.backward_line(); a.backward_line()
                b.forward_line(); b.forward_line()

                t = doc.get_text(a,b)
                if t.find("class") >= 0 or t.find("def") >= 0:
                    if self.options.verbose:
                        print "update trigger (line count changed and cursor next to def or class)"
                    self.update()
                    return True

        #print "c"

        #  mark the class or function the cursor currently points at
        insert = doc.get_iter_at_mark(doc.get_insert())
        if self.lastCursor != insert.get_offset():
            self.lastCursor = insert.get_offset()
            self.__setSelected(insert.get_line(), doc)

        self.browser.queue_draw()
        return True

    def __setSelected(self, line, document):
        #if self.options.verbose: print "set selected"
        uri = document.get_uri()
        if uri not in self.filelist.keys(): return
        token = self.filelist[uri].getTokenAtLine(line)
        if token is None: token = self.filelist[uri]
        if token.path is None: return
        path = token.path
        self.browser.expand_to_path(path)
        self.browser.scroll_to_cell(path)
        self.browser.set_cursor(path)

    #---------------------------------------------------------------------------

    def get_file_level(self, token):
        """ Return the pythonfile of a token. """
        while token.type != "file":
            if token.type is None: return None
            token = token.parent
        if token.path is None: return None
        return token

    def open_context_menu(self, treeview, event):
        """ Show a context menu when the user right-clicks on the browser """

        if event.button == 3:
            x, y = int(event.x), int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)
            menu = gtk.Menu()

            if pthinfo is not None: # clicked on a token in the browser
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path)
                tok = self.browsermodel.get_value(self.browsermodel.get_iter(path),0)
                m = gtk.MenuItem('Go To "%s"'%tok.name,False); menu.append(m); m.show()
                m.connect("activate",lambda w: self.go_to_path(self.browser,path))
                m = gtk.SeparatorMenuItem(); menu.append(m); m.show() #----------------

                if self.brm:
                    m = gtk.ImageMenuItem("Find References"); menu.append(m); m.show()
                    m.connect("activate",self.findReferences,path)
                    img = gtk.Image(); img.set_from_stock(gtk.STOCK_FIND,gtk.ICON_SIZE_MENU); m.set_image( img )
                    m = gtk.SeparatorMenuItem(); menu.append(m); m.show() #----------------

                #m = gtk.MenuItem("Expand All",False); menu.append(m); m.show()
                #m.connect("activate", self.expandAll, tok)
                #img = gtk.Image(); img.set_from_stock(gtk.STOCK_INDENT,gtk.ICON_SIZE_MENU); m.set_image( img )
                pf = self.get_file_level(tok) 
                m = gtk.MenuItem('Fold "%s"'%pf.name,False); menu.append(m); m.show()
                m.connect("activate", lambda w: self.browser.collapse_row(pf.path))
                #img = gtk.Image(); img.set_from_stock(gtk.STOCK_UNINDENT,gtk.ICON_SIZE_MENU); m.set_image( img )

            # always append a refresh option.
            m = gtk.ImageMenuItem(gtk.STOCK_REFRESH); menu.append(m); m.show()
            m.connect("activate",self.update)

            menu.popup( None, None, None, event.button, event.time)

    def findReferences(self, w, path):
        it = self.browsermodel.get_iter(path)
        tok = self.browsermodel.get_value(it,0)
        if tok.pythonfile is None: return
        doc = tok.pythonfile.doc
        self.go_to_path(self.browsermodel,path)

        # select function name
        #element = self.model.get_value(self.model.get_iter(path),1)
        #funcname = self.model.get_value(self.model.get_iter(path),4)
        it = doc.get_iter_at_mark( doc.get_insert() )
        it2 = it.copy(); 
        b = tok.original.find(tok.name) + tok.indent
        it2.forward_chars( b+len(tok.name) )
        it.forward_chars( b )
        doc.move_mark_by_name("insert",it)
        doc.move_mark_by_name("selection_bound",it2)
        #print doc.get_text( *doc.get_selection_bounds() )

        # start brm
        self.brm.findReferences(w,self.geditwindow)

    def __getElementPosition(self, path):
        """ Translate treeview path to document buffer position,
            returns a tuple: (line,column) """

        doc = self.geditwindow.get_active_document()
        if doc is None: return
        element = self.model.get_value(self.model.get_iter(path),1)
    
        # make a list of all parent elements. All of them have to be found!
        it = self.model.get_iter(path)
        lst = []
        it = self.model.iter_parent(it)
        while it is not None and self.model.get_value(it,0) != "file":
            lst.append( self.model.get_value(it,1) )
            it = self.model.iter_parent(it)

        # find parent element, then subelement
        # reparse every time: document might have changed
        (start, end) = doc.get_bounds()
        text = doc.get_text(start, end)
        rootFound = False
        lc = 0
        char = 0
        for line in text.splitlines(): # split first
            ln = line.lstrip()
            if len(lst) == 0:
                if ln[:len(element)] == element:
                    char = len(line)-len(ln) # where on the line
                    break
            elif ln[:len(lst[-1])] == lst[-1]:
                lst = lst[:-1]
            lc += 1

        return (lc,char)

    def __checkPythonDoc(self,doc):
        """ Return true if gedit document is a python program """
        if doc is None: return False
        if doc.get_mime_type() != "text/x-python": return False
        return True
