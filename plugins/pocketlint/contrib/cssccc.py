'''
This code is in the public domain.

Check CSS code for some common coding conventions.
The code must be in a valid CSS format.
It is recommend to first parse it using cssutils.
It is also recommend to check it with pocket-lint for things like trailing
spaces or tab characters.

If a comment is on the whole line, it will consume the whole line like it
was not there.
If a comment is inside a line it will only consume its own content.

Bases on Stoyan Stefanov's http://www.phpied.com/css-coding-conventions/

'@media' rule is not supported.
    @media print {
      html {
        background: #fff;
        color: #000;
      }
      body {
        padding: 1in;
        border: 0.5pt solid #666;
      }
    }

The following at-rules are supported:
 * keyword / text at-rules
  * @charset "ISO-8859-15";
  * @import url(/css/screen.css) screen, projection;
  * @namespace foo "http://example.com/ns/foo";
 * keybord / block rules
  * @page { block; }
  * @font-face { block; }


TODO:
 * add warning for using px for fonts.
 * add Unicode support.
 * add AtRule checks
 * add support for TAB as a separator / identation.
 * add support for @media
'''

from __future__ import (
    absolute_import,
    unicode_literals,
    with_statement,
)

__version__ = '0.1.1'

import sys

SELECTOR_SEPARATOR = ','
DECLARATION_SEPARATOR = ';'
PROPERTY_SEPARATOR = ':'
COMMENT_START = r'/*'
COMMENT_END = r'*/'
AT_TEXT_RULES = ['import', 'charset', 'namespace']
AT_BLOCK_RULES = ['page', 'font-face']
# If you want
# selector,
# selector2
# {
#     property:
# }
#IGNORED_MESSAGES = ['I013', 'I014']

# If you want
# selector,
# selector {
#     property:
# }
#IGNORED_MESSAGES = ['I005', 'I014']

# If you want
# selector,
# selector2 {
#     property:
#     }
IGNORED_MESSAGES = ['I005', 'I006']


def to_console(text):
    sys.stdout.write(text)
    sys.stdout.write('\n')


class CSSRule(object):
    '''A CSS rule.'''

    def check(self):
        '''Check the rule.'''
        raise AssertionError('Method not implemtned.')


class CSSAtRule(object):
    '''A CSS @rule.'''

    type = object()

    def __init__(self, identifier, keyword, log, text=None, block=None):
        self.identifier = identifier
        self.keyword = keyword
        self.text = text
        self.block = block
        self.log = log

    def check(self):
        '''Check the rule.'''


class CSSRuleSet(object):
    '''A CSS rule_set.'''

    type = object()

    def __init__(self, selector, declarations, log):
        self.selector = selector
        self.declarations = declarations
        self.log = log

    def __str__(self):
        return '%s{%s}' % (str(self.selector), str(self.declarations))

    def __repr__(self):
        return '%d:%s{%s}' % (
            self.selector.start_line,
            str(self.selector),
            str(self.declarations))

    def check(self):
        '''Check the rule set.'''
        self.checkSelector()
        self.checkDeclarations()

    def checkSelector(self):
        '''Check rule-set selector.'''
        start_line = self.selector.getStartLine()
        selectors = self.selector.text.split(SELECTOR_SEPARATOR)
        offset = 0
        last_selector = selectors[-1]
        first_selector = selectors[0]
        rest_selectors = selectors[1:]

        if first_selector.startswith('\n\n\n'):
            self.log(start_line, 'I002', 'To many newlines before selectors.')
        elif first_selector.startswith('\n\n'):
            pass
        elif start_line > 2:
            self.log(start_line, 'I003', 'To few newlines before selectors.')
        else:
            pass

        for selector in rest_selectors:
            if not selector.startswith('\n'):
                self.log(
                    start_line + offset,
                    'I004',
                    'Selector must be on a new line.')
            offset += selector.count('\n')

        if not last_selector.endswith('\n'):
            self.log(
                start_line + offset,
                'I005',
                'No newline after last selector.')

        if (len(last_selector) < 2 or
                not (last_selector[-2] != ' ' and last_selector[-1] == (' '))):
            self.log(
                start_line + offset,
                'I013',
                'Last selector must be followed by " {".')

    def checkDeclarations(self):
        '''Check rule-set declarations.'''
        start_line = self.declarations.getStartLine()
        declarations = self.declarations.text.split(DECLARATION_SEPARATOR)
        offset = 0

        # Check all declarations except last as this is the new line.
        first_declaration = True
        for declaration in declarations[:-1]:
            if not declaration.startswith('\n'):
                self.log(
                    start_line + offset,
                    'I007',
                    'Each declarations should start on a new line.')
            elif (not declaration.startswith('\n    ') or
                  declaration[5] == ' '):
                self.log(
                    start_line + offset,
                    'I008',
                    'Each declaration must be indented with 4 spaces.')

            parts = declaration.split(PROPERTY_SEPARATOR)
            if len(parts) != 2:
                self.log(
                    start_line + offset,
                    'I009',
                    'Wrong separator on property: value pair.')
            else:
                prop, value = parts
                if prop.endswith(' '):
                    self.log(
                        start_line + offset,
                        'I010',
                        'Whitespace before ":".')
                if not (value.startswith(' ') or value.startswith('\n')):
                    self.log(
                        start_line + offset,
                        'I011',
                        'Missing whitespace after ":".')
                elif value.startswith('  '):
                    self.log(
                        start_line + offset,
                        'I012',
                        'Multiple whitespaces after ":".')
            if first_declaration:
                first_declaration = False
            else:
                offset += declaration.count('\n')

        last_declaration = declarations[-1]
        offset += last_declaration.count('\n')
        if last_declaration != '\n':
            self.log(
                start_line + offset,
                'I006',
                'Rule declarations should end with a single new line.')
        if last_declaration != '\n    ':
            self.log(
                start_line + offset,
                'I014',
                'Rule declarations should end indented on a single new line.')


class CSSStatementMember(object):
    '''A member of CSS statement.'''

    def __init__(self, start_line, start_character, text):
        self.start_line = start_line
        self.start_character = start_character
        self.text = text

    def getStartLine(self):
        '''Return the line number for first character in the statement and
        the number of new lines untilg the first character.'''
        index = 0
        text = self.text
        try:
            character = text[index]
            while character == '\n':
                index += 1
                character = text[index]
        except IndexError:
            # The end of string was reached without finding a statement.
            pass

        return self.start_line + index + 1

    def __str__(self):
        return self.text

    def __repr__(self):
        return '%d:%d:{%s}' % (
            self.start_line, self.start_character, self.text)


class CSSCodingConventionChecker(object):
    '''CSS coding convention checker.'''

    icons = {
        'E': 'error',
        'I': 'info',
    }

    def __init__(self, text, logger=None):
        self._text = text.splitlines(True)
        self.line_number = 0
        self.character_number = 0
        if logger:
            self._logger = logger
        else:
            self._logger = self._defaultLog

    def log(self, line_number, code, message):
        '''Log the message with `code`.'''
        if code in IGNORED_MESSAGES:
            return
        icon = self.icons[code[0]]
        self._logger(line_number, code + ': ' + message, icon=icon)

    def check(self):
        '''Check all rules.'''
        for rule in self.getRules():
            rule.check()

    def getRules(self):
        '''Generates the next CSS rule ignoring comments.'''
        while True:
            yield self.getNextRule()

    def getNextRule(self):
        '''Return the next parsed rule.

        Raise `StopIteration` if we are at the last rule.
        '''
        if self._nextStatementIsAtRule():
            text = None
            block = None
            keyword = self._parse('@')
            # TODO: user regex [ \t {]
            keyword_text = self._parse(' ')
            keyword_name = keyword_text.text
            keyword.text += '@' + keyword_name + ' '

            if keyword_name.lower() in AT_TEXT_RULES:
                text = self._parse(';')
            elif keyword_name.lower() in AT_BLOCK_RULES:
                start = self._parse('{')
                keyword.text += start.text
                block = self._parse('}')
            else:
                self._parse(';')
                raise StopIteration

            return CSSAtRule(
                identifier=keyword_name,
                keyword=keyword,
                text=text,
                block=block,
                log=self.log)
        else:
            selector = self._parse('{')
            declarations = self._parse('}')
            return CSSRuleSet(
                selector=selector,
                declarations=declarations,
                log=self.log)

    def _defaultLog(self, line_number, message, icon='info'):
        '''Log the message to STDOUT.'''
        to_console('    %4s:%s' % (line_number, message))

    def _nextStatementIsAtRule(self):
        '''Return True if next statement in the buffer is an at-rule.

        Just look for open brackets and see if there is an @ before that
        braket.
        '''
        search_buffer = []
        line_counter = self.line_number
        current_line = self._text[line_counter][self.character_number:]
        while current_line.find('@') == -1:
            search_buffer.append(current_line)
            line_counter += 1
            try:
                current_line = self._text[line_counter]
            except IndexError:
                return False

        text_buffer = ''.join(search_buffer)
        if text_buffer.find('{') == -1:
            return True
        else:
            return False

    def _parse(self, stop_character):
        '''Return the parsed text until stop_character.'''
        try:
            self._text[self.line_number][self.character_number]
        except IndexError:
            raise StopIteration
        result = []
        start_line = self.line_number
        start_character = self.character_number
        comment_started = False
        while True:
            try:
                data = self._text[self.line_number][self.character_number:]
            except IndexError:
                break

            # Look for comment start/end.
            (comment_update, before_comment,
             after_comment, newline_consumed) = _check_comment(data)
            if comment_update is not None:
                comment_started = comment_update

            if comment_started:
                # We are inside a comment.
                # Add the data before the comment and go to next line.
                if before_comment is not None:
                    result.append(before_comment)
                self.character_number = 0
                self.line_number += 1
                continue

            # If we have a comment, strip it from the data.
            # Remember the initial cursor position to know where to
            # continue.
            initial_position = data.find(stop_character)
            if before_comment is not None or after_comment is not None:
                if before_comment is None:
                    before_comment = ''
                if after_comment is None:
                    after_comment = ''
                data = before_comment + after_comment

            if initial_position == -1 or newline_consumed:
                # We are not at the end.
                # Go to next line and append the data.
                result.append(data)
                self.character_number = 0
                self.line_number += 1
                continue
            else:
                # Delimiter found.
                # Find it again in the text that now has no comments.
                # Append data until the delimiter.
                # Move cursor to next character and stop searching for it.
                new_position = data.find(stop_character)
                result.append(data[:new_position])
                self.character_number += initial_position + 1
                break

        return CSSStatementMember(
            start_line=start_line,
            start_character=start_character,
            text=''.join(result))


def _check_comment(data):
    '''Check the data for comment markers.'''

    comment_started = None
    before_comment = None
    after_comment = None
    newline_consumed = False

    comment_start = data.find(COMMENT_START)
    if comment_start != -1:
        comment_started = True
        before_comment = data[:comment_start]
        # Only use `None` to signal that there is no text before the comment.
        if before_comment == '':
            before_comment = None

    comment_end = data.find(COMMENT_END)
    if comment_end != -1:
        comment_started = False
        # Set comment end after the lenght of the actual comment end
        # marker.
        comment_end += len(COMMENT_END)
        if before_comment is None and data[comment_end] == '\n':
            # Consume the new line if it next to the comment end and
            # the comment in on the whole line.
            comment_end += 1
            newline_consumed = True
        after_comment = data[comment_end:]
    return (comment_started, before_comment, after_comment, newline_consumed)


def show_usage():
    '''Print the command usage.'''
    to_console('Usage: cssccc OPTIONS')
    to_console('  -h, --help\t\tShow this help.')
    to_console('  -v, --version\t\tShow version.')
    to_console('  -f FILE, --file=FILE\tCheck FILE')


def read_file(filename):
    '''Return the content of filename.'''
    text = ''
    with open(filename, 'rt') as f:
        text = f.read()
    return text


if __name__ == '__main__':
    if len(sys.argv) < 2:
        show_usage()
    elif sys.argv[1] in ['-v', '--version']:
        to_console('CSS Code Convention Checker %s' % (__version__))
        sys.exit(0)
    elif sys.argv[1] == '-f':
        text = read_file(sys.argv[2])
        checker = CSSCodingConventionChecker(text)
        sys.exit(checker.check())
    elif sys.argv[1] == '--file=':
        text = read_file(sys.argv[1][len('--file='):])
        checker = CSSCodingConventionChecker(text)
        sys.exit(checker.check())
    else:
        show_usage()
