"""Track which part of a wildcard template produced which part of the output.

Before processing, every "{" and "__name__" in the template gets an invisible
source marker holding its offset in the original text. When the processor
resolves a block, wildcard or variable, it wraps the result in open/close
markers carrying a source key. At the end the markers are turned into a tree
of segments for the node's Preview, and stripped from the real output.

Markers use Unicode private-use characters, which never appear in prompts.
Source keys match what the frontend highlighter colors:
  c<offset>  the {…} block starting at <offset>
  w<offset>  the __wildcard__ starting at <offset>
  v<name>    the variable <name>
"""

import re

SOURCE_START = ""
SOURCE_END = ""
OPEN = ""
OPEN_END = ""
CLOSE = ""

_MARKER_CHARS = SOURCE_START + SOURCE_END + OPEN + OPEN_END + CLOSE
_SOURCE_RE = re.compile(SOURCE_START + r"\d+" + SOURCE_END)
_ANY_MARKER_RE = re.compile(
    "|".join([
        _SOURCE_RE.pattern,
        OPEN + "[^" + OPEN_END + "]*" + OPEN_END,
        CLOSE,
    ])
)
_WILDCARD_RE = re.compile(r"__([a-zA-Z0-9_./\\*?\[\] -]+?)__")

# Regexes the processors use, extended to capture an optional source marker
# in front of the construct. Group 1 is the source offset (or None).
MARKED_BRACES_RE = re.compile(r"(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?{([^{}]*?)}")
MARKED_WILDCARD_RE = re.compile(
    r"(?:" + SOURCE_START + r"(\d+)" + SOURCE_END + r")?__([a-zA-Z0-9_./\\*?\[\] -]+?)__"
)


def mark_sources(text):
    """Insert a source marker before every "{" (not "${") and "__name__"."""
    wildcard_starts = {m.start() for m in _WILDCARD_RE.finditer(text)}
    parts = []
    for i, ch in enumerate(text):
        if (ch == "{" and (i == 0 or text[i - 1] != "$")) or i in wildcard_starts:
            parts.append(f"{SOURCE_START}{i}{SOURCE_END}")
        parts.append(ch)
    return "".join(parts)


def wrap(key, text):
    """Wrap resolved text in markers for the given source key."""
    return f"{OPEN}{key}{OPEN_END}{text}{CLOSE}"


def strip_markers(text):
    """Remove every marker, leaving the plain text."""
    if not isinstance(text, str) or not any(c in text for c in _MARKER_CHARS):
        return text
    return _ANY_MARKER_RE.sub("", text)


def build_segments(marked):
    """Turn marked output into a list of segments for the Preview.

    Each segment is either {"text": str} or {"key": str, "children": [...]}.
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
            node = {"key": text[i + 1:end], "children": []}
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

    def __init__(self, match, prefix, suffix):
        self._inner = match.group(2)
        self._whole = f"{prefix}{self._inner}{suffix}"

    def group(self, index=0):
        return self._whole if index == 0 else self._inner
