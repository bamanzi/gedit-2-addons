# -*- coding: utf8 -*-
#  Highlight Text plugin for gedit
#
#  Copyright (C) 2010 Derek Veit
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Highlight Text plugin package

2010-01-30
Version 1.0.0

Description:
This plugin allows you to highlight all instances of the the selected text in a
document as if you had used it in the Find dialog but by just pressing a hot
key.

This duplicates the function of Incremental Search but without the text box.

Typical location:
~/.gnome2/gedit/plugins     (for one user)
    or
/usr/lib/gedit-2/plugins    (for all users)

Files:
highlighttext.gedit-plugin    -- gedit reads this to know about the plugin.
highlighttext/                -- Package directory
    __init__.py               -- Package module loaded by gedit.
    highlight_text.py         -- Plugin and plugin helper classes.
    logger.py                 -- Module providing simple logging.
    gpl.txt                   -- GNU General Public License.

How it loads:
1. gedit finds highlighttext.gedit-plugin in its plugins directory.
2. That file tells gedit to use Python to load the highlighttext module.
3. Python identifies the highlighttext directory as the highlighttext module.
4. Python loads __init__.py (this file) from the highlighttext directory.
5. This file imports the HighlightTextPlugin class from highlight_text.py.
6. gedit identifies HighlightTextPlugin as the gedit.Plugin object.
7. gedit calls methods of HighlightTextPlugin.

"""
from .highlight_text import HighlightTextPlugin

