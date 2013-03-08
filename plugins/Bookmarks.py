import gedit
import gtk

import sys
import select

import os
import gobject

import time

from threading import Thread
from threading import Timer

ui_string = """<ui>
  <menubar name="MenuBar">
    <menu name="BookmarksMenu" action="BookmarksMenuAction">
      <placeholder name="BookmarksOps_1">
        <menuitem name="AddBookmark" action="AddBookmarkAction" />
        <menuitem name="EditBookmarks" action="EditBookmarksAction" />
        <separator />
      </placeholder>
      <placeholder name="BookmarksOps_2">
      </placeholder>
    </menu>
  </menubar>
</ui>
"""

# In the Edit Bookmarks dialog, I denote folders by putting [] around them.
# This function removes brackets (or, well, anything else :P ) from a string.
def remove_brackets(str):
    return_string = ""
    
    for i in range(1, len(str) - 1):
        return_string += str[i]
        
    return (return_string)

# Wrapper type of thing.
class Bookmark:
    def __init__(self, name, path, parent):
        self.name = name
        self.path = path
        self.parent = parent

class PluginHelper:
    def __init__(self, plugin, window):
        self.window = window
        self.plugin = plugin
        
        # Any time the user makes a change to the bookmarks,
        # we'll set this variable to True so that any other
        # gedit window can get the changes through the
        # top-level idle function monitor_bookmark_changes.
        self.bookmark_change = False
        
        # Save the document's encoding in a variable for later use (when opening new tabs)
        try: self.encoding = gedit.encoding_get_current()
        except: self.encoding = gedit.gedit_encoding_get_current()
        
        # Keep track of bookmarks and any existing folders.
        self.bookmarks = []
        self.bookmark_folders = [""]
        
        # Keep track of how many bookmarks we have so we can give them
        # all unique names when adding them to the menu.
        self.bookmark_count = 0
        
        self.targets = [("example", gtk.TARGET_SAME_WIDGET, 0)]
        
        self.insert_menu_item(window)
        
        self.add_bookmark_dialog = None
        
        # Create an idle function that decides whether or not
        # the "Add Bookmark" option on the menu should be available.
        self.idle_id = gobject.timeout_add(100, self.control_add_button_state)
        
    # control_add_button_state checks to see if the current document exists
    # or is an unsaved (ever) file.  If it is a new, unsaved file, then we
    # can't very well add a bookmark for it, now can we?  :)
    def control_add_button_state(self):
        active_document = self.window.get_active_document()
        
        if (active_document):
            if (active_document.is_untitled()):
                self.add_bookmark_action.set_sensitive(False)
                
            else:
                self.add_bookmark_action.set_sensitive(True)
                
        else:
            self.add_bookmark_action.set_sensitive(False)
            
        return True
        
    # create_edit_bookmark_dialog creates a dialog that allows
    # the user to change the name of an existing bookmark / folder.
    # This is only accessed via the "Edit Bookmarks" dialog.
    def create_edit_bookmark_dialog(self, unused):
        (model, iter) = self.bookmark_treeview.get_selection().get_selected()
        current_bookmark_name = model.get_value(iter, 0)
        
        if (model.get_value(iter, 1) == True):
            current_bookmark_name = remove_brackets(current_bookmark_name)
        
        # Disable the edit/delete buttons on the Edit Bookmarks dialog until
        # the user finishes the operation (or cancels it).
        self.button_edit_bookmark.set_sensitive(False)
        self.button_delete_bookmark.set_sensitive(False)
        
        # Create the dialog and assign a function to its "destroy" event (we'll
        # want to re-enable the edit/delete buttons on the Edit Bookmarks dialog
        # when this dialog closes).
        self.dialog_edit_bookmark = gtk.Dialog("Edit Bookmark")
        self.dialog_edit_bookmark.connect("destroy", self.close_edit_bookmark_dialog)
        
        # Keep track of the TreeIter that the user chose to edit; if they change
        # their selection while this dialog is open somehow, we want to make
        # sure we're still editing the one they originally selected.
        self.currently_editing_iter = iter
        
        # Create a box for the "Name:  [_________]" line.
        box_name = gtk.HBox()
        
        # Set up an entry box for the bookmark name and default it to the current name.
        self.edit_bookmark_name = gtk.Entry()
        self.edit_bookmark_name.set_text(current_bookmark_name)
        self.edit_bookmark_name.connect("activate", self.save_edit_bookmark_dialog)
        
        # Pack a label and the entry box into the "name" box
        box_name.pack_start(gtk.Label("Name:  "), False, False)
        box_name.pack_start(self.edit_bookmark_name)
        
        # Create a second box for Save / Cancel buttons
        box_options = gtk.HBox()
        
        # Cancel button
        button_cancel = gtk.Button("Cancel")
        button_cancel.connect("clicked", self.close_edit_bookmark_dialog)
        
        # Save button
        button_save = gtk.Button("Save")
        button_save.connect("clicked", self.save_edit_bookmark_dialog)
        
        # Add the buttons to the "save/cancel" box we made.
        box_options.pack_start(button_cancel)
        box_options.pack_start(button_save)
        
        # Add both boxes into the dialog's VBox.
        self.dialog_edit_bookmark.vbox.pack_start(box_name)
        self.dialog_edit_bookmark.vbox.pack_start(box_options)
        
        # Show everything in the VBox
        self.dialog_edit_bookmark.vbox.show_all()
        
        # We call run so that the dialog runs in a modal fashion.
        # We only want the user to edit one bookmark at a time.
        result = self.dialog_edit_bookmark.run()
        
        if (result == gtk.RESPONSE_NONE or result == gtk.RESPONSE_DELETE_EVENT):
            self.dialog_edit_bookmark.destroy()
        
    # When the user clicks "Save" in the Edit (single) Bookmark dialog,
    # this function updates the TreeStore to reflect the change.
    def save_edit_bookmark_dialog(self, unused):
        (model, iter) = self.bookmark_treeview.get_selection().get_selected()
        
        # If it's a folder, we'll want to put brackets around it...
        is_folder = model.get_value(self.currently_editing_iter, 1)
        
        if (is_folder): # Add brackets
            model.set_value(self.currently_editing_iter, 0, "[%s]" % self.edit_bookmark_name.get_text())
        else:
            model.set_value(self.currently_editing_iter, 0, self.edit_bookmark_name.get_text())
        
        # Hide the Edit (single) Bookmark dialog
        self.dialog_edit_bookmark.hide()
        
        # Re-enable the Edit / Delete button on the Edit Bookmarks dialog.
        self.button_edit_bookmark.set_sensitive(True)
        self.button_delete_bookmark.set_sensitive(True)
        
    # close_edit_bookmark_dialog just re-enables the Edit / Delete
    # buttons on the Edit Bookmarks dialog.
    def close_edit_bookmark_dialog(self, unused):
        self.button_edit_bookmark.set_sensitive(True)
        self.button_delete_bookmark.set_sensitive(True)
        
    # create_edit_bookmarks_dialog launches a dialog box that allows
    # the user to reorder and modify their existing bookmarks or to
    # create new folders to place them in.
    def create_edit_bookmarks_dialog(self, unused):
        # Create the dialog
        self.dialog_edit_bookmarks = gtk.Dialog("Edit Bookmarks")
        
        # Set its default size
        self.dialog_edit_bookmarks.set_default_size(320, 480)
        
        # Create a scrolled window to hold the TreeView
        scrolled_window = gtk.ScrolledWindow()
        
        # tree_store will hold the data for each bookmark.  Only the first
        # string will actually appear in the TreeView.  The second string
        # tracks whether the item is a folder or not.  The final string
        # holds the path to the file.
        self.tree_store = gtk.TreeStore(str, bool, str) # Name, is_folder, file path
        self.bookmark_treeview = gtk.TreeView(self.tree_store)
        
        # When the user clicks a bookmark, we'll update the Edit/Delete buttons
        # to reflect whether the user has clicked on a bookmark or a folder.
        self.bookmark_treeview.get_selection().connect("changed", self.update_edit_bookmark_buttons)

        # Enable drag-and-drop.
        self.bookmark_treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                                    self.targets,
                                                    gtk.gdk.ACTION_MOVE)
        self.bookmark_treeview.enable_model_drag_dest(self.targets, gtk.gdk.ACTION_MOVE)
                                                  
        # Connect a function that will handle drag-and-drop logic.
        self.bookmark_treeview.connect("drag_data_received", self.drag_data_receive)
        
        # Create a cell for the TreeView and add in a Text Renderer object.
        cell_name = gtk.TreeViewColumn("Drag and Drop as desired!")
        self.bookmark_treeview.append_column(cell_name)
        cell_renderer = gtk.CellRendererText()
        cell_name.pack_start(cell_renderer, True)
        cell_name.add_attribute(cell_renderer, "text", 0)
        
        # Now, go through all of our bookmarks and add them to the tree store.
        for family in self.bookmarks:
            # If the first member of the family doesn't have a parent, then
            # it goes on the top level without a parent.
            if (family[0].parent == ""):
                self.tree_store.append(None, (family[0].name, False, family[0].path))
                
            # On the other hand, if it has a parent, then we want to first add
            # a "folder" TreeIter and then add all bookmarks with that particular
            # parent folder as children to that TreeIter.
            else:
                parent_iter = self.tree_store.append(None, ("[%s]" % family[0].parent, True, ""))
                
                for each in family:
                    self.tree_store.append(parent_iter, (each.name, False, each.path))
        
        # Add the TreeView to our scrolled window, then put the scrolled window into the dialog.
        scrolled_window.add(self.bookmark_treeview)
        self.dialog_edit_bookmarks.vbox.pack_start(scrolled_window)
        
        # Create a box to hold the "New Folder" button.
        box_new_folder = gtk.HBox()        
        button_new_folder = gtk.Button("Make new folder")
        button_new_folder.connect("clicked", self.add_folder)
        
        # Create a box to hold the "Edit Bookmark" button.
        box_edit_bookmark = gtk.HBox()
        self.button_edit_bookmark = gtk.Button("Edit Selected Bookmark")
        self.button_edit_bookmark.connect("clicked", self.create_edit_bookmark_dialog)
        
        # Create a box to hold the "Delete Bookmark" button.
        box_delete_bookmark = gtk.HBox()
        self.button_delete_bookmark = gtk.Button("Delete Selected Bookmark")
        self.button_delete_bookmark.connect("clicked", self.delete_selected_bookmark)
        
        # Add buttons to boxes
        box_new_folder.pack_start(button_new_folder)
        box_edit_bookmark.pack_start(self.button_edit_bookmark)
        box_delete_bookmark.pack_start(self.button_delete_bookmark)
        
        # Finally, create a box for the Save/Cancel buttons.
        box_options = gtk.HBox()
        
        button_cancel = gtk.Button("Cancel")
        button_cancel.connect("clicked", self.close_edit_bookmarks_dialog)
        
        button_save = gtk.Button("Save")
        button_save.connect("clicked", self.save_bookmarks)
        button_save.connect("clicked", self.close_edit_bookmarks_dialog)
        
        box_options.pack_start(button_cancel)
        box_options.pack_start(button_save)
        
        # Add all of our button-holding boxes into the dialog.
        self.dialog_edit_bookmarks.vbox.pack_start(box_new_folder, False, False)
        self.dialog_edit_bookmarks.vbox.pack_start(box_edit_bookmark, False, False)
        self.dialog_edit_bookmarks.vbox.pack_start(box_delete_bookmark, False, False)
        self.dialog_edit_bookmarks.vbox.pack_start(box_options, False, False)
        
        # Show all our objects.
        self.dialog_edit_bookmarks.vbox.show_all()
        
        # Show the dialog.
        self.dialog_edit_bookmarks.show()
        
    def close_edit_bookmarks_dialog(self, unused):
        self.dialog_edit_bookmarks.destroy()
        
    # update_edit_bookmark_buttons updates the Edit/Delete buttons in
    # the Edit Bookmarks dialog to reflect whether the current selection
    # is a Bookmark or a Folder.
    def update_edit_bookmark_buttons(self, unused):
        (model, iter) = self.bookmark_treeview.get_selection().get_selected()
        
        # Make sure there's an actual selection.
        if (iter):
            is_folder = model.get_value(iter, 1)
        
            # Set the text as needed.
            if (is_folder):
                self.button_edit_bookmark.set_label("Edit Selected Folder")
                self.button_delete_bookmark.set_label("Delete Selected Folder")
            else:
                self.button_edit_bookmark.set_label("Edit Selected Bookmark")
                self.button_delete_bookmark.set_label("Delete Selected Bookmark")
            
        return True
            
    # delete_selected_bookmark removes the current TreeIter and any children
    # it might have from the tree store.
    def delete_selected_bookmark(self, unused):
        (model, iter) = self.bookmark_treeview.get_selection().get_selected()
        
        # Make sure we have a selection...
        if (iter):
        
            # If it has children...
            if (model.iter_has_child(iter)):
            
                # Remove each child in reverse.
                for i in range(model.iter_n_children(iter) - 1, -1, -1):
                    child_iter = model.iter_nth_child(iter, i)
                    self.tree_store.remove(child_iter)
        
            # Remove the selected TreeIter.
            self.tree_store.remove(iter)
        
        return True
    
    # save_bookmarks goes through the TreeView and builds a string
    # with the updated bookmark arrangement.  Then it saves that
    # string to the bookmarks.txt file.
    def save_bookmarks(self, unused):
        tree_selection = self.bookmark_treeview.get_selection()
        (model, row_selected) = tree_selection.get_selected()
        
        # Build the data into this string.
        output_string = "BOOKMARKS FILE -- EDIT AT YOUR OWN PERILOUS RISK!!!"
        
        # Get the very first TreeIter in the TreeView.
        root_iter = model.get_iter_root()
        
        # Loop through all TreeIters until none remains.
        while (root_iter != None):
            
            # If it has children, then it's a folder and we're not actually
            # going to write this TreeIter to file.  We are going to use
            # its name as the value for the "parent" of each child TreeIter, though.
            if (model.iter_has_child(root_iter)):
                # Get the first child.
                child_iter = model.iter_children(root_iter)
                
                # Store the folder name in a variable.
                folder_name = remove_brackets(model.get_value(root_iter, 0))
                
                # Loop through and children until none remains.
                while (child_iter != None):
                    
                    # Add the Bookmark to the output string.
                    output_string += "\n%s\n%s\n%s" % (folder_name, model.get_value(child_iter, 0), model.get_value(child_iter, 2))
                    
                    # Continue through additional children...
                    child_iter = model.iter_next(child_iter)
                    
                # After looping through all children, continue on to next
                # top-level TreeIter...
                root_iter = model.iter_next(root_iter)
            else:
                # Add the Bookmark (it will have no parent folder) to the output string.
                output_string += "\n\n%s\n%s" % (model.get_value(root_iter, 0), model.get_value(root_iter, 2))
                
                # Continue through all top-level TreeIters...
                root_iter = model.iter_next(root_iter)
                
        path = os.path.expanduser( '~' ) + "/.gnome2/gedit/plugins/"
        
        # Save the bookmarks.
        file = open(os.path.join(path, 'bookmarks.txt'), "w")
        file.write(output_string)
        file.close()
        
        # Remove the bookmarks from the menu
        self.remove_bookmarks_from_menu()
        
        # Set bookmark_change to True (global idle function monitors this variable)
        self.bookmark_change = True
        
        # Reload the bookmarks menu to reflect the user's changes.
        self.load_bookmarks()
        self.add_bookmarks_to_menu()
        
    def remove_bookmarks_from_menu(self):
        manager = self.window.get_ui_manager()
        
        # Get all of the actions in the action group.
        all_actions = self.action_group.list_actions()
        
        # We want to delete all actions (except for the actions for the basic menu functions).
        for each in all_actions:
            if (not (each.get_name() in ("BookmarksMenuAction", "AddBookmarkAction", "EditBookmarksAction"))):
                self.action_group.remove_action(each)
        
        # Remove all Bookmarks and folders from the menu.
        manager.remove_ui(self.ui_id2)
        
        # Make sure everything's updated.
        manager.ensure_update()
        
    # copy_row copies the currently-dragged row and any of its children
    # to a new location.  It decides whether it can move to where the
    # user has specified or whether we need to move it to a slightly
    # different location.  (e.g., You can't put one bookmark inside another
    # bookmark.)
    def copy_row(self, treeview, model, iter_to_copy, target_iter, pos):
        new_row_data = []
        
        # Add the source TreeIter's data into a new list
        for i in range(0, 3):
            new_row_data.append(model.get_value(iter_to_copy, i))
            
        # We'll want to know whether we're dragging a Bookmark or a Folder.
        src_is_folder = model.get_value(iter_to_copy, 1)
        
        # If the user is dragging it into an empty area, we'll append
        # the dragged item to the end of the list.  Thus, we won't have
        # a target.
        target_is_folder = None
        if (target_iter): # But if we do have a target, we want to know if the target
            target_is_folder = model.get_value(target_iter, 1) # is a folder or not...
        
        new_iter = None # We'll store the TreeIter we create in this.
        
        if (pos in (gtk.TREE_VIEW_DROP_INTO_OR_BEFORE, gtk.TREE_VIEW_DROP_INTO_OR_AFTER)):
            # If we're dragging a folder, we definitely can't put it in another folder.
            # We also want to make sure we're not trying to put it inside an iter that
            # is already in another folder; otherwise, insert_after would still be making
            # it a subfolder.
            if (src_is_folder):
                iter_parent = model.iter_parent(target_iter)
                
                # If the target iter had a parent, then put this folder after that entire folder.
                if (iter_parent):
                    new_iter = model.insert_after(None, iter_parent, new_row_data)
                # This is a top level element, so it's safe to put this folder after it.
                # It will remain a top-level folder.
                else:
                    new_iter = model.insert_after(None, target_iter, new_row_data)
                    
            # If we're dragging a bookmark, then make sure we're putting it in a folder.
            # If we're trying to put it inside another bookmark, then instead we'll
            # place it after that bookmark.
            else:
                if (target_is_folder):
                    new_iter = model.append(target_iter, new_row_data)
                else:
                    iter_parent = model.iter_parent(target_iter)
                    new_iter = model.insert_after(iter_parent, target_iter, new_row_data)
                    
        elif (pos == gtk.TREE_VIEW_DROP_BEFORE):
            if (src_is_folder):
                iter_parent = model.iter_parent(target_iter)
                
                if (iter_parent):
                    new_iter = model.insert_before(None, iter_parent, new_row_data)
                else:
                    new_iter = model.insert_before(None, target_iter, new_row_data)
                    
            else:
                new_iter = model.insert_before(None, target_iter, new_row_data)
                
        elif (pos == gtk.TREE_VIEW_DROP_AFTER):
            if (src_is_folder):
                iter_parent = model.iter_parent(target_iter)
                
                if (iter_parent):
                    new_iter = model.insert_after(None, iter_parent, new_row_data)
                else:
                    new_iter = model.insert_after(None, target_iter, new_row_data)
                    
            else:
                new_iter = model.insert_after(None, target_iter, new_row_data)
            
        elif (pos == "AFTER"):
            new_iter = model.append(None, new_row_data)
            
        # Copy any children the dragged TreeIter may have had.
        if (model.iter_has_child(iter_to_copy)):
            for i in range(0, model.iter_n_children(iter_to_copy)):
                next_iter_to_copy = model.iter_nth_child(iter_to_copy, i)
                self.copy_row(treeview, model, next_iter_to_copy, new_iter, gtk.TREE_VIEW_DROP_INTO_OR_BEFORE)

    # drag_data_receive gets called whenever we drop a dragged row somewhere.
    # It's going to make sure the drag is legal, do a couple other things,
    # and then copy the row(s) in question.
    def drag_data_receive(self, treeview, context, x, y, selection, info, time):
        (model, src_iter) = treeview.get_selection().get_selected()
        
        drop_info = treeview.get_dest_row_at_pos(x, y)
        
        if (drop_info):
            # Which TreeIter are we dropping this on/around?
            target_iter = model.get_iter(drop_info[0])
            
            # We can't go and put a folder inside one of its children or itself...
            if (not model.is_ancestor(src_iter, target_iter)):
                
                # One call to copy_row also copies any children the row has.
                self.copy_row(treeview, model, src_iter, target_iter, drop_info[1])
            
                context.finish(True, True, time)
                
            else:
                context.finish(False, False, time)
            
        else:
            # Use "AFTER" to tell it to append it to the end of the list.
            self.copy_row(treeview, model, src_iter, None, "AFTER")
            
            context.finish(False, False, time)
            
    # add_folder adds a new TreeIter to the Edit Bookmarks dialog and scrolls to the bottom.
    def add_folder(self, unused):
        (model, iter) = self.bookmark_treeview.get_selection().get_selected()
        
        # Create a new list with the Folder attributes needed...
        folder_data = ["[New Folder]", True, ""]
        
        # Add it...
        model.append(None, folder_data)
        
        # Scroll to the end!
        self.bookmark_treeview.set_cursor(len(self.tree_store) - 1)
        
        return True

    # create_add_bookmark_dialog creates a small dialog for the user
    # to name their Bookmark and to choose a Folder (if desired).
    def create_add_bookmark_dialog(self, unused):
        self.add_bookmark_dialog = gtk.Dialog("Add Bookmark Dialog")
        
        # Name of the bookmark
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.add_bookmark)
        
        # Create a box for the "Name:  [__________]" line
        box_name = gtk.HBox()
        
        # Add the label and the Entry box to the "name line" box
        box_name.pack_start(gtk.Label("Name:  "))
        box_name.pack_start(self.entry)
        
        # Add a label and then the "name line" box
        self.add_bookmark_dialog.vbox.pack_start(gtk.Label("Enter a name for this bookmark"))
        self.add_bookmark_dialog.vbox.pack_start(box_name, False, False)
        
        # Create a box to hold the "Folder:  [__________]" line
        box_folder = gtk.HBox()
        
        # Add a label to the side
        box_folder.pack_start(gtk.Label("Folder:  "), False, False)
        
        # Create a ComboBox that will hold the existing Folder names
        self.add_bookmark_combo_box = gtk.combo_box_new_text()
        
        self.add_bookmark_combo_box.append_text("") # For "no folder"
        
        # Loop through existing folders and add them to the ComboBox
        for folder in self.bookmark_folders:
            self.add_bookmark_combo_box.append_text(folder)
        
        # Add the ComboBox to the "folder name" line
        box_folder.pack_start(self.add_bookmark_combo_box)
        
        # Add the "folder name" line to the dialog
        self.add_bookmark_dialog.vbox.pack_start(box_folder)
        
        # Create one last box for the Add/Cancel buttons
        box_options = gtk.HBox()
        
        # Cancel button
        button_cancel = gtk.Button("Cancel")
        button_cancel.connect("clicked", self.hide_add_bookmark_dialog)
        
        # Add button
        button = gtk.Button("Add")
        button.connect("clicked", self.add_bookmark)
        
        # Add the buttons into the box
        box_options.pack_start(button_cancel)
        box_options.pack_start(button)
        
        # Add the "buttons box" into the dialog
        self.add_bookmark_dialog.vbox.pack_start(box_options)
        
        # Show all of the elements
        self.add_bookmark_dialog.vbox.show_all()
        
        # Show the dialog
        self.show_add_bookmark_dialog(None)
        
    # add_bookmark grabs the name from the "Name Entry box," the current document's
    # path, and the desired folder (if any) and append the information to the
    # bookmarks.txt file.  It also adds a new item to the menu for the new bookmark.
    def add_bookmark(self, source):
        path = os.path.expanduser( '~' ) + "/.gnome2/gedit/plugins/"
        file = open(os.path.join(path, 'bookmarks.txt'), "a")
        
        # Get the bookmark's name
        bookmark_name = self.entry.get_text()
        if (bookmark_name.lstrip().rstrip() == ""):
            bookmark_name = "Untitled"
            
        # Get the path and parent/folder
        bookmark_path = self.window.get_active_document().get_uri()
        bookmark_parent = self.add_bookmark_combo_box.get_active_text()
        
        if (bookmark_parent == None):
            bookmark_parent = ""
        
        # Add the data to the bookmarks.txt file
        file.write("\n%s\n%s\n%s" % (bookmark_parent, bookmark_name, bookmark_path))
        
        # Close the file
        file.close()
        
        # Get the window manager
        manager = self.window.get_ui_manager()
        
        # Set an action name (just bookmark1, bookmark2, whatever)
        action_name = "bookmark%d" % self.bookmark_count
        
        # Set the path of the menu destination
        menu_path = '/MenuBar/BookmarksMenu/BookmarksOps_2'
        if (bookmark_parent != ""):
            menu_path += "/submenu_%s" % bookmark_parent.replace(" ", "_")
            
        self.remove_bookmarks_from_menu()
        
        self.load_bookmarks()
        self.add_bookmarks_to_menu()
        
        self.bookmark_change = True
        
        self.hide_add_bookmark_dialog(None)
        
        return
        
        ######################################
        
        # Add the Bookmark 
        manager.add_ui(merge_id = self.ui_id2,
                       path=menu_path,
                       name=action_name,
                       action=action_name,
                       type=gtk.UI_MANAGER_MENUITEM,
                       top=False)

        # Create an action for the Bookmark
        bookmark_action = gtk.Action(name=action_name,
                                     label=bookmark_name,
                                     tooltip=bookmark_path,
                                     stock_id=None)

        # Tell the bookmark to load the file in question on click
        bookmark_action.connect("activate", lambda a,x=bookmark_path: self.open_file(x))
        bookmark_action.set_visible(True) # Make it visible
                                         
        # Add the new bookmark action
        self.action_group.add_action(bookmark_action)
        
        # Increase the bookmark count
        self.bookmark_count += 1
        
        # Hide the "Add Bookmark" dialog
        self.hide_add_bookmark_dialog(None)
        
        # Set bookmark_change to True (global idle function monitors this variable)
        self.bookmark_change = True

    def deactivate(self):
        self.remove_bookmarks_from_menu()
        self.remove_menu_item()
        
        gobject.source_remove(self.idle_id)
        
        self.window = None
        self.plugin = None
        self.action_group = None
        
    def update_ui(self):
        return True
        
    def show_add_bookmark_dialog(self, unused):
        current_filename = os.path.basename(self.window.get_active_document().get_uri())
        
        self.entry.set_text(current_filename)
        self.add_bookmark_dialog.show()
        
    def hide_add_bookmark_dialog(self, unused):
        self.add_bookmark_dialog.hide()
        
        return True
        
    def open_file(self, src):
        # First let's make sure the file exists.  If it doesn't exist,
        # prompt them for how to handle the missing file.
        if (not os.path.exists(src.replace("file://", "").replace("%20", " "))):
            result = self.ask_about_missing_file(src)
            
            return
        
        current_documents = self.window.get_documents()
        
        # Make sure the document isn't already open
        for each in current_documents:
            if (each.get_uri() == src):
                # If it's already open, then focus on that tab and return
                self.window.set_active_tab(gedit.tab_get_from_document(each))
                
                return
            
        # If it isn't already open, then let's see if we're on an unchanged, untitled
        # document.  If so, we'll close it and replace it...
        active_document = self.window.get_active_document()
        
        # Make sure there IS an active document!
        if (active_document):
            if (active_document.is_untouched() and active_document.is_untitled()):
                self.window.close_tab(gedit.tab_get_from_document(active_document))
                #active_document.load(src, self.encoding, 1, True)
                
                self.window.create_tab_from_uri(src, self.encoding, 0, True, True)
            
                return
            
        # If it isn't open, open it...
        self.window.create_tab_from_uri(src, self.encoding, 0, True, True)
        
    def open_all_bookmarks_in_folder(self, folder_name):
        for family in self.bookmarks:
            if (family[0].parent == folder_name):
                for each in family:
                    self.open_file(each.path)
                    
                return
                
    def ask_about_missing_file(self, src):
        missing_file_dialog = gtk.Dialog("File doesn't exist")
        missing_file_dialog.set_default_size(320, 0)
        missing_file_dialog.connect("destroy", self.close_missing_file_dialog)
        
        box_warning = gtk.HBox()
        
        warning_image = gtk.Image()
        warning_image.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DND)
        
        box_warning.pack_start(warning_image, False, False)
        box_warning.pack_start(gtk.Label("  File %s doesn't exist!" % os.path.basename(src)), False, False)
        
        missing_file_dialog.vbox.pack_start(box_warning, False, False)        
        missing_file_dialog.vbox.pack_start(gtk.Label("\nWhat do you want to do?\n"), False, False)
        
        button_cancel = gtk.Button("Cancel")
        button_cancel.connect("clicked", self.close_missing_file_dialog)
        
        button_create_file = gtk.Button("Create File")
        button_create_file.connect("clicked", lambda a,x=src: self.create_and_open_file(x, None))
        button_create_file.connect("clicked", self.close_missing_file_dialog)
        
        missing_file_dialog.vbox.pack_start(button_cancel)
        missing_file_dialog.vbox.pack_start(button_create_file)
        
        missing_file_dialog.vbox.show_all()
        
        result = missing_file_dialog.run()
        
        if (result == gtk.RESPONSE_NONE or result == gtk.RESPONSE_DELETE_EVENT):
            missing_file_dialog.destroy()
        
    # close_missing_file_dialog (attached to a "Cancel" button) finds
    # the parent dialog and destroys it.
    def close_missing_file_dialog(self, object):
        # The parent is the dialog's VBox
        object_parent = object.get_parent()
        
        if (object_parent):
            # Now get the actual dialog (parent of the VBox)
            object_grandparent = object_parent.get_parent()
            
            if (object_grandparent):
                # Destroy the dialog
                object_grandparent.destroy()
        
        return False
            
    def create_and_open_file(self, src, object):
        file = open(src.replace("file://", ""), "w")
        file.write("")
        file.close()
        
        #self.close_missing_file_dialog(object)
        
        self.open_file(src)
        
        return False
        
    def insert_menu_item(self, window):
        manager = self.window.get_ui_manager()
        
        self.action_group = gtk.ActionGroup("PluginActions")
        
        bookmark_menu_action = gtk.Action(name="BookmarksMenuAction",
                                          label="Bookmarks",
                                          tooltip="View Bookmarks",
                                          stock_id=None)
                                          
        self.action_group.add_action(bookmark_menu_action)
        
        self.add_bookmark_action = gtk.Action(name="AddBookmarkAction",
                                         label="Add Bookmark...",
                                         tooltip="Add the current document to your bookmarks list",
                                         stock_id=None)
                                         
        self.add_bookmark_action.connect("activate", self.create_add_bookmark_dialog)
        self.add_bookmark_action.set_sensitive(False)
                                         
        edit_bookmarks_action = gtk.Action(name="EditBookmarksAction",
                                           label="Edit Bookmarks...",
                                           tooltip="Manage your bookmarks",
                                           stock_id=None)
                                           
        edit_bookmarks_action.connect("activate", self.create_edit_bookmarks_dialog)
        
        self.action_group.add_action_with_accel(self.add_bookmark_action, "<Ctrl>D")
        self.action_group.add_action(edit_bookmarks_action)
        
        manager.insert_action_group(self.action_group, -1)
        
        self.ui_id = manager.add_ui_from_string(ui_string)
        self.ui_id2 = manager.new_merge_id()
        
        self.load_bookmarks()
        self.add_bookmarks_to_menu()
        
    def remove_menu_item(self):
        manager = self.window.get_ui_manager()
        
        manager.remove_ui(self.ui_id)
        
    # load_bookmarks reads the bookmarks.txt file and stores all of the Bookmarks
    # in a list sorted by parent folder (if any)
    def load_bookmarks(self):
        path = os.path.expanduser( '~' ) + "/.gnome2/gedit/plugins/"
        
        if (not (os.path.exists(os.path.join(path, 'bookmarks.txt')))):
            self.bookmarks = []
            self.bookmark_folders = []
            self.bookmark_count = 0
            
            return
        
        file = open(os.path.join(path, 'bookmarks.txt'))
        lines = file.readlines()
        file.close()
        
        # Reset all bookmark storing variables
        self.bookmarks = []
        self.bookmark_folders = []
        self.bookmark_count = 0
        
        # Temporary list; we'll read all of the bookmarks and then
        # sort them by Folder afterwards.
        all_bookmarks = []
        
        # First let's load all of the bookmarks into the temporary list (all_bookmarks).
        # We start on the second line to skip the warning at the start of the file.
        for i in range(1, len(lines), 3):
            if (i + 2 < len(lines)):
                bookmark_parent = lines[i].rstrip("\r\n")
                bookmark_name = lines[i + 1].rstrip("\r\n")
                bookmark_path = lines[i + 2].rstrip("\r\n")

                # Append a Bookmark object (it just holds the name, path, and parent).
                all_bookmarks.append(Bookmark(bookmark_name, bookmark_path, bookmark_parent))
                
        # Now we'll go through our temporary list and sort them into their folders
        i = 0
        while (i < len(all_bookmarks)):
            if (all_bookmarks[i].parent == ""):
                # Add it as its own family
                self.bookmarks.append( [all_bookmarks[i]] )
                
            else:
                # We want to go through the rest of the list and get all bookmarks
                # of the same folder.  As we find more, remove them from the list
                # so that we don't process them more than once each.
                
                if (not (all_bookmarks[i].parent in self.bookmark_folders)):
                    self.bookmark_folders.append(all_bookmarks[i].parent)
                
                bookmark_family = [all_bookmarks[i]] # Save all same-parented bookmarks in this list
                
                j = i + 1
                
                while (j < len(all_bookmarks)):
                    if (all_bookmarks[j].parent == all_bookmarks[i].parent):
                        bookmark_family.append(all_bookmarks[j])
                        
                        # Remove the bookmark from the overall list now
                        all_bookmarks.pop(j)
                        
                    else:
                        j += 1
                        
                # Add the Family to the bookmark list
                self.bookmarks.append(bookmark_family)
                        
            i += 1
            
    # add_bookmarks_to_menu goes through the Bookmarks list and
    # adds each family to the Bookmarks menu.  If the members
    # of a family have a parent (folder), then it adds a submenu
    # to the Bookmarks menu along with an "Open All" button.
    def add_bookmarks_to_menu(self):
        manager = self.window.get_ui_manager()
        
        for family in self.bookmarks:
            # We store them by parent (family).  Thus, if the first one has
            # a parent folder, then they all will share that parent folder.
            # If it doesn't, it's alone.
            if (family[0].parent == ""):
                # Only one bookmark in this family.
                bookmark = family[0]
                
                # Store the action name.
                action_name = "bookmark%d" % self.bookmark_count
                
                # Add it to the menu with "ui_id2"; if the user edits their bookmarks,
                # then we'll want to remove all "ui_id2" elements and re-add them to
                # reflect the changes.
                manager.add_ui(merge_id = self.ui_id2,
                               path='/MenuBar/BookmarksMenu/BookmarksOps_2',
                               name=action_name,
                               action=action_name,
                               type=gtk.UI_MANAGER_MENUITEM,
                               top=False)
                               
                # Create an action for the bookmark.
                bookmark_action = gtk.Action(name=action_name,
                                             label=bookmark.name.replace("_", "%95"),
                                             tooltip=bookmark.path,
                                             stock_id=None)
                                             
                # Set the bookmark to load the appropriate file.
                bookmark_action.connect("activate", lambda a,x=bookmark.path: self.open_file(x))
                bookmark_action.set_visible(True) # Make it visible.
                
                # Add the bookmark action.
                self.action_group.add_action(bookmark_action)
                
                # Increase bookmark count.
                self.bookmark_count += 1
                
            else:
                # Start by adding a submenu
                submenu_action_name = "submenu_%s" % family[0].parent.replace(" ", "_")
                
                # Add the submenu to the menu
                manager.add_ui(merge_id = self.ui_id2,
                               path='/MenuBar/BookmarksMenu/BookmarksOps_2',
                               name=submenu_action_name,
                               action=submenu_action_name,
                               type=gtk.UI_MANAGER_MENU,
                               top=False)
                               
                # Define an action for the submenu
                submenu_action = gtk.Action(name=submenu_action_name,
                                            label=family[0].parent,
                                            tooltip=None,
                                            stock_id=None)
                                            
                submenu_action.set_visible(True) # Make it visible
                self.action_group.add_action(submenu_action) # Add the action
                
                # Add an "Open all" option
                open_all_action_name = "open_all_%s" % family[0].parent.replace(" ", "_")
                
                # Add it to the newly-created submenu
                manager.add_ui(merge_id = self.ui_id2,
                               path='/MenuBar/BookmarksMenu/BookmarksOps_2/%s' % submenu_action_name,
                               name=open_all_action_name,
                               action=open_all_action_name,
                               type=gtk.UI_MANAGER_MENUITEM,
                               top=False)
                               
                # Define an action for the "Open all" button
                open_all_action = gtk.Action(name=open_all_action_name,
                                             label="Open all",
                                             tooltip="Open all bookmarks in this folder",
                                             stock_id=None)
                                             
                # Tell the "Open all" button to "open all documents" when the user clicks it
                open_all_action.connect("activate", lambda a,x=family[0].parent: self.open_all_bookmarks_in_folder(x))
                open_all_action.set_visible(True) # Make it visible.
                
                # Add the "open all" action
                self.action_group.add_action(open_all_action)
                
                # Also add a separator.  It doesn't need an action.
                manager.add_ui(merge_id = self.ui_id2,
                               path='/MenuBar/BookmarksMenu/BookmarksOps_2/%s' % submenu_action_name,
                               name="",
                               action="",
                               type=gtk.UI_MANAGER_SEPARATOR,
                               top=False)
                
                # Now, go through each bookmark in this submenu
                for each in family:
                    
                    # Store an action name for the Bookmark
                    action_name = "bookmark%d" % self.bookmark_count
                    
                    # Add it to the submenu we created
                    manager.add_ui(merge_id = self.ui_id2,
                                   path='/MenuBar/BookmarksMenu/BookmarksOps_2/%s' % submenu_action_name,
                                   name=action_name,
                                   action=action_name,
                                   type=gtk.UI_MANAGER_MENUITEM,
                                   top=False)
                                   
                    # Create an action for the Bookmark
                    bookmark_action = gtk.Action(name=action_name,
                                                 label=each.name,
                                                 tooltip=each.path,
                                                 stock_id=None)
                                                 
                    # Tell it to load the file when clicked
                    bookmark_action.connect("activate", lambda a,x=each.path: self.open_file(x))
                    bookmark_action.set_visible(True) # Make it visible
                    
                    # Add the new bookmark action
                    self.action_group.add_action(bookmark_action)
                    
                    # Increase the bookmark count
                    self.bookmark_count += 1

class Bookmarks(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self.instances = {}
        
        # Add an idle function that will monitor all windows for
        # changes made to the bookmarks.  If the user adds or changes
        # a bookmark in one window, we want to reflect that change
        # in all windows.  The plugin helper for that particular
        # window will set "bookmark_change" to True on any change.
        self.idle_id = gobject.timeout_add(100, self.monitor_bookmark_changes)
        
    def activate(self, window):
        self.instances[window] = PluginHelper(self, window)
        
    def deactivate(self, window):
        gobject.source_remove(self.idle_id)
        
        self.instances[window].deactivate()
        
    def update_ui(self, window):
        self.instances[window].update_ui()
        
    def monitor_bookmark_changes(self):
        # Check all windows for bookmark changes.
        for window in self.instances:
            
            # Has any change occurred?
            if (self.instances[window].bookmark_change):
                
                # Set change variable to False
                self.instances[window].bookmark_change = False
                
                # Go through every window (we'll skip the current window) and
                # reset the bookmarks menu.
                for each_other_window in self.instances:
                    
                    # Skip current window
                    if (not (each_other_window == window)):
                        
                        # Remove the bookmarks from the menu
                        self.instances[each_other_window].remove_bookmarks_from_menu()
                        
                        # Reload bookmark data
                        self.instances[each_other_window].load_bookmarks()
                        
                        # Add the bookmarks back to the menu
                        self.instances[each_other_window].add_bookmarks_to_menu()
                        
                # It seems pretty unlikely that two different windows would
                # have changes to bookmarks in the same millisecond.  In the
                # bizarre event that such a thing happens, we'll just have
                # to handle it the next time through.
                return True
                    
        return True
                
                
