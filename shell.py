"""
shell.py  -  PyShell: main Shell manager
==========================================
Entry point. Run with:  python shell.py

Architecture:
  Shell          -  main class: loop, parsing, execution
  |-- parser.py  -  command line parser (pipes, redirects, quotes)
  +-- commands/  -  command class hierarchy
      |-- base.py      Command, InternalCommand
      |-- internal.py  ExitCommand, HelpCommand, SetCommand, CdCommand,
      |                DirCommand, EchoCommand, TypeCommand, ClsCommand,
      |                MdCommand, TimeCommand
      +-- external.py  ScriptCommand, CmdCommand, ExecutableCommand

Command resolution order:
  1. Internal command (runs inside Python)
  2. .py script found in MY_PATH directories
  3. CMD built-in command (shell=True -> cmd.exe /c)
  4. External EXE (Windows PATH)
"""

import os
import sys
import threading
import traceback
import subprocess
import datetime

from parser import parse_command_line
from commands import (
    InternalCommand,
    ExitCommand, HelpCommand, SetCommand, CdCommand,
    DirCommand, EchoCommand, TypeCommand, ClsCommand,
    MdCommand, TimeCommand,
    ScriptCommand, CmdCommand, ExecutableCommand,
)

# Set DEBUG = True (or run with --debug) to print full tracebacks on errors
DEBUG = False

# CMD built-in commands that are not implemented internally.
# These need shell=True so cmd.exe can resolve them.
CMD_BUILTINS = {
    'copy', 'xcopy', 'ren', 'rename', 'move', 'del', 'erase',
    'rd', 'rmdir', 'ver', 'vol', 'color', 'title', 'attrib',
    'assoc', 'ftype', 'pushd', 'popd', 'mklink',
}


# ══════════════════════════════════════════════════════════════════
class Shell:
    """
    Main Shell class.

    Responsibilities:
      - Input loop (REPL: Read-Eval-Print-Loop)
      - Command type resolution (internal / script / cmd / exe)
      - Pipeline execution with true parallelism
      - stdin and stdout redirect
      - Ctrl+C handling and error recovery
    """

    def __init__(self):
        # MY_PATH: semicolon-separated list of directories to search for scripts.
        # Stored as an environment variable so 'set MY_PATH' can read/change it.
        shell_dir = os.path.dirname(os.path.abspath(__file__))
        initial_my_path = os.pathsep.join([
            os.path.join(shell_dir, 'scripts'),
            os.path.join(shell_dir, 'scripts2'),
        ])
        os.environ.setdefault('MY_PATH', initial_my_path)

        # Register all internal commands in a dict keyed by name
        self._internal_commands = {}
        for cls in [ExitCommand, HelpCommand, SetCommand, CdCommand,
                    DirCommand, EchoCommand, TypeCommand, ClsCommand,
                    MdCommand, TimeCommand]:
            cmd = cls()
            self._internal_commands[cmd.name] = cmd

        # Give HelpCommand access to the full registry so it can list commands
        HelpCommand.registry = self._internal_commands

        # Command counter used in the prompt
        self._cmd_count = 0

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ══════════════════════════════════════════════════════════════════════════

    def run(self):
        """Main loop: show prompt, read a line, execute it."""
        print("Welcome to PyShell! Type 'help' for commands, 'exit' to quit.")
        while True:
            try:
                line = input(self._make_prompt())
            except KeyboardInterrupt:
                # Ctrl+C while waiting for input - do NOT exit the shell
                print()
                continue
            except EOFError:
                # Ctrl+D / end of input stream
                print("\nGoodbye!")
                break

            line = line.strip()
            if not line:
                continue

            self._cmd_count += 1

            try:
                self._execute_line(line)
            except SystemExit:
                # exit command called sys.exit() - let it propagate
                raise
            except Exception as e:
                self._handle_error(e)

    def _make_prompt(self) -> str:
        """Build the custom prompt: directory, username, time, command number."""
        cwd = os.getcwd()
        user = os.environ.get('USERNAME', os.environ.get('USER', 'user'))
        now = datetime.datetime.now().strftime("%H:%M")
        return f"[{now}] {user}@PyShell #{self._cmd_count}  {cwd}\n> "

    # ══════════════════════════════════════════════════════════════════════════
    # EXECUTION PIPELINE
    # ══════════════════════════════════════════════════════════════════════════

    def _execute_line(self, line: str):
        """Parse and execute one command line."""
        segments = parse_command_line(line)
        if not segments:
            return

        if len(segments) == 1:
            # Single command (may have redirects)
            self._execute_single(segments[0])
        else:
            # Pipeline: multiple commands connected by |
            self._execute_pipeline(segments)

    # ─────────────────────────────────────────────────────────────────────────
    # SINGLE COMMAND (no pipe)
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_single(self, segment: dict):
        """
        Run a single command with redirect support.
        segment = {'tokens': [...], 'stdin': ..., 'stdout': ...}
        """
        tokens = segment['tokens']
        stdin_file = segment['stdin']
        stdout_file = segment['stdout']

        cmd_obj = self._resolve_command(tokens[0])
        args = tokens[1:]

        # Open redirect files
        f_in  = open(stdin_file,  'r', encoding='utf-8', errors='replace') if stdin_file  else None
        f_out = open(stdout_file, 'w', encoding='utf-8')                   if stdout_file else None

        try:
            result = cmd_obj.execute(args, stdin=f_in, stdout=f_out)

            if result is not None:
                # External process - wait for it to finish
                try:
                    result.wait()
                except KeyboardInterrupt:
                    result.terminate()
                    result.wait()
                    print("\n[Stopped by user]")
        finally:
            if f_in:
                f_in.close()
            if f_out:
                f_out.close()

    # ─────────────────────────────────────────────────────────────────────────
    # PIPELINE  (connecting commands with |)
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_pipeline(self, segments: list):
        """
        Run a pipeline of commands in parallel.

        How it works:
          - External commands (Popen): stdout=subprocess.PIPE -> next command's stdin.
            All subprocess instances start before any of them finishes (true parallelism).
          - Internal commands: os.pipe() + thread for writing; the read-end is passed
            to the next command as its stdin.

        Important: we close the read-end of each pipe in the PARENT process after
        passing it to the child. This ensures EOF is sent when the writing end closes.

        Redirects:
          <  - only valid on the first segment
          >  - only valid on the last segment
        """
        n = len(segments)
        processes  = []   # Popen objects (external commands)
        threads    = []   # Thread objects (internal commands)
        open_files = []   # all opened files that must be closed at the end

        prev_read = None  # read-end of the pipe from the previous command

        for i, seg in enumerate(segments):
            is_last = (i == n - 1)
            tokens  = seg['tokens']

            cmd_obj = self._resolve_command(tokens[0])
            args    = tokens[1:]

            # ── stdin ─────────────────────────────────────────────────────
            if i == 0 and seg['stdin']:
                # < redirect on the first command
                f = open(seg['stdin'], 'r', encoding='utf-8', errors='replace')
                open_files.append(f)
                eff_stdin = f
            else:
                eff_stdin = prev_read  # None if first command with no redirect

            # ── stdout ────────────────────────────────────────────────────
            if is_last and seg['stdout']:
                # > redirect on the last command
                f = open(seg['stdout'], 'w', encoding='utf-8')
                open_files.append(f)
                eff_stdout_file = f
            else:
                eff_stdout_file = None  # None = terminal (last) or PIPE (middle)

            # ── Execute ───────────────────────────────────────────────────
            if isinstance(cmd_obj, InternalCommand):
                # Internal command: run in a thread using os.pipe()
                if not is_last:
                    r_fd, w_fd = os.pipe()
                    r_file = os.fdopen(r_fd, 'r', encoding='utf-8', errors='replace')
                    w_file = os.fdopen(w_fd, 'w', encoding='utf-8')
                else:
                    r_file = None
                    w_file = eff_stdout_file  # None -> sys.stdout

                # Capture loop variables to avoid closure bugs inside a loop
                _cmd, _args, _sin, _sout = cmd_obj, args, eff_stdin, w_file

                def _run_internal(c=_cmd, a=_args, s_in=_sin, s_out=_sout):
                    try:
                        c.execute(a, stdin=s_in, stdout=s_out)
                    finally:
                        # Close the write-end to send EOF to the next command
                        if s_out is not None:
                            try:
                                s_out.close()
                            except Exception:
                                pass
                        # Close the stdin (read-end of the previous pipe)
                        if s_in is not None:
                            try:
                                s_in.close()
                            except Exception:
                                pass

                t = threading.Thread(target=_run_internal, daemon=True)
                t.start()
                threads.append(t)

                if not is_last:
                    prev_read = r_file
                else:
                    prev_read = None

            else:
                # External command: Popen  (ScriptCommand / CmdCommand / ExecutableCommand)
                if not is_last:
                    popen_stdout = subprocess.PIPE
                elif eff_stdout_file:
                    popen_stdout = eff_stdout_file
                else:
                    popen_stdout = None  # -> terminal

                try:
                    # Call execute() which creates Popen with the right settings
                    proc = cmd_obj.execute(args, stdin=eff_stdin, stdout=popen_stdout)

                    if proc is None:
                        # Command not found (_NotFoundCommand returns None)
                        prev_read = None
                    else:
                        processes.append(proc)

                        # Close the read-end in the parent after the child inherited it.
                        # This is required so the child receives EOF when writing ends.
                        if eff_stdin is not None and eff_stdin not in open_files:
                            try:
                                eff_stdin.close()
                            except Exception:
                                pass

                        prev_read = proc.stdout if not is_last else None

                except (FileNotFoundError, OSError) as e:
                    print(f"Error: command '{tokens[0]}' not found. ({e})", file=sys.stderr)
                    prev_read = None

        # ── Wait for everyone to finish ───────────────────────────────────────
        try:
            for proc in processes:
                proc.wait()
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            for proc in processes:
                try:
                    proc.terminate()
                except Exception:
                    pass
            print("\n[Pipeline stopped]")

        # ── Close all opened files ────────────────────────────────────────────
        for f in open_files:
            try:
                f.close()
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════════
    # COMMAND RESOLUTION  -  determine command type by priority
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve_command(self, name: str):
        """
        Return the appropriate Command object for the given name.
        Priority order:
          1. Internal command
          2. .py script in MY_PATH
          3. CMD built-in  (shell=True -> cmd.exe /c)
          4. External EXE  (Windows PATH)
        """
        lower = name.lower()

        # 1. Internal command?
        if lower in self._internal_commands:
            return self._internal_commands[lower]

        # 2. Python script? (ends with .py)
        if lower.endswith('.py'):
            script_path = self._find_script(name)
            if script_path:
                return ScriptCommand(script_path)
            # Not found in MY_PATH - try as a direct path
            if os.path.isfile(name):
                return ScriptCommand(name)
            # Not found anywhere
            return _NotFoundCommand(name)

        # 3. CMD built-in?
        if lower in CMD_BUILTINS:
            return CmdCommand(lower)

        # 4. External EXE (subprocess will search the PATH)
        return ExecutableCommand(name)

    def _find_script(self, script_name: str) -> str | None:
        """
        Search for a Python script in MY_PATH directories, in order.
        Returns the full path if found, otherwise None.
        """
        my_path = os.environ.get('MY_PATH', '')
        dirs = my_path.split(os.pathsep)
        for d in dirs:
            full = os.path.join(d, script_name)
            if os.path.isfile(full):
                return full
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ERROR HANDLING
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_error(self, exc: Exception):
        """Print a friendly error message. In DEBUG mode also print traceback."""
        print(f"Error: {exc}", file=sys.stderr)
        if DEBUG:
            traceback.print_exc()


# ══════════════════════════════════════════════════════════════════
# NOT-FOUND COMMAND  -  placeholder for unknown .py scripts
# ══════════════════════════════════════════════════════════════════
class _NotFoundCommand:
    """Returned when a .py script cannot be located anywhere in MY_PATH."""

    def __init__(self, name):
        self.name = name

    def execute(self, args, stdin=None, stdout=None):
        print(f"'{self.name}': script not found in MY_PATH.", file=sys.stderr)
        return None

    def build_cmd(self, args):
        return []


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Enable debug mode with:  python shell.py --debug
    if '--debug' in sys.argv:
        DEBUG = True
        print("[DEBUG mode enabled]")

    shell = Shell()
    try:
        shell.run()
    except SystemExit:
        pass  # normal exit via the 'exit' command
    except KeyboardInterrupt:
        print("\nGoodbye!")
