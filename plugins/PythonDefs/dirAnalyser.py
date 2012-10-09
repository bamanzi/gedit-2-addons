#!/usr/bin/env python
#-*- coding:utf-8 -*-
#

import gio
import os


SOURCE_EXTS = (".py", ".c", ".h", ".cpp")


def is_source_file(path):
    ext = os.path.splitext( path )[1].lower()
    return ext in SOURCE_EXTS

    
def is_source_dir(path):
    for arq in os.listdir(path):
        if is_source_file( arq ):
            return True
    return False
    

def find_path_to_root(path):
    root_path = []
    parent = path
    while True:
        if not is_source_dir(parent):
            break
        root_path.append( parent )
        path = parent
        parent = os.path.join( os.path.abspath( os.path.join(path, "..") ) )
    root_path.reverse()
    return root_path
         
    
def find_path_to_root_of_gedit_document(doc):
    full_filename = doc.get_uri()        
    if full_filename == None or full_filename == "":
        return None
    
    full_filename = gio.File( full_filename ).get_path()
    if not is_source_file( full_filename ):
        return None
    
    path = os.path.dirname( full_filename )
    if not is_source_dir( path ):
        return None
    
    return find_path_to_root( path )



def dir_files(path):
    arqs = []
    for arq in os.listdir(path):
        full_arq = os.path.join(path, arq)
        if  (os.path.isdir(full_arq) and is_source_dir(full_arq)) or \
            is_source_file(full_arq):
                arqs.append( arq )
    
    arqs.sort()
    return arqs

