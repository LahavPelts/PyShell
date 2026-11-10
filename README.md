# PyShell

A simple Windows shell written in Python.

## Run

```
python create_test_files.py   # once: creates c:\temp\a.txt etc. (WARNING: overwrites ./a.txt)
python shell.py
python shell.py --debug       # also prints full tracebacks on errors
```

## How it works (short version)

1. `parser.py` splits the line: `ping x | countLines.py > res.txt`
   → `[ping x]` piped into `[countLines.py]`, whose output goes to `res.txt`.
2. `Shell.find_command()` finds each command name, in this order:
   internal command → `.py` script in `MY_PATH` → CMD built-in → `.exe` in PATH.
   Names are case-insensitive (`DIR` = `dir`).
3. `Shell.run_line()` starts every command with `Popen` **without waiting**, connecting
   each one's stdout to the next one's stdin. Then it waits for all of them, so the
   commands in a pipe run in parallel.
4. Ctrl+C stops the running command and returns to the prompt. Errors print a short
   message; the shell never crashes.

## Classes (inheritance)

```
Command
├── InternalCommand          runs inside Python, no new process
│   ├── ExitCommand  HelpCommand  SetCommand  CdCommand
│   └── DirCommand  TypeCommand  EchoCommand  MdCommand  TimeCommand
└── ExternalCommand          starts a new process with subprocess.Popen
    ├── ScriptCommand        python.exe script.py ...
    ├── CmdCommand           cmd.exe /c copy ...
    └── ExecutableCommand    ping ..., notepad ...
```

## Internal commands

| Command | What it does |
|---------|-------------|
| `help [command]` | list commands / help for one command |
| `dir [folder][*.ext] [/s] [/b]` | list files (`/s` = sub-folders, `/b` = names only) |
| `cd [path]` | change folder (no argument = show current folder) |
| `set [name[=value]]` | show / set environment variables (`set MY_PATH`) |
| `type <file>` | print a file |
| `echo <text>` | print text |
| `md <folder>` | create a folder |
| `time` | show the current time |
| `exit` | quit |

## Scripts (found through MY_PATH: `scripts/` and `scripts2/`)

| Script | What it does |
|--------|-------------|
| `hello.py` | says hello to the user |
| `hexdump.py <file>` | prints the file's bytes in hex |
| `grep.py <regex> [file]` | prints matching lines (from a file or from a pipe) |
| `printToScreen.py` | prints 10 lines (pipe demo) |
| `countLines.py` | counts lines from stdin |

## Commands to screenshot for the submission

```
help
help dir
DiR *.txt
dir /s *.py
dir /b
dir *.txt > c:\temp\dir_result.txt
dir c:\windows\*.log /s > c:\temp\dir_result.txt
set
set MY_PATH
set USERNAME=Israel
cd scripts
cd ..
type c:\temp\a.txt
time

hello.py
hexdump.py a.txt | grep.py 8F
printToScreen.py | countLines.py
printToScreen.py | countLines.py > res.txt

copy a.txt b.txt

ping www.google.com
ping www.google.com > ping_result.txt
ping www.google.com | countLines.py > res.txt
tasklist | find "Teams"
tasklist | findstr Teams
find "Python" < c:\temp\a.txt
calc
notepad
notepad c:\temp\a.txt
netstat -noa
netstat -noa > a.txt
netstat -noa | find "127"
netstat -noa | findstr 127 > a.txt

# 3 extra examples (pipe, redirect in, redirect out):
find "Python" < c:\temp\a.txt > c:\temp\found.txt
printToScreen.py | grep.py "0[2-4]" | countLines.py
dir /s /b *.py | find "scripts" > c:\temp\scripts_list.txt

# Ctrl+C: run  ping -t 127.0.0.1  and press Ctrl+C. The shell stays open.
```
