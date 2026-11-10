__author__ = 'lahav pelts'

"""
commands/base.py  -  Base command classes
==========================================
Command          -  the parent of ALL commands
InternalCommand  -  commands that run inside the shell itself (no new process)
"""

import sys


class Command:
    """
    Base class for all commands.

    Every command implements execute(args, stdin, stdout):
      args   - list of arguments (without the command name)
      stdin  - where to read from  (None = keyboard)
      stdout - where to write to   (None = screen)
    """
    name = ""          # e.g. "dir"
    description = ""   # shown by 'help'
    usage = ""         # shown by 'help <command>'

    def execute(self, args, stdin=None, stdout=None):
        raise NotImplementedError

    @staticmethod
    def unquote(s):
        """Remove surrounding quotes:  "hello"  ->  hello"""
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
            return s[1:-1]
        return s


class InternalCommand(Command):
    """
    A command that runs inside the shell's own Python process.
    It does NOT start a new process. It just writes its output to stdout.
    """

    def _stdout(self, stdout):
        """If no output file was given, write to the screen."""
        return stdout if stdout is not None else sys.stdout

    def _clean_args(self, args):
        """Remove quotes from every argument."""
        return [self.unquote(a) for a in args]
