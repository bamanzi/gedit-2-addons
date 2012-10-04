#    builder output capture and display
#    Copyright (C) 2009 Mike Reed <gedit@amadron.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import subprocess
import signal
import re
import gobject
import pango
import logging
import sys
import os.path

import gtk
try:
    import gedit
except:
    import pluma as gedit


class Output(object):
    _severities = {'error':'#DF2424',
                   'info':'#4242CD',
                   'warning':'#F5A20C',
                   'note': '#4242CD',
                   'default':'#4242CD'}

    def __init__(self, config):
        self._l = logging.getLogger('plugin.builder')
        self._l.debug('Entered')

        ui_builder = gtk.Builder()
        ui_builder.add_from_file(os.path.join(config.get_data_dir(), 'Output.glade'))
        ui_builder.connect_signals({
            'button_stop_clicked_cb': self._button_stop_clicked_cb,
            'button_next_clicked_cb': self._button_next_clicked_cb,
            'button_prev_clicked_cb': self._button_prev_clicked_cb
        })
        self._ui = ui_builder.get_object
        
        self._view = self._ui('view')
        self._view.modify_font(pango.FontDescription('Monospace'))
        self._view.connect('event', self._view_event)
        buffer = self._view.get_buffer()
        self._mark = buffer.create_mark('output', buffer.get_end_iter(), True)
        for (sev, color) in self._severities.iteritems():
            tag = buffer.create_tag(sev, foreground=color)
            tag.connect('event', self._tag_event)            
        buffer.create_tag('dir_enter', foreground='#285428')
        buffer.create_tag('dir_leave', foreground='#285428')
        buffer.create_tag('subproc', foreground='#b0b0b0')
        buffer.create_tag('line_highlight', background='#EFEBE7')

        # The regex to find items of interest in the ouput
        # It should have the following named subexpressions
        #   file - the file
        #   line - the line number within file
        #   col  - the column number on the line
        #   sev  - the severity of the item
        self._file_num_re = re.compile(
            r"(?P<file>[^: ]+?)"
             "(:|\()"
             "((?P<line>\d+)|(\([][<>() :,+a-zA-Z0-9_.]+\)))"
             "(\)?:|,)"
             "((?P<col>\d+):)?"
             "(\s*(?P<sev>[a-z]+):)?")
        self._dir_enter_re = re.compile(
            r"make\[\d+\]: Entering directory [`'](?P<dir>[^']+)'$")
        self._dir_leave_re = re.compile(
            r"make\[\d+\]: Leaving directory [`'](?P<dir>[^']+)'$")
        self._item_line = []  # o/p buffer line no for nth item.
        self._current_item_no = -1 # index into _item_line of currently selected item.
        self._prevdirs = [] # Stack of directories entered by "make"
        self._sub = None  # Points to a subprocess.Popen class of the running command
        self._item_selected_cb = None;
        self._item_found_cb = None;
        self._set_button_sensitivity()

    def widget(self):
        return self._ui('output')

    def set_item_selected_cb(self, cb):
        """Call 'cb' passing 'item no' when items are selected."""
        self._l.debug('Entered')
        self._item_selected_cb = cb

    def set_item_found_cb(self, cb):
        """Call 'cb' passing 'item no', 'path', 'line', 'column' when items are found."""
        self._l.debug('Entered')
        self._item_found_cb = cb

    def execute(self, cmd):
        self._l.info('execute [%s]' % cmd)
        self._item_line = []
        self._current_item_no = -1
        self._prevdirs = []
        self._cwd = os.path.abspath('.')
        buffer = self._view.get_buffer()
        buffer.set_text('')
        buffer.insert_with_tags_by_name(
            buffer.get_end_iter(),
            "Executing '%s' in '%s'\n\n" % (cmd, self._cwd),
            'subproc')
        self._sub = subprocess.Popen(
            cmd,
            1,       # 0=unbuffered, 1=line buffered, n=buffer size
            None,    # executable
            None,    # stdin
            subprocess.PIPE,    # stdout
            subprocess.STDOUT,  # stderr > stdout
            None,    # preexec cb
            True,    # close fds
            True,    # use shell
            None,    # cwd
            None,    # env
            True,    # \n, \r and \r\n => \n
            )
        self._source_id = gobject.io_add_watch(
            self._sub.stdout,
            gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
            self._append)
        self._set_button_sensitivity()
        
    def _append(self, source, condition):
        self._l.debug('Entered')
        retval = True
        buffer = self._view.get_buffer()
        line = self._sub.stdout.readline();
        if len(line) == 0:
            self._finish_sub()
            retval = False
        else:
            self._l.info('read [%s]' % line.rstrip())
            result = self._file_num_re.search(line)
            if result:
                self._l.debug('_file_num_re matched')
                (f, l, c, s) = result.group('file', 'line', 'col', 'sev')
                self._l.info('Matched (%r, %r, %r, %r)' % (f, l, c, s))
                if l:
                    file_line_no = int(l)
                else:
                    file_line_no = 1
                if c:
                    file_col_no = int(c)
                else:
                    file_col_no = 1
                start = result.start(0)
                end = result.end(0)
                buff_line_no = buffer.get_line_count() - 1
                fullpath = os.path.normpath(os.path.join(self._cwd, f))
                if self._item_found_cb:
                    self._item_found_cb(len(self._item_line), fullpath, file_line_no, file_col_no)
                self._item_line.append(buff_line_no)
                self._l.info('added item[%d]=(%s, %d:%d)' % (
                                buff_line_no, fullpath,
                                file_line_no, file_col_no))
                buffer.insert(buffer.get_end_iter(), line[:start])
                if s is None or s not in self._severities.keys():
                    s = 'default'
                buffer.insert_with_tags_by_name(
                    buffer.get_end_iter(), line[start:end], s)
                buffer.insert(buffer.get_end_iter(), line[end:])
            else:
                result = self._dir_enter_re.search(line)
                if result:
                    self._prevdirs.append(self._cwd)
                    self._cwd = os.path.normpath(os.path.join(
                        self._cwd, result.group('dir')))
                    self._l.info('cwd=[%s]' % self._cwd)
                    buffer.insert_with_tags_by_name(
                        buffer.get_end_iter(), line, 'dir_enter')
                else:
                    result = self._dir_leave_re.search(line)
                    if result:
                        prevdir = self._prevdirs.pop()
                        olddir = os.path.normpath(
                            os.path.join(prevdir, result.group('dir')))
                        if olddir != self._cwd:
                            self._l.error(
                                "Eeek! we are in '%s' but leaving '%s'" %
                                (self._cwd, olddir))
                        self._cwd = prevdir
                        self._l.info('cwd=[%s]' % self._cwd)
                        buffer.insert_with_tags_by_name(
                            buffer.get_end_iter(), line, 'dir_leave')
                    else:
                        buffer.insert(buffer.get_end_iter(), line)
                
        # Keep the buffer scrolled to the latest output
        buffer.move_mark(self._mark, buffer.get_end_iter())
        self._view.scroll_to_mark(self._mark, 0.0)
        return retval

    def _finish_sub(self):
        self._l.debug('Entered')
        self._sub.wait()
        self._l.info('Subprocess finished')
        buffer = self._view.get_buffer()
        buffer.insert_with_tags_by_name(
            buffer.get_end_iter(),
            '\n\nProcess finished returning %r' % self._sub.returncode,
            'subproc')
        buffer.move_mark(self._mark, buffer.get_end_iter())
        self._view.scroll_to_mark(self._mark, 0.0)
        self._sub = None
        self._set_button_sensitivity()

    def _kill_children(self):
        rel=[]
        # Get all PIDs and parents
        for thisdir in os.listdir('/proc'):
            statfile = os.path.join('/proc', thisdir, 'stat')
            if thisdir.isdigit() and os.path.isfile(statfile):
                f = open(statfile)
                data = f.readline().split()
                rel.append((int(data[3]), int(thisdir)))
                
        def find_and_kill(pid):
            for x in filter(lambda x: x[0] == pid, rel):
                find_and_kill(x[1])
            # Remember, we are killing from the bottom up.  Sometime
            # killing a child results in the parent terminating, so
            # ignore any non-existent PID errors.
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            
        find_and_kill(self._sub.pid)

    def _button_stop_clicked_cb(self, arg1):
        self._l.debug('Entered')
        if self._sub is None:
            return True
            
        gobject.source_remove(self._source_id)

        # This is a bit tricky because the subprocess is the shell and killing
        # it will possibly just orphan anything it is running.  Not
        # sure what robust method I can use here that is platform independent.
        if sys.platform == 'linux2':
            self._kill_children()
        else:
            self._l.info('SIGHUP')
            self._sub.send_signal(signal.SIGHUP)
            if self._sub.poll() is None:
                self._l.info('SIGINT')
                self._sub.terminate()
                if self._sub.poll() is None:
                    self._l.info('SIGKILL')
                    self._sub.kill()
                    self._sub.poll()
                    
        self._finish_sub()
        return True

    def _change_current_item_no(self, new_item_no):
        buffer = self._view.get_buffer()
        if self._current_item_no != -1:
            line = self._item_line[self._current_item_no]
            start_iter = buffer.get_iter_at_line(line)
            end_iter = buffer.get_iter_at_line(line+1)
            buffer.remove_tag_by_name('line_highlight', start_iter, end_iter)
        self._current_item_no = new_item_no
        line = self._item_line[self._current_item_no]
        start_iter = buffer.get_iter_at_line(line)
        end_iter = buffer.get_iter_at_line(line+1)
        buffer.apply_tag_by_name('line_highlight', start_iter, end_iter)

    def _scroll_to_current_item_no(self):
        buffer = self._view.get_buffer()
        line = self._item_line[self._current_item_no]
        buffer.move_mark(self._mark, buffer.get_iter_at_line(line))
        self._view.scroll_to_mark(self._mark, 0.0, True)
        self._set_button_sensitivity()

    def _button_next_clicked_cb(self, arg1):
        self._l.debug('Entered')
        self._change_current_item_no(self._current_item_no + 1)
        self._scroll_to_current_item_no()

    def _button_prev_clicked_cb(self, arg1):
        self._l.debug('Entered')
        self._change_current_item_no(self._current_item_no - 1)
        self._scroll_to_current_item_no()

    def _view_event(self, widget, event):
        if event.type == gtk.gdk.MOTION_NOTIFY:
            event.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
        elif event.type == gtk.gdk.BUTTON_PRESS or \
          event.type == gtk.gdk.ENTER_NOTIFY:
             self._tag_press_coord = (-1, -1)

    def _tag_event(self, tag, widget, event, iter):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            self._tag_press_coord = (event.x, event.y)
        elif event.type == gtk.gdk.BUTTON_RELEASE and event.button == 1 and \
          abs(event.x - self._tag_press_coord[0]) < 2 and \
          abs(event.y - self._tag_press_coord[1]) < 2:
            buff_line = iter.get_line()
            self._change_current_item_no(self._item_line.index(buff_line))
            self._set_button_sensitivity()
            if self._item_selected_cb:
                self._item_selected_cb(self._current_item_no)
        elif event.type == gtk.gdk.MOTION_NOTIFY:
            event.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))            
        
    def _set_button_sensitivity(self):
        items_found = len(self._item_line)
        self._ui('button_stop').set_sensitive(self._sub is not None)
        self._ui('button_prev').set_sensitive(
            self._sub is None and items_found and self._current_item_no > 0)
        self._ui('button_next').set_sensitive(
            self._sub is None and items_found and self._current_item_no < items_found-1)
                
            
