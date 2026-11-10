__author__ = 'lahav pelts'

"""
commands/internal.py  -  Internal commands
===========================================
All internal Shell commands - executed directly inside Python,
without spawning any external process.

Each class inherits from InternalCommand and implements execute().
Output is written to stdout (which may be a file, a pipe, or sys.stdout).
"""

import os
import sys
import datetime
import fnmatch

from .base import InternalCommand


# ══════════════════════════════════════════════════════════════════
# EXIT
# ══════════════════════════════════════════════════════════════════
class ExitCommand(InternalCommand):
    name = "exit"
    description = "Exit the shell"
    usage = "exit"

    def execute(self, args, stdin=None, stdout=None):
        print("Goodbye!", file=self._stdout(stdout))
        sys.exit(0)


# ══════════════════════════════════════════════════════════════════
# ECHO
# ══════════════════════════════════════════════════════════════════
class EchoCommand(InternalCommand):
    name = "echo"
    description = "Print text to the screen"
    usage = "echo [text...]"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)
        print(' '.join(args), file=out)


# ══════════════════════════════════════════════════════════════════
# TIME
# ══════════════════════════════════════════════════════════════════
class TimeCommand(InternalCommand):
    name = "time"
    description = "Display the current time"
    usage = "time"

    def execute(self, args, stdin=None, stdout=None):
        out = self._stdout(stdout)
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"Current time: {now}", file=out)


# ══════════════════════════════════════════════════════════════════
# CD
# ══════════════════════════════════════════════════════════════════
class CdCommand(InternalCommand):
    name = "cd"
    description = "Change the current directory"
    usage = "cd [path]"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)
        if not args:
            # No arguments: print the current directory
            print(os.getcwd(), file=out)
            return
        path = args[0]
        try:
            os.chdir(path)
        except FileNotFoundError:
            print(f"cd: path not found: {path}", file=sys.stderr)
        except PermissionError:
            print(f"cd: permission denied: {path}", file=sys.stderr)
        except OSError as e:
            print(f"cd: error: {e}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════
# SET
# ══════════════════════════════════════════════════════════════════
class SetCommand(InternalCommand):
    """
    Manage environment variables - including MY_PATH (script search dirs).

    Usage:
      set              - display all environment variables
      set PATH         - display variables whose name starts with PATH
      set NAME=value   - define / update a variable
    """
    name = "set"
    description = "Display or set environment variables"
    usage = "set [name] | set name=value"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)

        if not args:
            # Print all environment variables, sorted
            for key, val in sorted(os.environ.items()):
                print(f"{key}={val}", file=out)
            return

        arg = ' '.join(args)

        if '=' in arg:
            # set KEY=VALUE  ->  define variable
            key, _, value = arg.partition('=')
            key = key.strip()
            os.environ[key] = value
            print(f"Set: {key}={value}", file=out)
        else:
            # set KEY  ->  show variables whose name starts with KEY (case-insensitive)
            key = arg.strip().upper()
            found = False
            for env_key, env_val in sorted(os.environ.items()):
                if env_key.upper().startswith(key):
                    print(f"{env_key}={env_val}", file=out)
                    found = True
            if not found:
                print(f"set: variable '{arg.strip()}' not found", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════
# TYPE
# ══════════════════════════════════════════════════════════════════
class TypeCommand(InternalCommand):
    name = "type"
    description = "Display the contents of a text file"
    usage = "type <file>"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)
        if not args:
            print("type: a filename is required", file=sys.stderr)
            return
        path = args[0]
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                out.write(f.read())
        except FileNotFoundError:
            print(f"type: file not found: '{path}'", file=sys.stderr)
        except PermissionError:
            print(f"type: permission denied: '{path}'", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════
# MD
# ══════════════════════════════════════════════════════════════════
class MdCommand(InternalCommand):
    name = "md"
    description = "Create a new directory (like mkdir)"
    usage = "md <directory-name>"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)
        if not args:
            print("md: a directory name is required", file=sys.stderr)
            return
        path = args[0]
        try:
            os.makedirs(path, exist_ok=True)
            print(f"Directory '{path}' created.", file=out)
        except PermissionError:
            print(f"md: permission denied: '{path}'", file=sys.stderr)
        except OSError as e:
            print(f"md: error: {e}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════
# DIR
# ══════════════════════════════════════════════════════════════════
class DirCommand(InternalCommand):
    """
    List the files in a folder (written in Python, no cmd.exe).

    Flags:
      /s  - also look inside all sub-folders
      /b  - bare format: names only (no date / size)

    Examples:
      dir            dir *.txt          dir /s *.py
      dir /b         dir c:\\windows\\*.log /s
    """
    name = "dir"
    description = "List directory contents"
    usage = "dir [folder][*.pattern] [/s] [/b]"

    def execute(self, args, stdin=None, stdout=None):
        out = self._stdout(stdout)
        recursive = False
        bare = False
        folder = "."
        pattern = "*"

        # 1. Read the arguments (any order)
        for a in self._clean_args(args):
            if a.lower() == "/s":
                recursive = True
            elif a.lower() == "/b":
                bare = True
            elif "*" in a or "?" in a or os.path.isfile(a):            # c:\windows\*.log
                folder = os.path.dirname(a) or "."
                pattern = os.path.basename(a)
            else:                                   # c:\windows
                folder = a

        if not os.path.isdir(folder):
            print(f"dir: folder not found: {folder}", file=sys.stderr)
            return

        # 2. Which folders to list: just this one, or (with /s) all sub-folders too
        if recursive:
            folders = [root for root, dirs, files in os.walk(folder)]
        else:
            folders = [folder]

        # 3. List them
        count = 0
        for f in folders:
            count += self.list_folder(f, pattern, bare, recursive, out)
        if not bare:
            print(f"\n  {count} item(s) found", file=out)

    def list_folder(self, folder, pattern, bare, full_path, out):
        """Print the entries of ONE folder that match the pattern. Returns how many."""
        try:
            names = sorted(os.listdir(folder))
        except OSError:                             # e.g. access denied
            return 0
        names = [n for n in names if fnmatch.fnmatch(n.lower(), pattern.lower())]
        if not names:
            return 0                                # skip empty folders, like cmd

        if not bare:
            print(f"\n Directory of {os.path.abspath(folder)}\n", file=out)
        for name in names:
            path = os.path.join(folder, name)
            if bare:
                print(os.path.abspath(path) if full_path else name, file=out)
                continue
            try:
                info = os.stat(path)
            except OSError:
                continue
            date = datetime.datetime.fromtimestamp(info.st_mtime).strftime("%d/%m/%Y  %H:%M")
            size = "<DIR>" if os.path.isdir(path) else f"{info.st_size:,}"
            print(f"{date}  {size:>14}  {name}", file=out)
        return len(names)


# ══════════════════════════════════════════════════════════════════
# HELP
# ══════════════════════════════════════════════════════════════════
class HelpCommand(InternalCommand):
    """
    Display a list of available commands, or detailed help for one command.
    The Shell assigns the registry after initialization.
    """
    name = "help"
    description = "Show help for commands"
    usage = "help [command-name]"

    # The Shell sets this to the dict of all internal commands
    registry: dict = {}

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)

        if not args:
            print("=" * 58, file=out)
            print("  PyShell  -  Available internal commands", file=out)
            print("=" * 58, file=out)
            for cmd_name in sorted(self.registry):
                cmd = self.registry[cmd_name]
                print(f"  {cmd_name:<12}  {cmd.description}", file=out)
            print("\nTip: help <command>  for detailed help", file=out)
        else:
            name = args[0].lower()
            if name in self.registry:
                cmd = self.registry[name]
                print(f"\nCommand : {cmd.name}", file=out)
                print(f"Desc    : {cmd.description}", file=out)
                print(f"Usage   : {cmd.usage}", file=out)
            else:
                print(f"help: command '{name}' not found.", file=sys.stderr)
