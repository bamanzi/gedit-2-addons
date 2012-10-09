# Copyright (C) 2009-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""Format text and code"""

__all__ = [
    'Formatter',
    ]

import os
import re

try:
    import gconf as GConf
    APP_KEY = "gedit-2"
except:
    import mateconf as GConf
    APP_KEY = "pluma"
import gtk as Gtk
from textwrap import wrap
from gettext import gettext as _

from pocketlint.formatdoctest import DoctestReviewer
from pocketlint.formatcheck import Language, Reporter, UniversalChecker

from gdp import PluginMixin, setup_file_lines_view


class Formatter(PluginMixin):
    """Format Gedit Document and selection text."""

    def __init__(self, window):
        self.window = window
        # The replace in text uses the replace dialog.
        widgets = Gtk.Builder()
        widgets.add_from_file(
            '%s/format.ui' % os.path.dirname(__file__))
        widgets.connect_signals(self.ui_callbacks)
        self.replace_dialog = widgets.get_object('replace_dialog')
        self.replace_label = widgets.get_object('replace_label')
        self.replace_label_text = self.replace_label.get_text()
        self.replace_pattern_entry = widgets.get_object(
            'replace_pattern_entry')
        self.replace_replacement_entry = widgets.get_object(
            'replace_replacement_entry')
        self._bounds = None
        self._text = None
        # Syntax and style reporting use the panel.
        other_widgets = Gtk.Builder()
        other_widgets.add_from_file(
            '%s/format.ui' % os.path.dirname(__file__))
        self.file_lines = other_widgets.get_object(
            'file_lines_scrolledwindow')
        self.file_lines_view = other_widgets.get_object('file_lines_view')
        setup_file_lines_view(self.file_lines_view, self, 'Problems')
        panel = window.get_side_panel()
        icon = Gtk.image_new_from_stock(Gtk.STOCK_INFO, Gtk.ICON_SIZE_MENU)
        panel.add_item(self.file_lines, 'Check syntax and style', icon)

    def deactivate(self):
        """Clean up resources before deactivation."""
        panel = self.window.get_side_panel()
        panel.remove_item(self.file_lines)

    @property
    def ui_callbacks(self):
        """The dict of callbacks for the ui widgets."""
        return {
            'on_replace_quit': self.on_replace_quit,
            'on_replace': self.on_replace,
            }

    def _get_bounded_text(self):
        """Return tuple of the bounds and formattable text.

        The bounds mark either the selection or the document.
        """
        document = self.active_document
        if document.props.has_selection:
            bounds = document.get_selection_bounds()
        else:
            bounds = (document.get_start_iter(), document.get_end_iter())
        text = document.get_text(bounds[0], bounds[1], True)
        return bounds, text

    def _put_bounded_text(self, bounds, text):
        """Replace the current text between the bounds with the new text.

        This change is undoable.
        """
        document = self.active_document
        document.begin_user_action()
        document.place_cursor(bounds[0])
        document.delete(*bounds)
        document.insert_at_cursor(text)
        document.end_user_action()

    def _single_line(self, text):
        """Return the text as a single line.."""
        lines = [line.strip() for line in text.splitlines()]
        return ' '.join(lines)

    def single_line(self, data):
        """Format the text as a single line."""
        bounds, text = self._get_bounded_text()
        text = self._single_line(text)
        self._put_bounded_text(bounds, text)

    def newline_ending(self, data):
        """Fix the selection's line endings."""
        bounds, text = self._get_bounded_text()
        lines = [line.rstrip() for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def tabs_to_spaces(self, data):
        """Fix the selection's line endings."""
        bounds, text = self._get_bounded_text()
        gconf_client = GConf.client_get_default()
        tab_size = gconf_client.get_int(
            '/apps/%s/preferences/editor/tabs/tabs_size' % APP_KEY) or 4
        tab_spaces = ' ' * tab_size
        lines = [line.replace('\t', tab_spaces) for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def quote_lines(self, data):
        """Quote the selected text passage."""
        bounds, text = self._get_bounded_text()
        lines = ['> %s' % line for line in text.splitlines()]
        self._put_bounded_text(bounds, '\n'.join(lines))

    def sort_imports(self, data):
        """Sort python imports."""
        bounds, text = self._get_bounded_text()
        padding = self._get_padding(text)
        line = self._single_line(text)
        imports = line.split(', ')
        imports = sorted(imports, key=str.lower)
        imports = [imp.strip() for imp in imports if imp != '']
        text = self._wrap_text(', '.join(imports), padding=padding)
        self._put_bounded_text(bounds, text)

    def wrap_selection_list(self, data):
        """Wrap long lines and preserve indentation."""
        # This should use the textwrap module.
        paras = []
        indent_re = re.compile('^( +[0-9*-]*\.*)')
        bounds, text = self._get_bounded_text()
        for line in text.splitlines():
            match = indent_re.match(line)
            if match is not None:
                symbol = match.group(1)
                # When there is not symbol in the indent, remove a space
                # because a space is automatically added for the symbol.
                if not symbol.replace(' ', ''):
                    symbol = symbol[0:-1]
            else:
                symbol = ''
            padding_size = len(symbol)
            padding = ' ' * padding_size
            run = 72 - padding_size
            new_lines = []
            new_line = [symbol]
            new_length = padding_size
            # ignore the symbol
            words = line.split()
            for word in words[1:]:
                # The space between the words is 1
                if new_length + 1 + len(word) > run:
                    new_lines.append(' '.join(new_line))
                    new_line = [padding]
                    new_length = padding_size
                new_line.append(word)
                new_length += 1 + len(word)
            new_lines.append(' '.join(new_line))
            paras.extend(new_lines)
        self._put_bounded_text(bounds, '\n'.join(paras))

    def _get_padding(self, text):
        """Return the leading whitespace.

        Return '' if there is not leading whitespace.
        """
        leading_re = re.compile(r'^(\s+)')
        match = leading_re.match(text)
        if match:
            return match.group(1)
        else:
            return ''

    def _wrap_text(self, text, width=78, padding=None):
        """Wrap long lines."""
        if padding is None:
            padding = self._get_padding(text)
        line = self._single_line(text)
        lines = wrap(
            line, width=width, initial_indent=padding,
            subsequent_indent=padding)
        paragraph = '\n'.join(lines)
        return paragraph

    def rewrap_text(self, data):
        """Rewrap the paragraph."""
        bounds, text = self._get_bounded_text()
        text = self._wrap_text(text)
        self._put_bounded_text(bounds, text)

    def reformat_css(self, data):
        """Reformat the CSS."""
        bounds, text = self._get_bounded_text()
        # Break the text into rules using the trailing brace; the last item
        # is not css.
        rules = text.split('}')
        trailing_text = rules.pop().strip()
        css = []
        for rule in rules:
            rule = rule.strip()
            selectors, properties = rule.split('{')
            css.append('%s {' % selectors.strip())
            for prop in properties.split(';'):
                if not prop:
                    # We always check after the last semicolon because it is
                    # a common mistake to forget it on the last property.
                    # This loop fixes the syntax if there is remaining text.
                    break
                prop = ': '.join(
                    [part.strip() for part in prop.split(':')])
                css.append('    %s;' % prop)
            css.append('    }')
        if trailing_text:
            # This could be a comment.
            css.append(trailing_text)
        self._put_bounded_text(bounds, '\n'.join(css))

    def re_replace(self, data):
        """Replace each line using an re pattern."""
        self._bounds, self._text = self._get_bounded_text()
        self.replace_dialog.show()
        self.replace_dialog.run()

    def on_replace_quit(self, widget=None):
        """End the replacement, hide he dialog."""
        self._bounds = None
        self._text = None
        self.replace_dialog.hide()

    def on_replace(self, widget=None):
        """replace each line of text."""
        pattern = self.replace_pattern_entry.get_text()
        replacement = self.replace_replacement_entry.get_text()
        try:
            line_re = re.compile(pattern)
        except re.error:
            # Show a message that the pattern failed.
            message = _("The regular expression pattern has an error in it.")
            self.replace_label.set_markup(
                '%s\n<b>%s</b>' % (self.replace_label_text, message))
            return
        lines = [
            line_re.sub(replacement, line)
            for line in self._text.splitlines()]
        self._put_bounded_text(self._bounds, '\n'.join(lines))
        self.on_replace_quit()

    def show(self, data):
        """Show the finder pane."""
        panel = self.window.get_side_panel()
        panel.activate_item(self.file_lines)
        panel.props.visible = True

    def reformat_doctest(self, data):
        """Reformat the doctest."""
        bounds, text = self._get_bounded_text()
        file_name = self.active_document.get_uri_for_display()
        reviewer = DoctestReviewer(text, file_name)
        new_text = reviewer.format()
        self._put_bounded_text(bounds, new_text)

    def _check_style(self, document):
        """Check the style and syntax of a document."""
        file_path = document.get_uri_for_display()
        start_iter = document.get_start_iter()
        end_iter = document.get_end_iter()
        text = document.get_text(start_iter, end_iter, True)
        reporter = Reporter(
            Reporter.FILE_LINES, treeview=self.file_lines_view)
        language = Language.get_language(file_path)
        checker = UniversalChecker(
            file_path, text=text, language=language, reporter=reporter)
        checker.check()

    def check_style(self, data, documents=None, quiet=False):
        """Check the style and syntax of the active document."""
        self.file_lines_view.get_model().clear()
        if documents is None:
            documents = [self.active_document]
        for document in documents:
            self._check_style(document)
        model = self.file_lines_view.get_model()
        first = model.get_iter_first()
        if first is None:
            model.append(
                None, ('No problems found', 'emblem-default', 0, None, None))
        if first is None and quiet:
            # Do not interupt the user to say there is nothing to see.
            return
        self.file_lines_view.expand_all()
        self.show(None)

    def check_all_style(self, data):
        """Check the style and syntax of all open documents."""
        self.check_style(None, documents=self.window.get_documents())
