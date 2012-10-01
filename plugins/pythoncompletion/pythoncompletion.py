# -*- coding: utf-8 -*-

# Copyright (C) 2011 Eiichi Sato
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import gedit
import gobject
import gtk
import gtksourceview2 as gsv
from complete import complete

class CompletionProvider(gobject.GObject, gsv.CompletionProvider):
    def __init__(self, name):
        gobject.GObject.__init__(self)
        self.name = name

    def do_match(self, context):
        return context.get_iter().get_buffer().get_mime_type() \
                in ('text/x-python')

    def _get_incomplete_string(self, context, charsallowed='_'):
        insert = context.get_iter()
        buffer = insert.get_buffer()
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if (not char.isalnum()) and (char not in charsallowed):
                start.forward_char()
                break
        return unicode(buffer.get_text(start, insert))

    def do_get_proposals(self, context):
        insert = context.get_iter()
        buffer = insert.get_buffer()

        incomplete = self._get_incomplete_string(context, '_.')
        if (not incomplete) or incomplete.isdigit(): return

        completes = complete(buffer.get_text(*buffer.get_bounds()), incomplete, insert.get_line())
        if not completes: return

        incomplete2 = self._get_incomplete_string(context, '_')

        def sortfunc(a, b):
            if a['abbr'].startswith('_'): return 1
            if b['abbr'].startswith('_'): return -1
            return a['abbr'] > b['abbr']

        def makeitem(item):
            # discard chars after opening parenthesis
            tmp = item['abbr'].split('(')
            if len(tmp) == 1: tmp = tmp[0]
            elif len(tmp) == 2 and tmp[1] == ')': tmp = tmp[0] + '()'
            else: tmp = tmp[0] + '('

            result = gsv.CompletionItem(item['abbr'], tmp)
            result.set_property('info', item['info'])
            return result

        return [makeitem(item) \
                for item in sorted(completes, cmp=sortfunc) \
                if item['abbr'].startswith(incomplete2)]

    def do_populate(self, context):
        proposals = self.do_get_proposals(context)
        context.add_proposals(self, proposals if proposals else [], True)

    def do_get_activation(self):
        return gsv.COMPLETION_ACTIVATION_INTERACTIVE

    def do_get_name(self):
        return self.name

gobject.type_register(CompletionProvider)

class PythonCompletion(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self.window = None
        self.providers = {}

    def on_view_added(self, window, view):
        self.providers[view] = CompletionProvider('Python Completion')
        view.get_completion().add_provider(self.providers[view])
        view.get_completion().set_property('remember-info-visibility', True)

    def on_view_removed(self, window, view):
        view.get_completion().remove_provider(self.providers[view])
        del self.providers[view]

    def on_tab_added(self, window, tab):
        self.on_view_added(self, tab.get_view())

    def on_tab_removed(self, window, tab):
        self.on_view_removed(self, tab.get_view())

    def activate(self, window):
        for view in window.get_views():
            self.on_view_added(window, view)
        self.window = window
        self.on_tab_added_handler_id = window.connect('tab-added', self.on_tab_added)
        self.on_tab_removed_handler_id = window.connect('tab-removed', self.on_tab_removed)

    def deactivate(self, window):
        for view in window.get_views():
            self.on_view_removed(window, view)
        window.disconnect(self.on_tab_added_handler_id)
        window.disconnect(self.on_tab_removed_handler_id)
        self.window = None

    def is_configurable(self):
        return False

