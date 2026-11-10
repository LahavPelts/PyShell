"""
commands/base.py  -  Base command classes
==========================================
Command         -  prototype for all commands
InternalCommand -  base for commands that run directly inside the Shell
                   (no subprocess)
"""

import sys


class Command:
    """
    Base class for all commands.

    Every command implements execute(args, stdin, stdout).
    External commands (subprocess) return a Popen object.
    Internal commands return None.
    """

    name: str = ""           # command name, e.g. "dir"
    description: str = ""    # short description shown by help
    usage: str = ""          # usage example shown by help

    def execute(self, args: list, stdin=None, stdout=None):
        """
        Run the command.

        args   - list of argument strings (excluding the command name itself)
        stdin  - file-like object to read from, or None (= sys.stdin)
        stdout - file-like object to write to,  or None (= sys.stdout)

        Returns: subprocess.Popen (external commands) or None (internal commands)
        """
        raise NotImplementedError(f"execute() not implemented in {type(self).__name__}")

    # ── Convenience helpers ──────────────────────────────────────────────────

    def _stdin(self, stdin):
        """Return effective stdin: if None, return sys.stdin."""
        return stdin if stdin is not None else sys.stdin

    def _stdout(self, stdout):
        """Return effective stdout: if None, return sys.stdout."""
        return stdout if stdout is not None else sys.stdout

    @staticmethod
    def _unquote(s: str) -> str:
        """Strip surrounding quotes from a single argument (if present)."""
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
            return s[1:-1]
        return s

    def _clean_args(self, args: list) -> list:
        """
        Strip surrounding quotes from every argument.
        Called by internal commands to get clean paths and strings.
        """
        return [self._unquote(a) for a in args]


class InternalCommand(Command):
    """
    Base class for internal commands.

    Internal commands run directly inside the Shell process (no subprocess).
    They support redirect and pipe through the stdin / stdout parameters.
    """
    pass
