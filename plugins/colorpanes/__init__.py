# -*- coding: utf8 -*-
#  Color Panes plugin for Gedit
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
Color Panes plugin package

2010-10-13
Version 2.2.0

Description:
This plugin makes the side and bottom panes match the color scheme
used in the main text area.

Typical location:
~/.gnome2/gedit/plugins     (for one user)
    or
/usr/lib/gedit-2/plugins    (for all users)

Files:
colorpanes.gedit-plugin     -- Gedit reads this to know about the plugin.
colorpanes/                 -- Package directory
    __init__.py             -- Package module loaded by Gedit.
    color_panes.py          -- Plugin and plugin helper classes.
    logger.py               -- Module providing simple logging.
    gpl.txt                 -- GNU General Public License.

"""
from .color_panes import ColorPanesPlugin

