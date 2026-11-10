"""
hello.py  -  Simple greeting script
=====================================
Usage:  hello.py
"""

import os

username = os.environ.get('USERNAME', os.environ.get('USER', 'World'))
print(f"Hello, {username}!")
print("Welcome to PyShell :)")
