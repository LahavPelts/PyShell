__author__ = 'lahav pelts'

"""
create_test_files.py  -  Create test files for PyShell demos
=============================================================
Run once before testing:
  python create_test_files.py
"""

import os

def make(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  created: {path}")

print("Creating test files...")

# c:\temp files
make(r"c:\temp\a.txt",
     "Python is a great language\n"
     "Java is also popular\n"
     "I love programming\n"
     "Python 3.12 is fast\n"
     "Hello from PyShell\n")

make(r"c:\temp\hello.txt", "Hello World!\nThis is a test file.\n")
make(r"c:\temp\notes.txt", "Note 1\nNote 2\nNote 3\n")

# Files in the PyShell directory itself
script_dir = os.path.dirname(os.path.abspath(__file__))

make(os.path.join(script_dir, "a.txt"),
     "This is a.txt\n"
     "Line 2\n"
     "Line 3\n")

make(os.path.join(script_dir, "sample.txt"),
     "sample file\npython\njava\n")

print("\nAll files created successfully!")
print("You can now run:  python shell.py")
