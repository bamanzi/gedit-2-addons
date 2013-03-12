# Pyflakes is not ported to Pythong 3 yet.

__all__ = [
    'PyFlakesChecker',
    ]

import os
import subprocess


PACKAGE_PATH = os.path.dirname(__file__)


class PyFlakesChecker(object):
    """A fake for py3 that can run py2 in a sub-proc."""

    def __init__(self, tree, filename='(none)'):
        self.messages = []
        script = os.path.join(PACKAGE_PATH, 'formatcheck.py')
        command = ['python2', script, filename]
        linter = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        issues, errors = linter.communicate()
        issues = issues.decode('ascii').strip()
        if issues:
            for line in issues.split('\n')[1:]:
                line_no, message = line.split(':')
                self.messages.append(
                    '%s:%s:%s' % (filename, line_no.strip(), message.strip()))
