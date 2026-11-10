"""
hexdump.py  -  Display every byte of a binary file in hexadecimal
==================================================================
Usage:  hexdump.py <file-path>

Sample output:
  00000000: 4D 5A 90 00 03 00 00 00  04 00 00 00 FF FF 00 00  |MZ..............|
  (each row: offset, 16 bytes in hex, printable character view)
"""

import sys
import os


def hexdump(filepath: str):
    """Print a hexdump of the given file."""
    if not os.path.isfile(filepath):
        print(f"hexdump: file not found: '{filepath}'", file=sys.stderr)
        return

    with open(filepath, 'rb') as f:
        data = f.read()

    bytes_per_row = 16
    for offset in range(0, len(data), bytes_per_row):
        chunk = data[offset:offset + bytes_per_row]

        # Offset column
        offset_str = f"{offset:08X}"

        # Hex columns: 16 bytes split into two groups of 8
        hex_left  = ' '.join(f"{b:02X}" for b in chunk[:8])
        hex_right = ' '.join(f"{b:02X}" for b in chunk[8:])
        # Pad to a fixed width for partial last row
        hex_left  = hex_left.ljust(8 * 3 - 1)
        hex_right = hex_right.ljust(8 * 3 - 1)

        # Printable character column: show '.' for non-printable bytes
        printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

        print(f"{offset_str}: {hex_left}  {hex_right}  |{printable}|")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: hexdump.py <file-path>", file=sys.stderr)
        sys.exit(1)

    hexdump(sys.argv[1])
