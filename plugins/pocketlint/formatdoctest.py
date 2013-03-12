#!/usr/bin/python
# Copyright (C) 2009-2013 - Curtis Hovey <sinzui.is at verizon.net>
# This software is licensed under the MIT license (see the file COPYING).
"""Reformat a doctest to Launchpad style."""

from __future__ import (
    absolute_import,
    unicode_literals,
    with_statement,
)


__all__ = [
    'DoctestReviewer',
]


import _ast
import os
import re
import sys
from difflib import unified_diff
from doctest import DocTestParser, Example
from optparse import OptionParser
from textwrap import wrap

from pocketlint.reporter import Reporter
try:
    from pyflakes.checker import Checker as PyFlakesChecker
    PyFlakesChecker
except ImportError:
    from pocketlint import PyFlakesChecker


class DoctestReviewer(object):
    """Check and reformat doctests."""
    rule_pattern = re.compile(r'([=~-])+[ ]*$')
    moin_pattern = re.compile(r'^(=+)[ ](.+)[ ](=+[ ]*)$')

    SOURCE = 'source'
    WANT = 'want'
    NARRATIVE = 'narrative'

    def __init__(self, file_path, doctest, reporter=None, options=None):
        self.doctest = doctest
        self.file_path = file_path
        self.base_dir = os.path.dirname(file_path)
        self.file_name = os.path.basename(file_path)
        self.blocks = []
        self.block = []
        self.block_method = self.preserve_block
        self.code_lines = []
        self.example = None
        self.last_bad_indent = 0
        self.has_printed_filename = False
        self._reporter = reporter or Reporter(Reporter.CONSOLE)
        self.options = options

    def get_parts(self):
        parser = DocTestParser()
        try:
            return parser.parse(self.doctest, self.file_path)
        except ValueError as error:
            # Output code without unicode literals needs to be normalised
            # largely for the test suite, and somewhat for the person reading
            # message.
            message = str(error).replace("u'", "'")
            self._print_message(message, 0)
            return []

    def _print_message(self, message, lineno):
        """Print the error message with the lineno.

        :param message: The message to print.
        :param lineno: The line number the message pertains to.
        """
        self._reporter(
            int(lineno), message,
            base_dir=self.base_dir, file_name=self.file_name)

    def _is_formatted(self, text):
        """Return True if the text is pre-formatted, otherwise False.

        :param: text a string, or a list of strings.
        """
        if isinstance(text, list):
            text = text[0]
        return text.startswith(' ')

    def _walk(self, doctest_parts):
        """Walk the doctest parts; yield the line and kind.

        Yield the content of the line, and its kind (SOURCE, WANT, NARRATIVE).
        SOURCE and WANT lines are stripped of indentation, SOURCE is also
        stripped of the interpreter symbols.

        :param doctest_parts: The output of DocTestParser.parse.
        """
        for part in doctest_parts:
            if part == '':
                continue
            if isinstance(part, Example):
                self.example = part
                for line in part.source.splitlines():
                    kind = DoctestReviewer.SOURCE
                    yield line, kind
                for line in part.want.splitlines():
                    kind = DoctestReviewer.WANT
                    yield line, kind
            else:
                self.example = None
                kind = DoctestReviewer.NARRATIVE
                for line in part.splitlines():
                    yield line, kind

    def _apply(self, line_methods):
        """Call each line_method for each line in the doctest.

        :param line_methods: a list of methods that accept lineno, line,
            and kind as arguments. Each method must return the line for
            the next method to process.
        """
        self.blocks = []
        self.block = []
        lineno = 0
        previous_kind = DoctestReviewer.NARRATIVE
        for line, kind in self._walk(self.get_parts()):
            lineno += 1
            # Some method could check if the line number is one that
            # is skipped by doctest parser and increment the number again.
            # line probably needs to get a \n add to it too.
            self._append_source(kind, line)
            if kind != previous_kind and kind != DoctestReviewer.WANT:
                # The WANT block must adjoin the preceding SOURCE block.
                self._store_block(previous_kind)
            for method in line_methods:
                line = method(lineno, line, kind, previous_kind)
                if line is None:
                    break
            if not line:
                continue
            self.block.append(line)
            previous_kind = kind
        # Capture the last block and a blank line.
        self.block.append('\n')
        self._store_block(previous_kind)

    def _append_source(self, kind, line):
        """Update the list of source code lines seen."""
        if kind == self.SOURCE:
            self.code_lines.append(line)
        else:
            self.code_lines.append('')

    def _store_block(self, kind):
        """Append the block to blocks, re-wrap unformatted narrative.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        """
        if len(self.block) == 0:
            return
        block = self.block_method(kind, self.block, self.blocks)
        self.blocks.append('\n'.join(block))
        self.block = []

    def check(self):
        """Check the doctest for style and code issues.

        1. Check line lengths.
        2. Check that headings are not in Moin format.
        3. Check indentation.
        4. Check trailing whitespace.
        """
        self.code_lines = []
        self.last_bad_indent = 0
        self.block_method = self.preserve_block
        self.example = None
        self.has_printed_filename = False
        self.check_source_comments()
        line_checkers = [
            self.check_length,
            self.check_heading,
            self.check_indentation,
            self.check_trailing_whitespace,
        ]
        self._apply(line_checkers)
        code = '\n'.join(self.code_lines)
        self.check_source_code(code)

    def format(self):
        """Reformat doctest.

        1. Tests are reindented to 4 spaces.
        2. Simple narrative is rewrapped to 78 character width.
        3. Formatted (indented) narrative is preserved.
        4. Moin headings are converted to RSR =, == , and === levels.
        5. There is one blank line between blocks,
        6. Except for headers which have two leading blank lines.
        7. All trailing whitespace is removed.

        SOURCE and WANT long lines are not fixed--this is a human operation.
        """
        self.code_lines = []
        line_checkers = [
            self.fix_trailing_whitespace,
            self.fix_indentation,
            self.fix_heading,
            self.fix_narrative_paragraph,
        ]
        self.block_method = self.format_block
        self._apply(line_checkers)
        self.block_method = self.preserve_block
        return '\n\n'.join(self.blocks)

    def preserve_block(self, kind, block, blocks):
        """Do nothing to the block.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        :param block: The list of lines that should remain together.
        :param blocks: The list of all collected blocks.
        """
        return block

    def format_block(self, kind, block, blocks):
        """Format paragraph blocks.

        :param kind: The block's kind (SOURCE, WANT, NARRATIVE)
        :param block: The list of lines that should remain together.
        :param blocks: The list of all collected blocks.
        """
        if kind != DoctestReviewer.NARRATIVE or self._is_formatted(block):
            return block
        try:
            rules = ('===', '---', '...')
            last_line = block[-1]
            is_heading = last_line[0:3] in rules and last_line[-3:] in rules
        except IndexError:
            is_heading = False
        if len(blocks) != 0 and is_heading:
            # Headings should have an extra leading blank line.
            block.insert(0, '')
        elif is_heading:
            # Do nothing. This is the first heading in the file.
            pass
        else:
            long_line = ' '.join(block).strip()
            block = wrap(long_line, 72)
        return block

    def check_source_comments(self):
        """Comments are not appropiate in source examples."""
        for lineno, line in enumerate(self.doctest.splitlines()):
            if '>>> #' in line or '... #' in line:
                self._print_message(
                    'Comment belongs in narrative.', lineno + 1)

    def is_code_comment(self, line):
        """Return True if the line is a code comment."""
        comment_pattern = re.compile(r'^\s+#')
        return comment_pattern.match(line) is not None

    def check_length(self, lineno, line, kind, previous_kind):
        """Check the length of the line.

        Each kind of line has a maximum length:

        * NARRATIVE: 78 characters.
        * SOURCE: 70 characters (discounting indentation and interpreter).
        * WANT: 74 characters (discounting indentation).
        """
        if kind == DoctestReviewer.NARRATIVE and self.is_code_comment(line):
            # comments follow WANT rules because they are in code.
            kind = DoctestReviewer.WANT
            line = line.lstrip()
        length = len(line)
        if kind == DoctestReviewer.NARRATIVE and length > 78:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        elif kind == DoctestReviewer.WANT and length > 74:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        elif kind == DoctestReviewer.SOURCE and length > 70:
            self._print_message('%s exceeds 78 characters.' % kind, lineno)
        else:
            # This line has a good length.
            pass
        return line

    def check_indentation(self, lineno, line, kind, previous_kind):
        """Check the indentation of the SOURCE or WANT line."""
        if kind == DoctestReviewer.NARRATIVE:
            return line
        if self.example.indent != 4:
            if self.last_bad_indent != lineno - 1:
                self._print_message('%s has bad indentation.' % kind, lineno)
            self.last_bad_indent = lineno
        return line

    def check_trailing_whitespace(self, lineno, line, kind, previous_kind):
        """Check for the presence of trailing whitespace in the line."""
        if line.endswith(' '):
            self._print_message('%s has trailing whitespace.' % kind, lineno)
        return line

    def check_heading(self, lineno, line, kind, previous_kind):
        """Check for narrative lines that use moin headers instead of RST."""
        if kind != DoctestReviewer.NARRATIVE:
            return line
        moin = self.moin_pattern.match(line)
        if moin is not None:
            self._print_message('%s uses a moin header.' % kind, lineno)
        return line

    def check_source_code(self, code):
        """Check for source code problems in the doctest using pyflakes.

        The most common problem found are unused imports. `UndefinedName`
        errors are suppressed because the test setup is not known.
        """
        if code == '':
            return
        try:
            tree = compile(
                code, self.file_path, "exec", _ast.PyCF_ONLY_AST)
        except (SyntaxError, IndentationError) as exc:
            lineno = exc.lineno or 0
            line = exc.text or ''
            if line.endswith("\n"):
                line = line[:-1]
            self._print_message(
                'Could not compile:\n    %s' % line, lineno)
        else:
            warnings = PyFlakesChecker(tree)
            for warning in warnings.messages:
                if 'undefined name ' in str(warning):
                    continue
                dummy, lineno, message = str(warning).split(':')
                self._print_message(message.strip(), lineno)

    def fix_trailing_whitespace(self, lineno, line, kind, previous_kind):
        """Return the line striped of trailing whitespace."""
        return line.rstrip()

    def fix_indentation(self, lineno, line, kind, previous_kind):
        """set the indentation to 4-spaces."""
        if kind == DoctestReviewer.NARRATIVE:
            return line
        elif kind == DoctestReviewer.WANT:
            return '    %s' % line
        else:
            if line.startswith(' '):
                # This is a continuation of DoctestReviewer.SOURCE.
                return '    ... %s' % line
            else:
                # This is a start of DoctestReviewer.SOURCE.
                return '    >>> %s' % line

    def fix_heading(self, lineno, line, kind, previous_kind):
        """Switch Moin headings to RST headings."""
        if kind != DoctestReviewer.NARRATIVE:
            return line
        moin = self.moin_pattern.match(line)
        if moin is None:
            return line
        heading_level = len(moin.group(1))
        heading = moin.group(2)
        rule_length = len(heading)
        if heading_level == 1:
            rule = '=' * rule_length
        elif heading_level == 2:
            rule = '-' * rule_length
        else:
            rule = '.' * rule_length
        # Force the heading on to the block of lines.
        self.block.append(heading)
        return rule

    def fix_narrative_paragraph(self, lineno, line, kind, previous_kind):
        """Break narrative into paragraphs."""
        if kind != DoctestReviewer.NARRATIVE or len(self.block) == 0:
            return line
        if line == '':
            # This is the start of a new paragraph in the narrative.
            self._store_block(previous_kind)
        if self._is_formatted(line) and not self._is_formatted(self.block):
            # This line starts a pre-formatted paragraph.
            self._store_block(previous_kind)
        return line

    def format_and_save(self, is_interactive=False):
        new_doctest = self.format()
        if new_doctest != self.doctest:
            if is_interactive:
                diff = unified_diff(
                    self.doctest.splitlines(), new_doctest.splitlines())
                sys.stdout.write('\n'.join(diff))
                sys.stdout.write('\n\n')
                if sys.version_info >= (3,):
                    user_input = input
                else:
                    user_input = raw_input
                do_save = user_input(
                    'Do you wish to save the changes? S(ave) or C(ancel)?')
            else:
                do_save = 'S'
            self.doctest = new_doctest
            if do_save.upper() == 'S':
                with open(self.file_path, 'wt') as doctest_file:
                    doctest_file.write(new_doctest)


def get_option_parser():
    """Return the option parser for this program."""
    usage = "usage: %prog [options] doctest.txt"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-f", "--format", dest="is_format", action="store_true",
        help="Reformat the doctest.")
    parser.add_option(
        "-i", "--interactive", dest="is_interactive", action="store_true",
        help="Approve each change.")
    parser.set_defaults(
        is_format=False,
        is_interactive=False)
    return parser


def main(argv=None):
    """Run the operations requested from the command line."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, args) = parser.parse_args(args=argv[1:])
    if len(args) == 0:
        parser.error("A doctest must be specified.")

    for file_path in args:
        with open(file_path) as doctest_file:
            doctest_data = doctest_file.read().decode('utf-8')
        reviewer = DoctestReviewer(file_path, doctest_data)
        if options.is_format:
            reviewer.format_and_save()
        reviewer.check()


if __name__ == '__main__':
    sys.exit(main())
