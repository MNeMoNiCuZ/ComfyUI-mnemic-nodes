"""Track which part of a wildcard template produced which part of the output.

Before processing, every "{" and line/document wildcard gets an invisible
source marker holding its offset in the original text. When the processor
resolves a block, wildcard or variable, it wraps the result in open/close
markers carrying a source key. At the end the markers are turned into a tree
of segments for the node's Preview, and stripped from the real output.

Markers use Unicode private-use characters, which never appear in prompts.
Source keys match what the frontend highlighter colors:
  c<offset>  the {…} block starting at <offset>
  w<offset>  the __wildcard__, ___document___, ~~folder~~ or ~~~folder~~~
             starting at <offset>
  v<name>    the variable <name>
A key can be followed by FILE and the path of the wildcard file the text
was picked from, then FILE and the line number in that file.
"""

import re

SOURCE_START = ""
SOURCE_END = ""
OPEN = ""
OPEN_END = ""
CLOSE = ""
FILE = ""

_MARKER_CHARS = SOURCE_START + SOURCE_END + OPEN + OPEN_END + CLOSE
_SOURCE_RE = re.compile(SOURCE_START + r"\d+" + SOURCE_END)
_ANY_MARKER_RE = re.compile(
    "|".join([
        _SOURCE_RE.pattern,
        OPEN + "[^" + OPEN_END + "]*" + OPEN_END,
        CLOSE,
    ])
)
# Underscores name a file, tildes name a folder to pick a random file from.
# Try three characters first so document wildcards cannot become line wildcards.
_WILDCARD_NAME_CHAR = r"[a-zA-Z0-9_./\\*?\[\] -]"
WILDCARD_PATTERN = r"(?P<delimiter>___|__|~~~|~~)(?P<wildcard_name>" + _WILDCARD_NAME_CHAR + r"+?)(?P=delimiter)"
WILDCARD_RE = re.compile(WILDCARD_PATTERN)
WILDCARD_NAME_RE = re.compile(_WILDCARD_NAME_CHAR + "+")

# Regexes the processors use, extended to capture an optional source marker
# in front of the construct. Group 1 is the source offset (or None).
# A ${name} use is not a block: it stays until the variable is defined, which
# can happen later in the run, inside a document.
MARKED_BRACES_RE = re.compile(r"(?<!\$)(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?{((?:\$\{[^{}]*\}|[^{}])*?)}")
# A document wrapper selects a reference before expanding the selected file.
MARKED_DOCUMENT_CHOICE_RE = re.compile(
    r"___(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?{([^{}]*?)}___"
)
# The start of an if{...} block; its end is found by counting braces.
MARKED_CONDITION_START_RE = re.compile(
    r"(?<![a-zA-Z0-9])if(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?{"
)
# A name can be built from ${variables} and {...} blocks, as in
# __people/${location}__. Those resolve first and leave their markers and
# @@MNM_PROTECTED_n@@ tokens in the name; the processor checks the plain name
# against WILDCARD_NAME_RE.
MARKED_WILDCARD_RE = re.compile(
    r"(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?"
    r"(?P<delimiter>___|__|~~~|~~)(?P<wildcard_name>(?:"
    + _WILDCARD_NAME_CHAR + "|" + OPEN + "[^" + OPEN_END + "]*" + OPEN_END + "|" + CLOSE + r"|@@MNM_PROTECTED_\d+@@"
    + r")+?)(?P=delimiter)"
)


def mark_sources(text):
    """Insert a source marker before every "{" (not "${") and file wildcard."""
    wildcard_starts = {m.start() for m in WILDCARD_RE.finditer(text)}
    parts = []
    for i, ch in enumerate(text):
        if (ch == "{" and (i == 0 or text[i - 1] != "$")) or i in wildcard_starts:
            parts.append(f"{SOURCE_START}{i}{SOURCE_END}")
        parts.append(ch)
    return "".join(parts)


def wrap(key, text, file=None, line=None):
    """Wrap resolved text in markers for the given source key, and the file and line it came from."""
    if file:
        key = f"{key}{FILE}{file}"
        if line:
            key = f"{key}{FILE}{line}"
    return f"{OPEN}{key}{OPEN_END}{text}{CLOSE}"


def strip_markers(text):
    """Remove every marker, leaving the plain text."""
    if not isinstance(text, str) or not any(c in text for c in _MARKER_CHARS):
        return text
    return _ANY_MARKER_RE.sub("", text)


def build_segments(marked):
    """Turn marked output into a list of segments for the Preview.

    Each segment is either {"text": str} or {"key": str, "children": [...]},
    with "file" added when the text was picked from a wildcard file, and
    "line" (1-based) when it was one line of that file.
    Unbalanced markers are ignored.
    """
    text = _SOURCE_RE.sub("", marked)
    root = []
    stack = [root]
    buffer = []

    def flush():
        if buffer:
            stack[-1].append({"text": "".join(buffer)})
            buffer.clear()

    i = 0
    while i < len(text):
        ch = text[i]
        if ch == OPEN:
            end = text.find(OPEN_END, i + 1)
            if end == -1:
                i += 1
                continue
            flush()
            key, _, origin = text[i + 1:end].partition(FILE)
            file, _, line = origin.partition(FILE)
            node = {"key": key, "children": []}
            if file:
                node["file"] = file
            if line:
                node["line"] = int(line)
            stack[-1].append(node)
            stack.append(node["children"])
            i = end + 1
            continue
        if ch == CLOSE:
            flush()
            if len(stack) > 1:
                stack.pop()
            i += 1
            continue
        if ch not in _MARKER_CHARS:
            buffer.append(ch)
        i += 1
    flush()
    return root


class InnerMatch:
    """A match-like view of a marked match without its source marker.

    The processors' evaluate functions read match.group(0) (the whole
    construct) and match.group(1) (its contents). This gives them the same
    values they got before markers existed.
    """

    def __init__(self, match, prefix, suffix, content_group=2):
        self._inner = match.group(content_group)
        self._whole = f"{prefix}{self._inner}{suffix}"

    def group(self, index=0):
        return self._whole if index == 0 else self._inner
