"""
grep.py  -  Regex search in a file or stdin
=============================================
Usage:
  grep.py <pattern> [file]   -  read from a file
  grep.py <pattern>           -  read from stdin (use in a pipe)

Examples:
  grep.py Python c:\\temp\\a.txt
  hexdump.py shell.py | grep.py F8
  tasklist | grep.py python

Unlike findstr, this supports full Python regex syntax.
"""

import sys
import re


def grep(pattern: str, lines):
    """
    Print lines that contain a match for the pattern.
    lines: any iterable of strings
    """
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"grep: invalid regex: {e}", file=sys.stderr)
        sys.exit(1)

    found = 0
    for line in lines:
        line = line.rstrip('\n').rstrip('\r')
        if regex.search(line):
            print(line)
            found += 1

    return found


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: grep.py <pattern> [file]", file=sys.stderr)
        sys.exit(1)

    pattern = sys.argv[1]

    if len(sys.argv) >= 3:
        # Read from a file
        filepath = sys.argv[2]
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                grep(pattern, f)
        except FileNotFoundError:
            print(f"grep: file not found: '{filepath}'", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin (pipe mode)
        grep(pattern, sys.stdin)
