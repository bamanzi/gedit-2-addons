#   pythontools.py
#
# Copyright (C) 2006 Frederic Back (fredericback@gmail.com)
# (Except the icon depicting a serpent, which was taken from the python website)
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

"""
A plugin for gedit containing a collection of tools to work with python code.

Features:
* a class browser
* an implementation of BicycleRepairMan
* other tools

"""

import sys
import os

try:
    import gedit
    import gconf
    APP_KEY = "gedit-2"
except:
    import pluma as gedit
    import mateconf as gconf
    APP_KEY = "pluma"
import gtk
import gobject
import re

from pyclassbrowser import ClassBrowser

#-------------------------------------------------------------------------------

class Options(gobject.GObject):

    __gsignals__ = {
        'options-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.__gconfDir = "/apps/%s/plugins/pyparse" % APP_KEY

        # default values
        self.private_colour = gtk.gdk.Color(50000,20000,20000)
        self.comment_colour = gtk.gdk.Color(0,0,60000)
        self.def_colour = gtk.gdk.Color(0,0,0)
        self.class_colour = gtk.gdk.Color(0,10000,0)
        self.file_colour = gtk.gdk.Color(60000,10000,10000)
        self.zoom_factor = 1.0
        self.fold_other_files = True
        self.verbose = False
    
        # create gconf directory if not set yet
        client = gconf.client_get_default()        
        if not client.dir_exists(self.__gconfDir):
            client.add_dir(self.__gconfDir,gconf.CLIENT_PRELOAD_NONE)

        # get the gconf keys, or stay with default if key not set
        try:
            # Note: This makes no sense - simply enable at startup:
            #self.autoUpdate = client.get_bool(self.__gconfDir+"/autoUpdate") or self.autoUpdate 

            self.fold_other_files = client.get_bool(self.__gconfDir+"/fold_other_files") \
                                    or self.fold_other_files 

            self.verbose = client.get_bool(self.__gconfDir+"/verbose") \
                                    or self.verbose 

            z = client.get_float(self.__gconfDir+"/tree_scale")
            if z != 0: self.zoom_factor = z

            col = client.get_string(self.__gconfDir+"/private_colour")
            if col: self.private_colour = gtk.gdk.color_parse(col)

            col = client.get_string(self.__gconfDir+"/comment_colour")
            if col: self.comment_colour = gtk.gdk.color_parse(col)

            col = client.get_string(self.__gconfDir+"/def_colour")
            if col: self.def_colour = gtk.gdk.color_parse(col)

            col = client.get_string(self.__gconfDir+"/class_colour")
            if col: self.class_colour = gtk.gdk.color_parse(col)

            col = client.get_string(self.__gconfDir+"/file_colour")
            if col: self.file_colour = gtk.gdk.color_parse(col)


        except Exception, e: # catch, just in case
            print e
        

    def create_configure_dialog(self):
        win = gtk.Window()
        win.connect("delete-event",lambda w,e: w.destroy())
        win.set_title("Python Tools")
        vbox = gtk.VBox() 

        #--------------------------------  

        notebook = gtk.Notebook()
        notebook.set_border_width(6)
        vbox.pack_start(notebook)

        vbox2 = gtk.VBox()
        vbox2.set_border_width(6) 

        box = gtk.HBox()
        box.pack_start(gtk.Label("browser scale"),False,False,6)
        treeScale = gtk.SpinButton(gtk.Adjustment(self.zoom_factor,0.1,2,0.1),0.1,1)
        box.pack_start(treeScale,False)
        vbox2.pack_start(box,False)

        box = gtk.HBox()
        fold_other_files = gtk.CheckButton("_collapse inactive files")
        fold_other_files.set_active(self.fold_other_files)
        box.pack_start(fold_other_files,False,False,6)
        vbox2.pack_start(box,False)

        box = gtk.HBox()
        verbose = gtk.CheckButton("show debug information")
        verbose.set_active(self.verbose)
        box.pack_start(verbose,False,False,6)
        vbox2.pack_start(box,False)

        notebook.append_page(vbox2,gtk.Label("Class Browser"))

        #--------------------------------       
        vbox2 = gtk.VBox()
        vbox2.set_border_width(6)

        box = gtk.HBox()
        def_colour = gtk.ColorButton()
        def_colour.set_color(self.def_colour)
        box.pack_start(def_colour,False)
        box.pack_start(gtk.Label("functions"),False,False,6)
        vbox2.pack_start(box)

        box = gtk.HBox()
        class_colour = gtk.ColorButton()
        class_colour.set_color(self.class_colour)
        box.pack_start(class_colour,False)
        box.pack_start(gtk.Label("classes"),False,False,6)
        vbox2.pack_start(box)

        box = gtk.HBox()
        private_colour = gtk.ColorButton()
        private_colour.set_color(self.private_colour)
        box.pack_start(private_colour,False)
        box.pack_start(gtk.Label("private functions"),False,False,6)
        vbox2.pack_start(box)

        box = gtk.HBox()
        comment_colour = gtk.ColorButton()
        comment_colour.set_color(self.comment_colour)
        box.pack_start(comment_colour,False)
        box.pack_start(gtk.Label("commented elements"),False,False,6)
        vbox2.pack_start(box)

        box = gtk.HBox()
        file_colour = gtk.ColorButton()
        file_colour.set_color(self.file_colour)
        box.pack_start(file_colour,False)
        box.pack_start(gtk.Label("documents"),False,False,6)
        vbox2.pack_start(box)

        notebook.append_page(vbox2,gtk.Label("Colours"))

        def setValues(w):

            # set class attributes
            self.zoom_factor = treeScale.get_adjustment().get_value()
            self.class_colour = class_colour.get_color()
            self.def_colour = def_colour.get_color()
            self.comment_colour = comment_colour.get_color()
            self.private_colour = private_colour.get_color()
            self.file_colour = file_colour.get_color()
            self.fold_other_files = fold_other_files.get_active()
            self.verbose = verbose.get_active()

            # write changes to gconf
            client = gconf.client_get_default()

            client.set_float(self.__gconfDir+"/tree_scale", self.zoom_factor)
            client.set_bool(self.__gconfDir+"/fold_other_files", self.fold_other_files)
            client.set_bool(self.__gconfDir+"/verbose", self.verbose)

            client.set_string(self.__gconfDir+"/class_colour", self.color_to_hex(self.class_colour))
            client.set_string(self.__gconfDir+"/def_colour", self.color_to_hex(self.def_colour))
            client.set_string(self.__gconfDir+"/comment_colour", self.color_to_hex(self.comment_colour))
            client.set_string(self.__gconfDir+"/private_colour", self.color_to_hex(self.private_colour))
            client.set_string(self.__gconfDir+"/file_colour", self.color_to_hex(self.file_colour))


            # commit changes and quit dialog
            self.emit("options-changed")
            win.destroy()

        box = gtk.HBox()
        b = gtk.Button(None,gtk.STOCK_OK)
        b.connect("clicked",setValues)
        box.pack_end(b,False)
        b = gtk.Button(None,gtk.STOCK_CANCEL)
        b.connect("clicked",lambda w,win: win.destroy(),win)
        box.pack_end(b,False)
        vbox.pack_start(box,False)

        win.add(vbox)
        win.show_all()        
        return win

    def color_to_hex(self, color ):
        r = str(hex( color.red / 256 ))[2:]
        g = str(hex( color.green / 256 ))[2:]
        b = str(hex( color.blue / 256 ))[2:]
        return "#%s%s%s"%(r.zfill(2),g.zfill(2),b.zfill(2))

gobject.type_register(Options)

#-------------------------------------------------------------------------------
def addComment(widget, window):
    """ Comment the selection of the current document """
    doc = window.get_active_document()
    try: (start, end) = doc.get_selection_bounds()
    except: return
    start.set_line_offset(0)
    end.forward_line()
    text = doc.get_text(start, end)

    output = ""
    for row in text.splitlines():
        newrow = ""
        flag = False
        for i in range( len(row) ):
            if row[i] in [" ","\t"] or flag:
                newrow += row[i]
                continue
            newrow += "#" + row[i]
            flag = True
        output += newrow + "\n"

    doc.begin_user_action()
    doc.delete(start, end)
    doc.insert(start, output)
    doc.end_user_action()

#-------------------------------------------------------------------------------
def removeComment(widget, window):
    """ Uncomment the selection of the current document """
    doc = window.get_active_document()
    try: (start, end) = doc.get_selection_bounds()
    except: return
    start.set_line_offset(0)
    end.forward_line()
    text = doc.get_text(start, end)

    output = ""
    for row in text.splitlines():
        newrow = ""
        flag = False
        for i in range( len(row) ):
            if row[i] in [" ","\t"] or flag:
                newrow += row[i]
                continue
            if row[i] == "#": continue
            newrow += row[i]
            flag = True
        output += newrow + "\n"

    doc.begin_user_action()
    doc.delete(start, end)
    doc.insert(start, output)
    doc.end_user_action()



#-------------------------------------------------------------------------------
class PythonToolsPlugin(gedit.Plugin):

    pyicon = [
    "14 15 7 1",
    " 	c None",
    ".	c #00FF00",
    "+	c #FF0000",
    "@	c #000000",
    "#	c #FFFF00",
    "$	c #808000",
    "%	c #0000FF",
    "   @@@        ",
    "  @$$$@       ",
    "  @%@%$@@     ",
    " @@#@#@$$@    ",
    "@$$@$@$$$$@   ",
    "@$$$$$$.$$@   ",
    "@......@$$@   ",
    "@@.+@.@@.$@   ",
    " @++@@@.$@  @@",
    " @+@@..$$@ @$@",
    "  @@..$$@  @$@",
    "  @..$$@@@@$$@",
    "  @..$$@$$$$@ ",
    "  @..$$$$$$.@ ",
    "   @.......@  "]


    def __init__(self):
        self.commentChar = "#"
        self.options = Options()
        gedit.Plugin.__init__(self)

    def create_configure_dialog(self):
        return self.options.create_configure_dialog()

    def is_configurable(self):
        return True

    def activate(self, window):
        # try to include BicycleRepairMan---------------------------------------
        try:
            import geditBRM
            self.repairBicycle = True
            self.brm = geditBRM.geditBRM(window)
        except Exception, e:
            print e
            self.repairBicycle = False        

        # add class browser widget to sidepane----------------------------------
        self.parser = ClassBrowser(window,self.options,self.brm)
        pane = window.get_side_panel()
        image = gtk.Image()
        drawable = gtk.gdk.get_default_root_window()
        pixmap, mask = gtk.gdk.pixmap_colormap_create_from_xpm_d(drawable,
            drawable.get_colormap(),None, PythonToolsPlugin.pyicon)
        image.set_from_pixmap(pixmap, mask)
        pane.add_item(self.parser, "Python Class Browser", image)

        # define actions--------------------------------------------------------
        actions = [
            ("PythonTools",None,"Python Tools",None),
            ("addpythoncomment", None, "Add Comments", None,"Add Comments",addComment),
            ("removepythoncomment", None, "Remove Comments", None,"Remove Comments",removeComment) ]

        if self.repairBicycle: # add BRM actions if available
            actions += [
                #("BRMrename", None, 
                #"rename selected function", None,"rename selected function",
                #self.brm.renameSelection) ,
                ("BRMfinddef", None, 
                "Find Definition", None,"find the definition of the selection",
                self.brm.findDefinition) , 
                ("BRMfindref", None, 
                "Find References", None,"find references to the selection",
                self.brm.findReferences) ,
            ]

        # store per window data in the window object----------------------------
        windowdata = dict()
        window.set_data("PythonToolsPluginWindowDataKey", windowdata)
        windowdata["action_group"] = gtk.ActionGroup("GeditPythonToolsPluginActions")
        windowdata["action_group"].add_actions(actions, window)
        manager = window.get_ui_manager()
        manager.insert_action_group(windowdata["action_group"], -1)
        windowdata["ui_id"] = manager.new_merge_id ()

        # create menu items-----------------------------------------------------
        submenu = """
            <ui>
              <menubar name='MenuBar'>
                <menu name='ToolsMenu' action='Tools'>
                  <placeholder name='ToolsOps_1'>
                    <menu name='PythonTools' action='PythonTools'>"""

        if self.repairBicycle:
                      #<menuitem action='BRMrename'/>


            submenu += """
                      <menuitem action='BRMfinddef'/>
                      <menuitem action='BRMfindref' />
                      <separator />"""

        submenu += """
                      <menuitem action='addpythoncomment'/>
                      <menuitem action='removepythoncomment'/>
                    </menu>
                    <separator/>
                  </placeholder>
                </menu>
              </menubar>
            </ui>"""
        manager.add_ui_from_string(submenu)

    def deactivate(self, window):
        pane = window.get_side_panel()
        pane.remove_item(self.parser)

        windowdata = window.get_data("PythonToolsPluginWindowDataKey")
        manager = window.get_ui_manager()
        manager.remove_ui(windowdata["ui_id"])
        manager.remove_action_group(windowdata["action_group"])

    def update_ui(self, window):
        self.parser.update()   
 
        view = window.get_active_view()
        windowdata = window.get_data("PythonToolsPluginWindowDataKey")
        windowdata["action_group"].set_sensitive(bool(view and view.get_editable()))
