__author__ = 'lahav pelts'

"""
countLines.py  -  Read from stdin and count lines
===================================================
Usage:  countLines.py              (inside a pipe)
         ... | countLines.py
         ... | countLines.py > out.txt

Note: reads from stdin only, not from a file.
      This demonstrates reading from STDIN in a pipe.

Examples:
  printToScreen.py | countLines.py
  ping www.google.com | countLines.py
  netstat -noa | countLines.py > a.txt
"""

import sys

count = 0
try:
    for line in sys.stdin:
        count += 1
except KeyboardInterrupt:
    pass  # Ctrl+C: stop reading and print what we counted so far

print(f"Total lines: {count}")
