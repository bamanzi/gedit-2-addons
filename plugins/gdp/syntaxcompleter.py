# Copyright (C) 2007-2011 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the GNU General Public License version 2
# (see the file COPYING).
"""A syntax completer for document words and python symbols."""


__metaclass__ = type

__all__ = [
    'BaseSyntaxGenerator',
    'MarkupGenerator',
    'PythonSyntaxGenerator',
    'SyntaxController',
    'TextGenerator',
    ]


import re
from gettext import gettext as _
from keyword import kwlist
from pydoc import TextDoc
from xml.sax import saxutils

import gobject as GObject
import gtk as Gtk
import gtksourceview2 as GtkSource

from gdp import PluginMixin


lang_manager = GtkSource.language_manager_get_default()
doctest_language = lang_manager.get_language('doctest')

doctest_pattern = re.compile(
    r'^.*(doc|test|stories).*/.*\.(txt|doctest)$')


def get_word(document, word_pattern, end=None):
    """Return a 3-tuple of the word fragment before the cursor.

    The tuple contains the (word_fragment, start_iter, end_iter) to
    identify the prefix and its starting and end position in the
    document.
    """
    if end is None:
        end = document.get_iter_at_mark(document.get_insert())
    start = end.copy()
    word = None

    # When the preceding character is not alphanumeric,
    # there is be no word before the cursor.
    start_char = start.copy()
    if start_char.backward_char():
        char = start_char.get_char()
        if not word_pattern.match(char):
            return (None, start, end)

    # GtkTextIter *_word_end() methods do not seek for '_' and '-', so
    # we need to walk backwards through the iter to locate the word end.
    count = 0
    peek = start.copy()
    while peek.backward_chars(1):
        if not word_pattern.match(peek.get_char()):
            break
        else:
            count += 1

    if count > 0:
        start.backward_chars(count)
        word = document.get_text(start, end, True)
    else:
        word = None

    return (word, start, end)


class DynamicProposal(GObject.GObject, GtkSource.CompletionProposal):
    """A common CompletionProposal for dymamically generated info.

    XXX sinzui 2010-03-14: do_changed, do_equal, do_get_icon, do_get_label,
    do_hash may need implementation.
    """
    __gtype_name__ = "GDPDynamicProposal"

    def __init__(self, word, info=None):
        GObject.GObject.__init__(self)
        self._word = word
        self._info = info or ''

    def __repr__(self):
        return '<%s word="%s" at 0x%x>' % (
            self.__class__.__name__, self._word, id(self))

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return other._word == self._word and other._info == self._info

    def __lt__(self, other):
        return self._word < other._word

    def __hash__(self):
        return hash((type(self), self._word, self._info))

    def equal(self, other):
        return self.__eq__(other)

    def hash(self):
        return self.__hash__()

    def do_get_text(self):
        """See `CompletionProvider`."""
        return self._word

    def do_get_markup(self):
        """See `CompletionProvider`."""
        return saxutils.escape(self._word)

    def do_get_info(self):
        """See `CompletionProvider`."""
        return self._info


class PangoDoc(TextDoc):

    def bold(self, text):
        return '\x86%s\x87' % text

    def document(self, mod, *args):
        text = TextDoc.document(self, mod)
        text = saxutils.escape(text)
        text = text.replace('\x86', '<b>')
        text = text.replace('\x87', '</b>')
        return text


class PythonProposal(DynamicProposal):
    """A proposal that provides pydoc info."""

    def do_get_info(self):
        """See `CompletionProvider`."""
        if self._info is None:
            return None
        return PangoDoc().document(self._info)


class DynamicProvider(GObject.GObject, GtkSource.CompletionProvider):
    """A common CompletionProvider for dynamically generated info."""
    __gtype_name__ = "GDPDynamicProvider"
    word_char = re.compile(r'[\w_-]', re.I)

    def __init__(self, name, language_id, handler, document):
        GObject.GObject.__init__(self)
        self.name = name
        self.proposals = []
        self.language_id = language_id
        self.handler = handler
        self.document = document
        self.info_widget = None
        self.mark = None
        theme = Gtk.icon_theme_get_default()
        w, h = Gtk.icon_size_lookup(Gtk.ICON_SIZE_MENU)
        self.icon = theme.load_icon(Gtk.STOCK_JUSTIFY_LEFT, w, 0)

    def mark_position(self, it):
        """Create or move the mark of the word start."""
        if not self.mark:
            self.mark = it.get_buffer().create_mark(None, it, False)
        else:
            self.mark.get_buffer().move_mark(self.mark, it)

    def get_word(self, context):
        """See `CompletionProvider`."""
        it = context.get_iter()
        word, start, end = get_word(self.document, self.word_char, it)
        if word is not None:
            self.mark_position(start)
        return word

    def do_get_start_iter(self, context, proposal):
        """See `CompletionProvider`."""
        if not self.mark or self.mark.get_deleted():
            return None
        return self.mark.get_buffer().get_iter_at_mark(self.mark)

    def do_match(self, context):
        """See `CompletionProvider`."""
        return True

    def get_generator(self, document, prefix):
        """Return the specialized generator for document's language."""
        if self.language_id == 'python':
            return PythonSyntaxGenerator(document, prefix=prefix)
        if self.language_id in (
            'xml', 'xslt', 'html', 'pt', 'mallard', 'docbook'):
            return MarkupGenerator(document, prefix=prefix)
        else:
            # The text generator is never returned because get_proposals will
            # use it in non-authoritative cases.
            return None

    def get_proposals(self, prefix):
        """See `CompletionProvider`."""
        all_words = []
        is_authoritative = False
        generator = self.get_generator(self.document, prefix)
        if generator:
            is_authoritative, words = generator.get_words()
            all_words += words
        if not is_authoritative:
            is_authoritative, simple_words = TextGenerator(
                self.document, prefix=prefix).get_words()
            all_words += simple_words
        return all_words

    def do_populate(self, context):
        """See `CompletionProvider`."""
        proposals = self.get_proposals(self.get_word(context))
        context.add_proposals(self, proposals, True)

    def do_get_name(self):
        """See `CompletionProvider`."""
        return self.name

    def do_activate_proposal(self, proposal, piter):
        """See `CompletionProvider`."""
        return self.handler(proposal, piter)

    def do_get_icon(self):
        """See `CompletionProvider`."""
        return self.icon

    def do_get_activation(self):
        """See `CompletionProvider`."""
        return GtkSource.COMPLETION_ACTIVATION_USER_REQUESTED

    def do_get_info_widget(self, proposal):
        """See `DynamicProvider`."""
        if self.info_widget is None:
            self.info_view = Gtk.Label('')
            self.info_view.set_alignment(0.0, 0.0)
            self.info_widget = Gtk.ScrolledWindow()
            self.info_widget.add_with_viewport(self.info_view)
        return self.info_widget

    def do_update_info(self, proposal, info):
        """See `CompletionProvider`."""
        markup = proposal.get_info() or ''
        self.info_view.set_markup(markup)
        self.info_view.show()
        self.info_widget.set_size_request(400, -1)
        info.set_sizing(400, -1, False, False)
        info.process_resize()

GObject.type_register(DynamicProposal)
GObject.type_register(DynamicProvider)


class BaseSyntaxGenerator:
    """An abstract class representing the source of a word prefix."""

    def __init__(self, document, prefix=None):
        """Create a new SyntaxGenerator.

        :param prefix: A `str`. The word prefix used to match words.
        :param document: `gedit.Document`. The source of words to search.
        """
        self._prefix = prefix
        self._document = document

    word_char = re.compile(r'[\w_]', re.I)

    @property
    def string_before_cursor(self):
        """Return the string that matches `word_char` before the cursor."""
        text, start_iter, end_iter = get_word(self._document, self.word_char)
        if text is None:
            text = ''
        return text

    def ensure_prefix(self, prefix):
        """Return the available prefix or an empty string."""
        if prefix:
            return prefix
        elif self._prefix:
            return self._prefix
        else:
            # Match all words in the text.
            return ''

    def get_words(self, prefix=None):
        """Return a 2-tuple of is_authoritative and unique `set` of words.

        :param prefix: A `str`. The word prefix used to match words.
        :return: a 2-tuple of is_authoritative and a set of words.
            is_authoritative is True when the set of words are the only words
            that can match the prefix. The words are a set of words.
        """
        raise NotImplementedError

    @property
    def prefix(self):
        """The prefix use to match words to."""
        return self._prefix

    @property
    def file_path(self):
        """The path to the file that is the word source."""
        return self._document.get_uri()

    @property
    def text(self):
        """The text of the gedit.Document or None."""
        if not self._document:
            return None
        start_iter = self._document.get_start_iter()
        end_iter = self._document.get_end_iter()
        return self._document.get_text(start_iter, end_iter, True)


class TextGenerator(BaseSyntaxGenerator):
    """Generate a list of words that match a given prefix for a document."""

    def get_words(self, prefix=None):
        """See `BaseSyntaxGenerator.get_words`.

        is_authoritative is always False because TextGenerator because it is
        not for a specific document Language.
        """
        prefix = self.ensure_prefix(prefix)
        is_authoritative = False
        if len(prefix) > 0:
            # Match words that are just the prefix too.
            conditional = r'*'
        else:
            conditional = r'+'
        pattern = r'\b(%s[\w-]%s)' % (re.escape(prefix), conditional)
        word_re = re.compile(pattern, re.I)
        words = word_re.findall(self.text)
        # Find the unique words that do not have pseudo m-dashed in them.
        words = set(words)
        words = [DynamicProposal(word) for word in words if '--' not in word]
        return is_authoritative, words


class MarkupGenerator(BaseSyntaxGenerator):
    """Generate a list of elements and attributes for a document."""

    word_char = re.compile(r'[^<>]')
    common_attrs = []

    INSIDE_ATTRIBUTES = 'INSIDE_ATTRIBUTES'
    INSIDE_CLOSE = 'INSIDE_CLOSE'
    INSIDE_OPEN = 'INSIDE_OPEN'
    OUTSIDE = 'OUTSIDE'

    def get_cursor_context(self):
        """Return the context of the cursor in relation to the last tag."""
        text, start_iter, end_iter = get_word(self._document, self.word_char)
        if not start_iter.backward_char():
            # The start was at the begining of the doc; no tags were found.
            return self.OUTSIDE
        char = start_iter.get_char()
        if char == '>':
            return self.OUTSIDE
        elif text and text.startswith('/'):
            return self.INSIDE_CLOSE
        elif text and ' ' in text:
            return self.INSIDE_ATTRIBUTES
        else:
            return self.INSIDE_OPEN

    def get_words(self, prefix=None):
        """See `BaseSyntaxGenerator.get_words`."""
        prefix = self.ensure_prefix(prefix)
        context = self.get_cursor_context()
        if context == self.OUTSIDE:
            # is_authoritative is false and there are no words because the
            # cursor is not in a tag to complete.
            return False, set()
        is_authoritative = True
        if context == self.INSIDE_OPEN:
            words = self._get_open_tags(prefix)
        elif context == self.INSIDE_ATTRIBUTES:
            words = self._get_attributes(prefix)
        else:
            words = self._get_close_tags(prefix)
        return is_authoritative, words

    def get_cardinality(self, prefix):
        if prefix:
            # Match words that are just the prefix too.
            return r'*'
        else:
            return r'+'

    def _get_open_tags(self, prefix):
        """Return all the tag names."""
        cardinality = self.get_cardinality(prefix)
        prefix = re.escape(prefix)
        pattern = r'<(%s[\w_.:-]%s)' % (prefix, cardinality)
        word_re = re.compile(pattern, re.I)
        words = word_re.findall(self.text)
        return [DynamicProposal(word) for word in words]

    def _get_attributes(self, prefix):
        pattern = r'<[\w_.:-]+ ([\w_.:-]*)=[^>]+>'
        attrs_re = re.compile(pattern, re.I)
        attr_clusters = attrs_re.findall(self.text)
        attrs = set(self.common_attrs)
        for attr_cluster in attr_clusters:
            attr_pairs = attr_cluster.split()
            for pair in attr_pairs:
                attr = pair.split('=')
                attrs.add(attr[0])
        if prefix:
            for attr in list(attrs):
                if not attr.startswith(prefix):
                    attrs.remove(attr)
        return [DynamicProposal(attr) for attr in attrs]

    def _get_close_tags(self, prefix):
        """Return the tags that are still open before the cursor."""
        cardinality = self.get_cardinality(prefix)
        prefix = re.escape(prefix)
        # Get the text before the cursor.
        start_iter = self._document.get_start_iter()
        end_iter = self._document.get_iter_at_mark(
            self._document.get_insert())
        text = self._document.get_text(start_iter, end_iter, True)
        # Get all the open tags.
        open_pattern = r'<(%s[\w_.:-]%s)' % (prefix, cardinality)
        open_re = re.compile(open_pattern, re.I)
        open_tags = open_re.findall(text)
        # Get all the empty tags.
        empty_pattern = r'<(%s[\w_.:-]%s)[^>]*/>' % (prefix, cardinality)
        empty_re = re.compile(empty_pattern, re.I)
        empty_tags = empty_re.findall(text)
        # Get all the close tags.
        close_pattern = r'</(%s[\w_.:-]%s)' % (prefix, cardinality)
        close_re = re.compile(close_pattern, re.I)
        close_tags = close_re.findall(text)
        # Return only the tags that are still open.
        for tag in empty_tags:
            if tag in open_tags:
                open_tags.remove(tag)
        for tag in close_tags:
            if tag in open_tags:
                open_tags.remove(tag)
        return [DynamicProposal(tag + '>') for tag in open_tags]


class PythonSyntaxGenerator(BaseSyntaxGenerator):
    """Generate a list of Python symbols that match a given prefix."""

    word_char = re.compile(r'[\w_.]', re.I)
    _kwlist = None

    @property
    def kwlist(self):
        if self._kwlist is None:
            self._kwlist = [
                self._get_dynamic_proposal(None, word) for word in kwlist]
        return self._kwlist

    def get_words(self, prefix=None):
        """See `BaseSyntaxGenerator.get_words`.

        :return: a 2-tuple of is_authoritative and a set of matching
            identifiers. is_authoritative is True when the prefix is a part
            of a dotted identifier.
        """
        prefix = self.ensure_prefix(prefix)
        is_authoritative = False
        if prefix == '':
            is_authoritative = True

        import __builtin__
        global_syms = [
            self._get_dynamic_proposal(__builtin__, name)
            for name in dir(__builtin__)]
        try:
            pyo = compile(self._get_parsable_text(), 'sc.py', 'exec')
        except SyntaxError:
            # This cannot be completed because of syntax errors.
            # Return
            self._document.emit('syntax-error-python')
            is_authoritative = False
            return is_authoritative, []
        co_names = ('SIGNAL_RUN_LAST', 'TYPE_NONE', 'TYPE_PYOBJECT', 'object')
        local_syms = [
            self._get_dynamic_proposal(None, name)
            for name in pyo.co_names if name not in co_names]

        namespaces = self.string_before_cursor.split('.')
        if len(namespaces) == 1:
            # The identifier is scoped to this module (the document).
            symbols = local_syms + global_syms + self.kwlist
            symbols = [proposal for proposal in symbols
                       if proposal.get_text().startswith(prefix)]
            return is_authoritative, symbols

        # Remove the prefix to create the module's full name.
        namespaces.pop()
        module_name = '.'.join(namespaces)
        locald = {}
        try:
            # Check this file first.
            module_ = eval(module_name, globals(), locald)
        except NameError:
            # Try a true import.
            try:
                module_ = __import__(module_name, globals(), locald, [])
            except ImportError:
                return is_authoritative, []

        for symbol in namespaces[1:]:
            module_ = getattr(module_, symbol)
        is_authoritative = True
        symbols = [self._get_dynamic_proposal(module_, name)
                   for name in dir(module_) if name.startswith(prefix)]
        return is_authoritative, symbols

    def _get_parsable_text(self):
        """Return the parsable text of the module.

        The line being edited may not be valid syntax, so the line is
        replaced with 'pass', or if it starts a block, it becomes 'if True:'
        """
        current_iter = self._document.get_iter_at_mark(
            self._document.get_insert())
        index = current_iter.get_line()
        text_lines = self.text.splitlines()
        if index + 1 == len(text_lines):
            # The current line is the last line. Add a fake line because
            # the compiler will require another line to follow a comment.
            text_lines.append('')
        current_indentation = self._get_indentation(text_lines[index])
        next_indentation = self._get_indentation(text_lines[index + 1])
        if len(next_indentation) > len(current_indentation):
            # Make this line compilable for the next block.
            text_lines[index] = current_indentation + 'if True:'
        else:
            # Comment-out this line so that it is not compiled.
            text_lines[index] = current_indentation + 'pass'
        return '\n'.join(text_lines)

    def _get_indentation(self, line):
        "Return the line's indentation"
        indentation_pattern = re.compile(r'^[ \t]*')
        match = indentation_pattern.match(line)
        if match:
            return match.group()
        # No match means the indentation is an empty string.
        return ''

    def _get_dynamic_proposal(self, module, name):
        info = None
        if module is None:
            identifier = None
        elif type(module) == 'dict':
            identifier = module[name]
        else:
            identifier = module.__dict__[name]
        return PythonProposal(name, info=identifier)


class SyntaxController(PluginMixin):
    """This class manages the gedit.View's interaction with the SyntaxView."""

    def __init__(self, window):
        """Initialize the controller for the gedit.View."""
        self.signal_ids = {}
        self.view = None
        self.window = window
        self.set_view(window.get_active_view())

    def deactivate(self):
        """Clean up resources before deactivation."""
        self.set_view(None)

    def set_view(self, view, is_reset=False):
        """Set the view to be controlled.

        Installs signal handlers for the view. Calling document.get_uri()
        self.set_view(None) will effectively remove all the control from
        the current view. when is_reset is True, the current view's
        signals will be reset.
        """
        if view is self.view and not is_reset:
            return

        if self.view:
            # Unregister the current view before assigning the new one.
            self._disconnectSignal(self.view, 'destroy')
            self._disconnectSignal(self.view, 'notify::editable')

        self.view = view
        if view is not None:
            self.signal_ids['destroy'] = view.connect(
                'destroy', self.on_view_destroy)
            self.signal_ids['notify::editable'] = view.connect(
                'notify::editable', self.on_notify_editable)

    def _disconnectSignal(self, obj, signal):
        """Disconnect the signal from the provided object."""
        if signal in self.signal_ids:
            obj.disconnect(self.signal_ids[signal])
            del self.signal_ids[signal]

    def show_syntax_view(self, widget=None):
        """Show the SyntaxView widget."""
        if not self.view.get_editable():
            return
        self.completion = self.view.get_completion()
        language_id = None
        document = self.view.get_buffer()
        if hasattr(document, 'get_language'):
            # How can we not get a document or language?
            language = document.get_language()
            if language is not None:
                language_id = language.get_id()
        title = _('GDP Syntax Completer')
        self.provider = DynamicProvider(
            title, language_id, self.on_proposal_activated, document)
        self.completion.show(
            [self.provider], self.completion.create_context())

    def get_word_prefix(self, document):
        """Return a 3-tuple of the word fragment before the cursor.

        The tuple contains the (word_fragement, start_iter, end_iter) to
        identify the prefix and its starting and end position in the
        document.
        """
        word_char = re.compile(r'[\w_-]', re.I)
        return get_word(document, word_char)

    def insert_word(self, word, start=None):
        """Return True when the word is inserted into the Document.

        The word cannot be None or an empty string.
        """
        assert word, "The word cannot be None or an empty string."
        document = self.view.get_buffer()
        if start:
            document.delete(
                start, document.get_iter_at_mark(document.get_insert()))
        document.insert_at_cursor(word)

    def correct_language(self, document):
        """Correct the language for ambuguous mime-types."""
        if not hasattr(document, 'get_language'):
            return
        file_path = document.get_uri_for_display()
        if doctest_pattern.match(file_path):
            document.set_language(doctest_language)

    def on_proposal_activated(self, proposal, piter):
        """Complete the word using the proposal."""
        if not proposal:
            return
        document = self.view.get_buffer()
        (ignored, start, end_) = self.get_word_prefix(document)
        word = proposal.get_text()
        self.insert_word(word, start)
        return True

    def on_notify_editable(self, view, param_spec):
        """Update the controller when the view editable state changes.

        This method is ultimately responsible for enabling and disabling
        the SyntaxView widget for syntax completion.
        """
        self.set_view(view, True)

    def on_view_destroy(self, view):
        """Disconnect the controller."""
        self.deactivate()
