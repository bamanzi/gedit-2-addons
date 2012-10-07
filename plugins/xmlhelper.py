# -*- coding: utf8 -*-
# XML Helper for GEdit
# 
# Copyright (c) 2007 Matej Cepl <matej@ceplovi.cz>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import gedit
import gtk
import re,sys

end_tag_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="EditMenu" action="Edit">
			<placeholder name="EditOps_6">
				<menuitem name="LastTag" action="LastTag"/>
				<menuitem name="EndTag" action="EndTag"/>
			</placeholder>
		</menu>
	</menubar>
</ui>
"""

debug = False

def prDebug(string):
	if debug:
		print >>sys.stderr,string

class Endness:
	end = 0
	start = 1
	single = 2

class XMLHelper(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
		
	def __get_tag(self,iter):
		if not(iter.forward_char()):
			raise RuntimeError, "we are in trouble"
		searchRet=iter.forward_search(">",gtk.TEXT_SEARCH_TEXT_ONLY)
		if searchRet:
			begEnd,endEnd=searchRet
			retStr = iter.get_text(begEnd)
			if (retStr[-1]=="/") or (retStr[:3]=="!--"):
				hasEndTag = Endness.single
				retStr = retStr.rstrip("/")
			elif  retStr[0] == "/":
				hasEndTag = Endness.end
				retStr = retStr.lstrip("/")
			else:
				hasEndTag = Endness.start
			# cut element's parameters
			retStr = retStr.split()[0]
			prDebug("tag found is %s and the value of hasEndTag is %s" % (retStr,hasEndTag))
			return retStr,hasEndTag
		else:
			raise IOError, "Never ending tag at line %d" % (iter.get_line()+1)

	def findLastEndableTag(self,position):
		tagStack = []
		res = position.backward_search("<", gtk.TEXT_SEARCH_TEXT_ONLY)
		while res:
			start_match,end_match=res
			tag,isEndTag=self.__get_tag(start_match)
			if isEndTag==Endness.end:
				tagStack.append(tag)
				prDebug("Push tag '%s'" % tag)
			elif isEndTag==Endness.single:
				prDebug("Ignoring single tag '%s'" % tag)
			elif len(tagStack) != 0: # stack not empty
				poppedTag=tagStack.pop()
				prDebug("Popped tag '%s'" % poppedTag)
				if poppedTag != tag:
					raise IOError,"mismatching tags.\nFound %s and expecting %s." % \
						(tag,poppedTag)
			else: # stack is empty and this is not end tag == we found it
				prDebug("We found tag '%s'" % tag)
				return tag
			start_match.backward_char()
			res = start_match.backward_search("<",gtk.TEXT_SEARCH_TEXT_ONLY)

		# not totally sure what following means, but doesn't look right to me
		if len(tagStack) != 0:
			raise IOError, "whatever"
		if not(res): # There is no open tag in the current buffer
			return None

	def end_tag(self, action, window):
		buffer = window.get_active_view().get_buffer()
		inp_mark=buffer.get_iter_at_mark(buffer.get_insert())
		tagname=self.findLastEndableTag(inp_mark)
		if tagname:
			buffer.insert(inp_mark,'</%s>' % tagname)

	def previous_tag(self,action,window):
		buffer = window.get_active_view().get_buffer()
		inp_mark = buffer.get_iter_at_mark(buffer.get_insert())
		res = inp_mark.backward_search("<", gtk.TEXT_SEARCH_TEXT_ONLY)
		if res:
			start_match,end_match = res
			tag,isEndTag = self.__get_tag(start_match)
			if isEndTag == Endness.end:
				buffer.insert(inp_mark,'<%s>' % tag)

	def activate(self, window):
		actions = [
			('EndTag', None, 'End Tag', '<Ctrl>e', "Close the last currently opened XML tag", self.end_tag),
			('LastTag', None, 'Repeat XML Tag', '<Ctrl>m', "Repeat last XML tag", self.previous_tag),
		]

		# store per window data in the window object
		windowdata = dict()
		window.set_data("XMLHelperWindowDataKey", windowdata)
		windowdata["action_group"] = gtk.ActionGroup("GeditXMLHelperActions")
		windowdata["action_group"].add_actions(actions, window)
		manager = window.get_ui_manager()
		manager.insert_action_group(windowdata["action_group"], -1)
		windowdata["ui_id"] = manager.add_ui_from_string(end_tag_str)
		
		window.set_data("XMLHelperInfo", windowdata)

	def deactivate(self, window):
		windowdata = window.get_data("XMLHelperWindowDataKey")
		manager = window.get_ui_manager()
		manager.remove_ui(windowdata["ui_id"])
		manager.remove_action_group(windowdata["action_group"])

	def update_ui(self, window):
		view = window.get_active_view()
		windowdata = window.get_data("XMLHelperWindowDataKey")
		windowdata["action_group"].set_sensitive(bool(view and view.get_editable()))
