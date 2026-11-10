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
for line in sys.stdin:
    count += 1

print(f"Total lines: {count}")
