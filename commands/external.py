"""
commands/external.py  -  External commands (each one starts a NEW process)
===========================================================================
ExternalCommand        - parent class: runs build_cmd() with subprocess.Popen
  |-- ScriptCommand     - a .py script from MY_PATH   ->  python.exe script.py args
  |-- CmdCommand        - a CMD built-in (copy, ren)  ->  cmd.exe /c copy a b
  +-- ExecutableCommand - an .exe (ping, notepad)     ->  ping www.google.com

The children only decide WHAT to run (build_cmd).
The parent decides HOW to run it (execute). This is inheritance.
"""

import sys
import subprocess
from .base import Command


class ExternalCommand(Command):

    def __init__(self, name):
        self.name = name

    def build_cmd(self, args):
        """Return the command line to run. Each child class overrides this."""
        raise NotImplementedError

    def execute(self, args, stdin=None, stdout=None):
        """
        Start the process and return the Popen object WITHOUT waiting.
        Not waiting is what lets all the commands in a pipe run in parallel.
        stdin / stdout can be: None (keyboard/screen), an open file,
        the previous process's output, or subprocess.PIPE.
        """
        return subprocess.Popen(self.build_cmd(args), stdin=stdin, stdout=stdout)


class ScriptCommand(ExternalCommand):
    """A Python script. We add python.exe so the user doesn't have to type it."""

    def __init__(self, name, script_path):
        super().__init__(name)
        self.script_path = script_path

    def build_cmd(self, args):
        # sys.executable = the full path of the python.exe that runs our shell
        return [sys.executable, self.script_path] + [self.unquote(a) for a in args]


class CmdCommand(ExternalCommand):
    """A command that only exists inside cmd.exe (copy, ren, del...)."""

    def build_cmd(self, args):
        return "cmd.exe /c " + " ".join([self.name] + args)


class ExecutableCommand(ExternalCommand):
    """
    A program (.exe). We pass the line as one string, so quotes stay exactly
    as the user typed them (find "Teams" needs the quotes).
    Windows itself searches the current folder and the PATH for the .exe.
    """

    def build_cmd(self, args):
        return " ".join([self.name] + args)
