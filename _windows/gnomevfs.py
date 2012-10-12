
import os
import urllib

def get_local_path_from_uri(uri):
    if uri.startswith("file://"):
        if os.name=='nt':
            uri = uri[len("file:///"):]
        else:
            uri = uri[len("file://"):]
    return urllib.unquote(uri)


#FIXME: gedit.Document.get_uri_for_display()
def get_uri_from_local_path(path):
    if os.name=='nt':
        path=path.replace('\\', '/')
        return "file:///" + urllib.quote(path, '/:')
    else:
        return "file://" + urllib.quote(path)


if __name__=='__main__':
    uri1 = 'file:///C:/Windows.old/Documents%20and%20Settings/Administrator/Application%20Data/gedit/plugins/gdp/__init__.py'
    path1 = 'C:/Windows.old/Documents and Settings/Administrator/Application Data/gedit/plugins/gdp/__init__.py'
    assert get_local_path_from_uri(uri1)==path1
    assert get_uri_from_local_path(path1)==uri1
    
    path2 = r'C:\Windows.old\Documents and Settings\Administrator\Application Data\gedit\plugins\gdp\__init__.py'
    assert get_uri_from_local_path(path2)==uri1
    
    assert os.path.exists("c:/windows")
    assert os.path.exists(r"c:\windows")
    
    
    try:
        import gedit

        #OK:    
        window.create_tab_from_uri('file:///C:/windows/win.ini', None, 1, False, True)
        
        #Exception
        window.create_tab_from_uri('file://C:/windows/win.ini', None, 1, False, True)
    #Run the following on gedit's Python Console: 
    #On Windows: gedit.Window.create_tab_from_uri
    except:
        print "Run the following on gedit's Python Console"
    
