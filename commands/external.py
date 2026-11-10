"""
commands/external.py  -  External commands
===========================================
Three types of external commands:

  ScriptCommand     -  Python scripts from MY_PATH directories
                       (runs with sys.executable, no need to type "python")
  CmdCommand        -  CMD built-in commands (copy, ren, del, move...)
                       (runs via shell=True so cmd.exe handles quoting)
  ExecutableCommand -  EXE files from the Windows PATH
                       (ping, notepad, calc, tasklist, find, findstr...)
                       (runs via shell=True so quotes are preserved exactly)

Each class implements:
  build_cmd(args)  ->  the command string or list to pass to subprocess.Popen
  execute(args)    ->  runs the command and returns a Popen object (for piping)
"""

import sys
import subprocess
from .base import Command


def _strip_arg(s: str) -> str:
    """Strip surrounding quotes from a single argument (internal helper)."""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


class ScriptCommand(Command):
    """
    Runs a Python script found in one of the MY_PATH directories.

    Example:  hexdump.py abc.exe
      ->  python.exe  <full-path-to-script>  abc.exe

    Arguments are stripped of surrounding quotes before being passed to
    the script (Python receives clean argv values).
    """
    name = "script"
    description = "Python script"

    def __init__(self, script_path: str):
        self.script_path = script_path

    def build_cmd(self, args: list) -> list:
        """Build the full command list, stripping quotes from arguments."""
        clean = [_strip_arg(a) for a in args]
        return [sys.executable, self.script_path] + clean

    def execute(self, args: list, stdin=None, stdout=None):
        """Run the script with Popen and return the Popen object."""
        proc = subprocess.Popen(
            self.build_cmd(args),
            stdin=stdin,
            stdout=stdout,
            text=True,
        )
        return proc


class CmdCommand(Command):
    """
    Runs a CMD built-in command (copy, ren, del, move...) using shell=True.

    shell=True causes Python to invoke cmd.exe /c internally, which means
    CMD handles quoting and built-in resolution correctly.

    Example:  copy a.txt b.txt
      ->  cmd.exe /c copy a.txt b.txt   (handled by shell=True)
    """
    name = "cmd_builtin"
    description = "CMD built-in command"

    def __init__(self, cmd_name: str):
        self.cmd_name = cmd_name

    def build_cmd(self, args: list) -> str:
        """Build the command as a string (quotes are preserved as typed)."""
        return ' '.join([self.cmd_name] + args)

    def execute(self, args: list, stdin=None, stdout=None):
        """Run via shell=True so cmd.exe processes the command string."""
        proc = subprocess.Popen(
            self.build_cmd(args),
            stdin=stdin,
            stdout=stdout,
            text=True,
            shell=True,
        )
        return proc


class ExecutableCommand(Command):
    """
    Runs an EXE file directly - Windows PATH resolves it automatically.

    Examples:  ping, notepad, calc, tasklist, find, findstr, netstat...

    Uses shell=True with a string so that quotes are preserved exactly as
    the user typed them.  This is important for commands like find "Teams"
    which require double quotes around the search string.
    """
    name = "executable"
    description = "External executable"

    def __init__(self, exe_name: str):
        self.exe_name = exe_name

    def build_cmd(self, args: list) -> str:
        """Build the command as a string (original quotes preserved)."""
        return ' '.join([self.exe_name] + args)

    def execute(self, args: list, stdin=None, stdout=None):
        """
        Run the EXE with Popen + shell=True.
        shell=True preserves quotes (e.g. find "Teams").
        Returns a Popen object so the caller can build pipes.
        """
        proc = subprocess.Popen(
            self.build_cmd(args),
            stdin=stdin,
            stdout=stdout,
            text=True,
            shell=True,
        )
        return proc
