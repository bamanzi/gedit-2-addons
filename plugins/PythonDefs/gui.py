#!/usr/bin/env python
#-*- coding:utf-8 -*-

import gtk
import glib
import os.path
import pango
import cairo

from codeAnalyser import *
from dirAnalyser import *



def gedit_source_open(window, filename):
    uri = gio.File( filename ).get_uri()
    tab = window.get_tab_from_uri( uri )
    if tab == None:
        tab = window.create_tab_from_uri( uri, \
            encoding=None, line_pos=0, create=False, jump_to=True )
    
    while gtk.events_pending():
        gtk.main_iteration(block=False )
        
    doc = tab.get_document()
    view = tab.get_view()
    return doc, view


def gedit_source_goto_line(doc, view, line):
    it = doc.get_iter_at_line( line )
    view.scroll_to_iter( it, within_margin = 0.05, \
        use_align = True, xalign = 0.0, yalign = 0.0 )
    view.get_buffer().place_cursor( it )


def gedit_source_get_current_line(doc, view):
    buf = view.get_buffer()
    mark = buf.get_insert()
    it = buf.get_iter_at_mark( mark )
    return it.get_line()






class Gui:
    def __init__(self):
        mydir = os.path.dirname(__file__)
        builder = gtk.Builder()
        builder.add_from_file( os.path.join( mydir, "gui.glade" ) )

        self.storeDefs = builder.get_object( "storeDefs" )
        self.window = builder.get_object( "window" )
        self.treeview = builder.get_object( "treeview" )
        self.viewDoc = builder.get_object( "viewDoc" )
        self.labDoc = builder.get_object( "labDoc" )
        self.viewDir = builder.get_object( "viewDir" )
        self.hboxDir = builder.get_object( "hboxDir" )
        self.labTitle = builder.get_object( "labTitle" )
        
        self.pixbuf = [None, None, None, None, None]
        self.pixbuf[0] = gtk.gdk.pixbuf_new_from_file( \
            os.path.join( mydir, "imgs", "class.png" ) )
        self.pixbuf[1] = gtk.gdk.pixbuf_new_from_file( \
            os.path.join( mydir, "imgs", "method.png" ) )
        self.pixbuf[2] = gtk.gdk.pixbuf_new_from_file( \
            os.path.join( mydir, "imgs", "method_special.png" ) )
        self.pixbuf[3] = gtk.gdk.pixbuf_new_from_file( \
            os.path.join( mydir, "imgs", "method_get_set.png" ) )
        self.pixbuf[4] = gtk.gdk.pixbuf_new_from_file( \
            os.path.join( mydir, "imgs", "folder.png" ) )
        
        self.analysed_for = {'file':None, 'doc':None, 'view':None}
        
        self.cor_class = "#e8d293"
        self.hboxDir.set_app_paintable(True)
        self.labDoc.set_app_paintable(True)
        
        self.window.connect( "delete-event", self.on_close )
        self.window.connect( "key-press-event", self.on_window_key_press_event )
        self.treeview.connect( "cursor-changed", self.on_treeview_cursor_changed )
        self.labDoc.connect( "activate-link", self.on_labDoc_activate_link )
        self.treeview.connect( "row-activated", self.on_treeview_row_activated )
        self.hboxDir.connect( "expose-event", self.on_hboxDir_expose_event )
        self.labDoc.connect( "expose-event", self.on_labDoc_expose_event )



    def setup_for_active_document(self, gedit_window):
        doc = gedit_window.get_active_document()
        view = gedit_window.get_active_view()
        self.setup_for_source( doc, view )

    
    def setup_for_source(self, doc, view):
        self.analysed_for = {'file':None, 'doc':doc, 'view':view}

        self.analyser = CodeAnalyser()
        self.analyser.from_gedit_document( doc )
        
        self.current_line = gedit_source_get_current_line(doc, view)
        self.fill_list()

        root_path = find_path_to_root_of_gedit_document( doc )
        self.post_setup( root_path, doc.get_short_name_for_display() )
    
    
    def setup_for_file(self, filename):
        if os.path.isfile( filename ):
            self.analysed_for = {'file':filename, 'doc':None, 'view':None}
            self.analyser = CodeAnalyser()
            self.analyser.from_file( filename )
            
            self.current_line = 0
            self.fill_list()
            
            root_path = find_path_to_root( os.path.dirname(filename) )
            self.post_setup( root_path, os.path.basename(filename) )
        else:
            root_path = find_path_to_root( filename )
            self.fill_path( root_path )

            last_folder = os.path.basename(filename)
            last_btn = self.hboxDir.get_children()[-1]
            if last_btn.get_data("path") == last_folder:
                while gtk.events_pending(): gtk.main_iteration(block=False)
                self.dir_button_click(last_btn)
    

    def post_setup(self, root_path, filename):
        self.labTitle.set_markup( "Definitions for <b>%s</b>" % \
            glib.markup_escape_text(filename) )
            
        self.fill_path( root_path )
        
        # expande tudo e deixa com o foco do mouse/teclado
        #
        self.treeview.expand_all()
        self.treeview.grab_focus()
        
        # deixa marcado no item adequado (o mais próximo ou o primeiro)
        #
        if len(self.storeDefs) > 0:
            if self.closest_to_current_line != None:
                path = self.treeview.get_model().get_path( self.closest_to_current_line )
                self.treeview.set_cursor( path )
                self.treeview.scroll_to_cell( path )                 
            else:
                self.treeview.set_cursor( (0,) )
    

    def fill_list(self):
        self.storeDefs.clear()
        self.labDoc.set_markup("")
        
        self.keywords = {}
        self.closest_to_current_line = None
        closest_delta = 100000
        
        cur_class = None
        
        for item in self.analyser.items:

            tipo = item[0]
            name = item[1]
            line = "%d" % ( item[2]+1 )
            doc = item[3] if item[3] != None else ""
            params = item[4] if item[4] != None else ""
            cor = None
            
            if tipo == 'c':
                name = "<b>%s</b>" % name 
                pixbuf = self.pixbuf[0]
                parent = None
                cor = self.cor_class
            elif tipo == 'p':
                parent = cur_class
                if name[0:2] == "__":
                    pixbuf = self.pixbuf[2]
                elif name[0:3] == "get" or name[0:3] == "set":
                    pixbuf = self.pixbuf[3]
                else:
                    pixbuf = self.pixbuf[1]
            else:
                pixbuf = None
            
            if params != "":
                name = name + " <span foreground='gray'>" + glib.markup_escape_text(params) + "</span>"
            
            node = self.storeDefs.append( parent, [pixbuf, name, line, cor, True, doc, params] )
            self.keywords[ item[1] ] = node
            
            if tipo == 'c':
                cur_class = node

            delta = abs(item[2] - self.current_line)
            if delta < closest_delta or closest_to_current_line == None :
                closest_delta = delta
                closest_to_current_line = item[2]
                self.closest_to_current_line = node


    def fill_path(self, root_path):
        self.hboxDir.foreach( lambda btn: self.hboxDir.remove(btn) )
        for d in root_path:
            base_d = os.path.basename(d)
            
            lab = gtk.Label()
            lab.set_markup( "<small>%s</small>" % glib.markup_escape_text(base_d) )
            lab.show()
            b = gtk.Button()
            b.add(lab)
            b.set_data( "path", base_d )
            b.set_data( "full_path", d )
            b.connect( "clicked", self.dir_button_click )
            b.show()
            self.hboxDir.pack_start( b, expand=False )


    def dir_button_click(self, widget):
        folder = widget.get_data("full_path")
        
        def position_func(menu):
            btn_x, btn_y = widget.allocation.x, widget.allocation.y
            window_x, window_y = self.window.window.get_origin()
            vx, vy = self.viewDir.allocation.x, self.viewDir.allocation.y
            x = window_x + btn_x + vx
            y = window_y + btn_y + widget.allocation.height + vy
            return x, y, True
       
        def menu_clicked(widget):
            f = widget.get_data( "full_filename" )
            self.setup_for_file( f )
        
        menu = gtk.Menu()
        arqs = dir_files( folder )
        
        for arq in arqs:
            full_filename = os.path.join( folder, arq )
            is_file = os.path.isfile( full_filename )
            
            menuitem = gtk.ImageMenuItem( arq )
            menuitem.get_child().set_use_underline( False )
            img = gtk.Image()
            stock_img = gtk.STOCK_FILE if is_file else gtk.STOCK_DIRECTORY
            img.set_from_stock( stock_img, gtk.ICON_SIZE_MENU )
            menuitem.set_image( img )
            menuitem.show()
            menuitem.set_data( "full_filename", full_filename )
            menuitem.connect( "activate", menu_clicked )
            menu.append( menuitem )
        menu.popup( None, None, position_func, 1, 0 )
    
        


    def run(self, gedit_window):
        self.setup_for_active_document( gedit_window )
        self.window.show()            
        
        self.parent_window = gedit_window
        if self.parent_window:
            self.window.set_transient_for( self.parent_window )
        else:
            gtk.main()


    def on_window_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.on_close()
            return True
        elif event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.space:
            self.goto_selected()
            return True
        return False


    def on_treeview_cursor_changed(self, widget):
        path = ( self.treeview.get_cursor()[0] or (-1,) )
        it = self.storeDefs.get_iter( path )
        doc = self.storeDefs.get_value( it, 5 )
        params = self.storeDefs.get_value( it, 6 )
        self.labDoc.set_markup( format_doc(doc, self.keywords, params) )
    
    
    def has_keyword(self, keyword):
        return keyword in self.keywords

    def goto_keyword(self, keyword):
        it = self.keywords[keyword]
        path = self.storeDefs.get_path( it )
        self.treeview.set_cursor( path )


    def on_labDoc_activate_link(self, widget, uri):
        self.goto_keyword( uri )
        return True


    def on_treeview_row_activated(self, widget, treePath, treeViewColumn):
        self.goto_selected()
        return True


    def goto_selected(self):
        i = (self.treeview.get_cursor() or (-1,))[0]
        line = int(self.storeDefs[i][2])-1
        
        filename = self.analysed_for['file']
        doc, view = self.analysed_for['doc'], self.analysed_for['view']
        
        if filename != None:
            doc, view = gedit_source_open( self.parent_window, filename )
            
        if doc != None and view != None:
            gedit_source_goto_line( doc, view, line )

        self.on_close()


    def on_hboxDir_expose_event(self, widget, event):
        w = widget.get_allocation().width
        h = widget.get_allocation().height
        cr = event.window.cairo_create()

        grad = cairo.LinearGradient( 0, 0, 0, h-1 )
        grad.add_color_stop_rgb( 0.0,   0.1, 0.4, 0.7 )
        grad.add_color_stop_rgb( 1.0,   0.0, 0.2, 0.5 )
        cr.set_source( grad )
        cr.rectangle( 0, 0, w-1, h-1 )
        cr.fill()
        
        cr.set_line_width( 1 )
        cr.set_source_rgb( 0.0, 0.2, 0.5 )
        cr.rectangle( 0.5, 0.5, w-1, h-1 )
        cr.stroke()
        return False


    def on_labDoc_expose_event(self, widget, event):
        w = widget.get_allocation().width
        h = widget.get_allocation().height
        cr = event.window.cairo_create()
        grad = cairo.LinearGradient( 0, h/2, 0, h-1 )
        grad.add_color_stop_rgb( 0.0,   0.98, 1.0, 0.79 )
        grad.add_color_stop_rgb( 1.0,   0.70, 0.8, 0.60 )
        cr.set_source( grad )
        cr.rectangle( 0, 0, w, h )
        cr.fill()
        return False


    def on_close(self, *args):
        if self.parent_window:
            self.window.hide()
            return True
        else:
            gtk.main_quit()
            return False

