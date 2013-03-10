try:
    import gedit
except:
    import pluma as gedit
    
__version__ = "1"

import tokenize
import os
import sys
import gtk

verbose = 0
recurse = 0
dryrun  = 0


def _rstrip(line, JUNK='\n \t'):
    """Return line stripped of trailing spaces, tabs, newlines.

    Note that line.rstrip() instead also strips sundry control characters,
    but at least one known Emacs user expects to keep junk like that, not
    mentioning Barry by name or anything <wink>.
    """

    i = len(line)
    while i > 0 and line[i-1] in JUNK:
        i -= 1
    return line[:i]

class Reindenter:

    def __init__(self, text):
        self.find_stmt = 1  # next token begins a fresh stmt?
        self.level = 0      # current indent level

        # Raw file lines.
        self.raw = text

        # File lines, rstripped & tab-expanded.  Dummy at start is so
        # that we can use tokenize's 1-based line numbering easily.
        # Note that a line is all-blank iff it's "\n".
        self.lines = [_rstrip(line).expandtabs() + "\n"
                      for line in self.raw]
        self.lines.insert(0, None)
        self.index = 1  # index into self.lines of next line

        # List of (lineno, indentlevel) pairs, one for each stmt and
        # comment line.  indentlevel is -1 for comment lines, as a
        # signal that tokenize doesn't know what to do about them;
        # indeed, they're our headache!
        self.stats = []

    def run(self):
        tokenize.tokenize(self.getline, self.tokeneater)
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == "\n":
            lines.pop()
        # Sentinel.
        stats = self.stats
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = self.after = []
        # Copy over initial empty lines -- there's nothing to do until
        # we see a line with *something* on it.
        i = stats[0][0]
        after.extend(lines[1:i])
        for i in range(len(stats)-1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i+1][0]
            have = getlspace(lines[thisstmt])
            want = thislevel * 4
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line.  If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in xrange(i+1, len(stats)-1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == getlspace(lines[jline]):
                                    want = jlevel * 4
                                break
                    if want < 0:           # Maybe it's a hanging
                                           # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in xrange(i-1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = have + getlspace(after[jline-1]) - \
                                       getlspace(lines[jline])
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for line in lines[thisstmt:nextstmt]:
                    if diff > 0:
                        if line == "\n":
                            after.append(line)
                        else:
                            after.append(" " * diff + line)
                    else:
                        remove = min(getlspace(line), -diff)
                        after.append(line[remove:])
        return self.raw != self.after


    # Line-getter for tokenize.
    def getline(self):
        if self.index >= len(self.lines):
            line = ""
        else:
            line = self.lines[self.index]
            self.index += 1
        return line

    # Line-eater for tokenize.
    def tokeneater(self, type, token, (sline, scol), end, line,
                   INDENT=tokenize.INDENT,
                   DEDENT=tokenize.DEDENT,
                   NEWLINE=tokenize.NEWLINE,
                   COMMENT=tokenize.COMMENT,
                   NL=tokenize.NL):

        if type == NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            self.find_stmt = 1

        elif type == INDENT:
            self.find_stmt = 1
            self.level += 1

        elif type == DEDENT:
            self.find_stmt = 1
            self.level -= 1

        elif type == COMMENT:
            if self.find_stmt:
                self.stats.append((sline, -1))
                # but we're still looking for a new stmt, so leave
                # find_stmt alone

        elif type == NL:
            pass

        elif self.find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            self.find_stmt = 0
            if line:   # not endmarker
                self.stats.append((sline, self.level))

# Count number of leading blanks.
def getlspace(line):
    i, n = 0, len(line)
    while i < n and line[i] == " ":
        i += 1
    return i

class ReindentPython(gedit.Plugin):
        def __init__(self):
            gedit.Plugin.__init__(self)

        def activate(self, window):
            actions = [
                    ("Reindent", None, "Reindent code", None,"Reindent code following PEP008 Guideline", self.reindent)] 
            windowdata = dict()
            window.set_data("ReindentPluginWindowDataKey", windowdata)
            windowdata["reindent_action_group"] = gtk.ActionGroup("GeditReindentPluginActions")
            windowdata["reindent_action_group"].add_actions(actions, window)
            manager = window.get_ui_manager()
            manager.insert_action_group(windowdata["reindent_action_group"], -1)
            windowdata["ui_id"] = manager.new_merge_id ()
            
            action = gtk.ActionGroup("PythonPluginActions")
            manager = window.get_ui_manager()
            manager.insert_action_group(action, -1)
            submenu = """
                <ui>
                  <menubar name='MenuBar'>
                    <menu name='PythonMenu' action='Python'>
                      <placeholder name='ToolsOps_2'>
                        <menuitem action='Reindent'/>
                    <separator/>
                  </placeholder>
                </menu>
              </menubar>
            </ui>"""
            manager.add_ui_from_string(submenu)


        def deactivate(self, window):
            windowdata = window.get_data("ReindentPluginWindowDataKey")
            manager = window.get_ui_manager()
            manager.remove_ui(windowdata["ui_id"])
            manager.remove_action_group(windowdata["reindent_action_group"])

        def update_ui(self, window):
            view = window.get_active_view()
            windowdata = window.get_data("ReindentPluginWindowDataKey") 
            windowdata["reindent_action_group"].set_sensitive(bool(view and view.get_editable()))
        
        def reindent(self, widget, window):
            doc = window.get_active_document()
            bounds = doc.get_bounds()
            text = doc.get_text(*bounds)
            text_array = text.split("\n")
            r = Reindenter(text_array)
            r.run()
            text = ""
            for i in r.after:
                text += i   
            doc.set_text(text)
