"""
printToScreen.py  -  Print several lines to the screen
========================================================
Usage:  printToScreen.py

Designed to test pipes:
  printToScreen.py | countLines.py
  printToScreen.py | countLines.py > res.txt
"""

import sys

lines = [
    "Line 01 - Hello World",
    "Line 02 - Python is great",
    "Line 03 - Testing PyShell",
    "Line 04 - Pipe test",
    "Line 05 - Almost done",
    "Line 06 - Redirects work!",
    "Line 07 - subprocess.Popen",
    "Line 08 - Running in parallel",
    "Line 09 - stdin / stdout",
    "Line 10 - The end.",
]

for line in lines:
    print(line)
    sys.stdout.flush()  # flush immediately so data flows to the next pipe stage
