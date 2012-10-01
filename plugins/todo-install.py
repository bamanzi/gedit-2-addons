#!/usr/bin/python
import os
import sys
import re

# get the user name argument
username = sys.argv[1]

# exclude older versions
try:
    print "Trying to remove older versions if exists..."
    os.system('sudo -u '+username+' rm -R ~/.gnome2/gedit/plugins/todo')
    os.system('sudo -u '+username+' rm -R ~/.gnome2/gedit/plugins/todo.gedit-plugin')
    print "done."
except OSError:
    pass

try:
    print "Trying to copy new files..."
    # Create the plugins dir if not exists
    os.system('sudo -u '+username+' mkdir -p ~/.gnome2/gedit/plugins')
    os.system('sudo -u '+username+' mkdir -p ~/.gnome2/gedit/plugins/todo')
    os.system('sudo -u '+username+' cp ./todo/__init__.py ~/.gnome2/gedit/plugins/todo/__init__.py')
    os.system('sudo -u '+username+' cp ./todo/todo.conf ~/.gnome2/gedit/plugins/todo/todo.conf')
    os.system('sudo -u '+username+' cp ./todo/todo.py ~/.gnome2/gedit/plugins/todo/todo.py')
    os.system('sudo -u '+username+' cp ./todo/todo_gears.png ~/.gnome2/gedit/plugins/todo/todo_gears.png')
    os.system('sudo -u '+username+' cp ./todo/todo_header.png ~/.gnome2/gedit/plugins/todo/todo_header.png')
    os.system('sudo -u '+username+' cp ./todo.gedit-plugin ~/.gnome2/gedit/plugins/todo.gedit-plugin')
    print "done."
except OSError:
    print "An error ocurred on trying to install"

try:
    print "Trying to create gedit:// url handlers..."
    print "Copying and configuring handler file..."
    os.system('cp ./todo/gedit_todo_handler /usr/bin/gedit_todo_handler')
    os.system('chmod a+x /usr/bin/gedit_todo_handler')
    print "Running gconftool-2..."
    os.system('sudo -u '+username+' /usr/bin/gconftool-2 -s -t string /desktop/gnome/url-handlers/gedit/command \'/usr/bin/gedit_todo_handler "%s"\'')
    os.system('sudo -u '+username+' /usr/bin/gconftool-2 -s -t bool /desktop/gnome/url-handlers/gedit/enabled true')
    print "done."
except:
    print "Error wile creating URL handler for gedit://. you need to create it manualy. please see README file for instructions"

try:

    # TODO: Look for about:config in firefox and see if these values can be setted there.
    print "Trying to configure mozilla firefox..."

    r = re.compile('// Enable gedit protocols')

    ff_config = open('/etc/firefox-3.0/pref/firefox.js', 'r+a')

    already_configured = False

    for line in ff_config.read().split('\n'):
        if r.search(line):
            already_configured = True
            break

    if not already_configured:
        ff_config.write('\n\n// Enable gedit protocols')
        ff_config.write('\npref("network.protocol-handler.app.gedit", "/usr/bin/gedit_todo_handler");')
        ff_config.write('\npref("network.protocol-handler.warn-external.gedit", false);')
        ff_config.close()
    else:
        print "Firefox sems to be already configured."
    print "done."
except:
    raise
    print "Error while trying to configure mozilla/firefox. maybe it is not \n" \
        "installed or the configurations file stand in another place. see the \n" \
        "README to see how to configure it manually."
