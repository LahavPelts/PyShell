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
        args = self._clean_args(args)
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
# CLS
# ══════════════════════════════════════════════════════════════════
class ClsCommand(InternalCommand):
    name = "cls"
    description = "Clear the screen"
    usage = "cls"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        os.system('cls')


# ══════════════════════════════════════════════════════════════════
# TIME
# ══════════════════════════════════════════════════════════════════
class TimeCommand(InternalCommand):
    name = "time"
    description = "Display the current time"
    usage = "time"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
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
    List directory contents - implemented with os.listdir / os.walk.

    Flags:
      /s          - recursive (include subdirectories)

    Pattern:
      *.txt, *.exe  - filter by extension

    Path:
      c:\\windows         - specific directory
      c:\\windows\\*.log  - directory + pattern

    Examples:
      dir
      dir *.txt
      dir /s
      dir /s *.exe
      dir c:\\windows\\*.log /s
    """
    name = "dir"
    description = "List directory contents"
    usage = "dir [path] [*.pattern] [/s]"

    def execute(self, args, stdin=None, stdout=None):
        args = self._clean_args(args)
        out = self._stdout(stdout)

        recursive = False
        pattern = '*'
        search_path = '.'

        remaining = []
        for a in args:
            if a.lower() == '/s':
                recursive = True
            else:
                remaining.append(a)

        if remaining:
            arg = remaining[0]
            # If the path contains a wildcard, split into directory and pattern
            if '*' in arg or '?' in arg:
                search_path = os.path.dirname(arg) or '.'
                pattern = os.path.basename(arg)
            else:
                search_path = arg

        if not os.path.exists(search_path):
            print(f"dir: path not found: '{search_path}'", file=sys.stderr)
            return

        def print_one_dir(path, pat):
            """Print the contents of a single directory."""
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                print(f"\n  [access denied: {path}]", file=out)
                return

            print(f"\n Directory: {os.path.abspath(path)}\n", file=out)
            dirs_count = 0
            files_count = 0
            total_size = 0

            for entry in entries:
                full_path = os.path.join(path, entry)
                is_dir = os.path.isdir(full_path)

                # Pattern filter: directories are always shown, files are filtered
                if not is_dir and not fnmatch.fnmatch(entry.lower(), pat.lower()):
                    continue

                try:
                    st = os.stat(full_path)
                    mtime = datetime.datetime.fromtimestamp(st.st_mtime)
                    mtime_str = mtime.strftime("%d/%m/%Y  %H:%M")

                    if is_dir:
                        dirs_count += 1
                        print(f"{mtime_str}    <DIR>          {entry}", file=out)
                    else:
                        size = st.st_size
                        files_count += 1
                        total_size += size
                        print(f"{mtime_str}    {size:>14,}  {entry}", file=out)
                except OSError:
                    print(f"  [error accessing: {entry}]", file=out)

            print(f"\n  {files_count} file(s)  |  {dirs_count} dir(s)  |  {total_size:,} bytes", file=out)

        if recursive:
            for root, dirs, files in os.walk(search_path):
                print_one_dir(root, pattern)
        else:
            print_one_dir(search_path, pattern)


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
