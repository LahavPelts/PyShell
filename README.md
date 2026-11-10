# PyShell

A custom shell built in Python for Windows.

## Run

```
python create_test_files.py   # once, to create test files
python shell.py
python shell.py --debug       # shows full tracebacks on errors
```

## Commands

| Command | What it does |
|---------|-------------|
| `help` | list all commands |
| `dir [path] [*.ext] [/s]` | list directory contents |
| `cd [path]` | change directory |
| `set [name[=value]]` | show/set environment variables |
| `type <file>` | print file contents |
| `echo <text>` | print text |
| `md <dir>` | create directory |
| `time` | show current time |
| `cls` | clear screen |
| `exit` | quit |

## Scripts (in MY_PATH)

| Script | What it does |
|--------|-------------|
| `hello.py` | greet the user |
| `hexdump.py <file>` | show file bytes in hex |
| `grep.py <pattern> [file]` | regex search (also works in pipes) |
| `printToScreen.py` | print 10 lines (pipe demo) |
| `countLines.py` | count lines from stdin |

## Examples

```
dir *.txt
dir /s *.py
dir c:\windows\*.log /s > result.txt
printToScreen.py | countLines.py
printToScreen.py | countLines.py > res.txt
ping www.google.com | countLines.py > res.txt
tasklist | find "svchost"
netstat -noa | findstr 127 > a.txt
find "Python" < c:\temp\a.txt
copy a.txt b.txt
hexdump.py shell.py | grep.py "00" | countLines.py
```
