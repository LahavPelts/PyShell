__author__ = 'lahav pelts'

"""
shell.py  -  PyShell: a simple Windows shell written in Python
===============================================================
Run with:   python shell.py          (add --debug to see full error tracebacks)

Files:
  shell.py             - the Shell class: prompt loop, finding commands, running them
  parser.py            - splits a line into commands, | pipes, < and > redirects
  commands/base.py     - Command, InternalCommand        (parent classes)
  commands/internal.py - exit, help, set, cd, dir, type, echo, md, time
  commands/external.py - ScriptCommand, CmdCommand, ExecutableCommand

How a command name is found (in this order):
  1. Internal command   (dir, cd, set...)  -> runs inside Python, no new process
  2. Python script      (hello.py / hello) -> searched in the MY_PATH folders
  3. CMD built-in       (copy, ren...)     -> runs with  cmd.exe /c
  4. Program            (ping, notepad...) -> Windows finds the .exe in PATH
"""

import os
import sys
import shutil
import tempfile
import datetime
import traceback
import subprocess

from parser import parse_command_line
from commands import (
    InternalCommand,
    ExitCommand, HelpCommand, SetCommand, CdCommand,
    DirCommand, EchoCommand, TypeCommand, MdCommand, TimeCommand,
    ScriptCommand, CmdCommand, ExecutableCommand,
)

DEBUG = False   # True = print full tracebacks (python shell.py --debug)

# Commands that exist only inside cmd.exe (there is no .exe file for them)
CMD_COMMANDS = ["copy", "ren", "rename", "move", "del", "erase", "rd", "rmdir",
                "mkdir", "cls", "ver", "vol", "title", "color", "start", "date"]


class Shell:

    def __init__(self):
        # MY_PATH = our own "PATH": the folders where we look for .py scripts.
        # It is an environment variable, so  'set MY_PATH'  shows / changes it.
        here = os.path.dirname(os.path.abspath(__file__))
        os.environ.setdefault("MY_PATH", os.pathsep.join([
            os.path.join(here, "scripts"),
            os.path.join(here, "scripts2"),
        ]))

        # All internal commands, by name:  {"dir": DirCommand(), ...}
        self.internal_commands = {}
        for cls in [ExitCommand, HelpCommand, SetCommand, CdCommand, DirCommand,
                    EchoCommand, TypeCommand, MdCommand, TimeCommand]:
            self.internal_commands[cls.name] = cls()
        HelpCommand.registry = self.internal_commands   # so 'help' can list them

        self.count = 0   # number of commands run (shown in the prompt)

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------
    def run(self):
        print("Welcome to PyShell! Type 'help' for commands, 'exit' to quit.")
        while True:
            try:
                line = input(self.prompt()).strip()
                if line:
                    self.count += 1
                    self.run_line(line)
            except KeyboardInterrupt:
                # Ctrl+C: stop the current command but stay in the shell
                print("\n[Stopped]")
            except EOFError:
                # End of input (Ctrl+Z, or the input file ended)
                print("\nGoodbye!")
                break
            except Exception as e:
                # Any other error: print a short message, the shell does NOT crash
                print(f"Error: {e}", file=sys.stderr)
                if DEBUG:
                    traceback.print_exc()

    def prompt(self):
        """Prompt with the time, user name, command number and current folder."""
        user = os.environ.get("USERNAME", "user")
        now = datetime.datetime.now().strftime("%H:%M")
        return f"[{now}] {user}@PyShell #{self.count}  {os.getcwd()}\n> "

    # ------------------------------------------------------------------
    # RUN ONE LINE  (a single command is just a pipeline with one part)
    # ------------------------------------------------------------------
    def run_line(self, line):
        parts = parse_command_line(line)
        # parts = [{'tokens': ['ping', 'x'], 'stdin': None, 'stdout': None}, ...]

        # 1. Find the command object of every part BEFORE starting anything.
        #    If one is missing we stop now (nothing is left half-running).
        commands = []
        for part in parts:
            cmd = self.find_command(part["tokens"][0])
            if cmd is None:
                return
            commands.append(cmd)

        processes = []    # the Popen objects we started
        open_files = []   # files we opened, to close at the end
        prev_output = None  # output of the previous command = input of the next

        try:
            # 2. Start every command, connecting each one to the next.
            for i, cmd in enumerate(commands):
                part = parts[i]
                args = part["tokens"][1:]
                is_last = (i == len(commands) - 1)

                # Where does this command READ from?
                stdin = prev_output                 # previous command in the pipe
                if part["stdin"]:                   # ... or a  < file
                    stdin = open(part["stdin"], "r")
                    open_files.append(stdin)

                # Where does this command WRITE to?
                if part["stdout"]:                  # a  > file
                    stdout = open(part["stdout"], "w")
                    open_files.append(stdout)
                elif is_last:
                    stdout = None                   # the screen
                else:
                    stdout = subprocess.PIPE        # the next command in the pipe

                if isinstance(cmd, InternalCommand):
                    prev_output = self.run_internal(cmd, args, stdout, open_files)
                else:
                    proc = cmd.execute(args, stdin=stdin, stdout=stdout)
                    processes.append(proc)
                    prev_output = proc.stdout       # None unless stdout was PIPE

                # The child process now has its own copy of the pipe,
                # so the shell closes its copy (this is how EOF reaches the reader).
                if stdin is not None and stdin not in open_files:
                    stdin.close()

            # 3. All commands are running IN PARALLEL. Now wait for them all.
            for proc in processes:
                proc.wait()

        except KeyboardInterrupt:
            # Ctrl+C: kill what is still running, then go back to the prompt
            for proc in processes:
                proc.kill()
            print("\n[Stopped]")
        finally:
            for f in open_files:
                f.close()

    def run_internal(self, cmd, args, stdout, open_files):
        """
        Run an internal command. If its output must go into a pipe, we write it
        to a temporary file and give that file to the next command as its stdin.
        """
        if stdout is subprocess.PIPE:
            temp = tempfile.TemporaryFile("w+")
            open_files.append(temp)
            cmd.execute(args, stdout=temp)
            temp.seek(0)          # rewind, so the next command reads from the start
            return temp
        cmd.execute(args, stdout=stdout)
        return None

    # ------------------------------------------------------------------
    # FINDING A COMMAND
    # ------------------------------------------------------------------
    def find_command(self, name):
        """Return the right Command object for this name, or None if not found."""
        lower = name.lower()   # commands are case-insensitive: DIR = dir = Dir

        # 1. Internal command
        if lower in self.internal_commands:
            return self.internal_commands[lower]

        # 2. Python script: search the MY_PATH folders, one by one.
        #    "hexdump.py" and just "HexDump" both find hexdump.py
        script_name = name if lower.endswith(".py") else name + ".py"
        for folder in os.environ.get("MY_PATH", "").split(os.pathsep):
            path = os.path.join(folder, script_name)
            if os.path.isfile(path):
                return ScriptCommand(name, path)
        if lower.endswith(".py"):
            print(f"'{name}': script not found in MY_PATH", file=sys.stderr)
            return None

        # 3. CMD built-in command
        if lower in CMD_COMMANDS:
            return CmdCommand(lower)

        # 4. A program (.exe). We only CHECK that it exists here;
        #    Popen itself finds it in the current folder / PATH when it runs.
        if shutil.which(name):
            return ExecutableCommand(name)

        print(f"'{name}' is not recognized as a command", file=sys.stderr)
        return None


if __name__ == "__main__":
    if "--debug" in sys.argv:
        DEBUG = True
    try:
        Shell().run()
    except SystemExit:
        pass   # the 'exit' command was used
