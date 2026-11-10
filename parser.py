__author__ = 'lahav pelts'

"""
parser.py  -  Command line parser
===================================
Responsible for:
  1. Normalizing "smart quotes" (from Word / web) to regular quotes
  2. Splitting a line by | while respecting quoted strings
  3. Extracting stdin (<) and stdout (>) redirects from each segment
  4. Tokenizing each segment while respecting quoted strings
"""

import shlex

# Smart quote characters that need to be normalized
SMART_QUOTES = {
    '“': '"',   # left double quotation mark
    '”': '"',   # right double quotation mark
    '‘': "'",   # left single quotation mark
    '’': "'",   # right single quotation mark
}


def normalize_quotes(text: str) -> str:
    """Replace smart quotes with regular ASCII quotes."""
    for smart, regular in SMART_QUOTES.items():
        text = text.replace(smart, regular)
    return text


def split_by_pipe(text: str) -> list:
    """
    Split a line by | only, ignoring any | that appears inside quotes.

    Example:
      'echo "a|b" | cat'  ->  ['echo "a|b" ', ' cat']
    """
    parts = []
    current = []
    in_quote = False
    quote_char = None

    for c in text:
        if c in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = c
            current.append(c)
        elif in_quote and c == quote_char:
            in_quote = False
            quote_char = None
            current.append(c)
        elif c == '|' and not in_quote:
            parts.append(''.join(current))
            current = []
        else:
            current.append(c)

    parts.append(''.join(current))
    return parts


def _raw_tokenize(text: str) -> list:
    """
    Split a string into tokens while respecting quoted strings.

    Uses posix=False to preserve backslashes in Windows paths
    (e.g. c:\\temp\\file.txt is kept intact).
    Quotes are preserved in the tokens so that external commands
    (like find "Teams") receive them correctly.
    """
    try:
        lex = shlex.shlex(text, posix=False)
        lex.whitespace_split = True
        lex.whitespace = ' \t'
        # posix=False keeps quotes around tokens exactly as the user typed them
        # e.g.  find "Teams"  ->  ['find', '"Teams"']
        # Command classes are responsible for stripping quotes when needed
        return list(lex)
    except ValueError:
        # Fallback: simple whitespace split if shlex fails (e.g. unclosed quotes)
        return text.split()


def parse_segment(segment: str) -> dict:
    """
    Parse a single segment (the part between two | characters).
    Extracts: stdin redirect (<), stdout redirect (>), and command tokens.

    Returns a dict:
      'tokens'  -  list of strings: [command_name, arg1, arg2, ...]
      'stdin'   -  file path string or None
      'stdout'  -  file path string or None
    """
    raw = _raw_tokenize(segment)

    cmd_tokens = []
    stdin_file = None
    stdout_file = None

    i = 0
    while i < len(raw):
        t = raw[i]

        if t == '<' and i + 1 < len(raw):
            stdin_file = raw[i + 1]
            i += 2
            continue
        elif t == '>' and i + 1 < len(raw):
            stdout_file = raw[i + 1]
            i += 2
            continue
        elif t.startswith('<') and len(t) > 1:
            # Support <file.txt (no space after <)
            stdin_file = t[1:]
        elif t.startswith('>') and len(t) > 1:
            # Support >file.txt (no space after >)
            stdout_file = t[1:]
        else:
            cmd_tokens.append(t)

        i += 1

    return {
        'tokens': cmd_tokens,
        'stdin': stdin_file,
        'stdout': stdout_file,
    }


def parse_command_line(line: str) -> list:
    """
    Parse a full command line.
    Returns a list of dicts, one per segment separated by |.

    Example:
      'ping google.com | countLines.py > out.txt'
      ->
      [
        {'tokens': ['ping', 'google.com'], 'stdin': None,  'stdout': None},
        {'tokens': ['countLines.py'],       'stdin': None,  'stdout': 'out.txt'},
      ]
    """
    line = normalize_quotes(line.strip())
    if not line:
        return []

    segments = split_by_pipe(line)
    result = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        parsed = parse_segment(seg)
        if parsed['tokens']:
            result.append(parsed)

    return result
