import re

from .wildcard_provenance import CLOSE, MARKED_CONDITION_START_RE, OPEN, strip_markers, wrap


def _has_top_level_pipe(value):
    depth = 0
    for ch in value:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "|" and depth == 0:
            return True
    return False


def split_variable_definitions(text):
    """Find ${name=!value} variable definitions and remove them from text.

    The value may contain nested {...} blocks, e.g. ${color=!{red|{dark|light} blue}},
    so the closing brace is found by counting braces rather than taking the
    first "}". Plain ${name} uses are left in place. A definition whose braces
    never balance ends at the first "}" on its line, as it always has.

    Loose forms are accepted too: ${name=value} and ${!name=value} work like
    ${name=!value}, and a bare choice list such as ${vehicle=!car|bike} is
    treated as ${vehicle=!{car|bike}}.

    Returns (definitions, text_without_definitions), where definitions is a
    list of (name, value_expression) tuples in the order they appear.
    """
    definitions = []
    parts = []
    i = 0
    while True:
        start = text.find("${", i)
        if start == -1:
            break
        eq = text.find("=", start + 2)
        close = text.find("}", start + 2)
        name = text[start + 2:eq] if eq != -1 else ""
        if eq == -1 or (close != -1 and close < eq) or "{" in name or "\n" in name:
            # Not a definition (e.g. a ${name} use); keep it and move on.
            parts.append(text[i:start + 2])
            i = start + 2
            continue

        value_start = eq + 2 if text.startswith("=!", eq) else eq + 1
        depth = 0
        end = value_start
        while end < len(text):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                if depth == 0:
                    break
                depth -= 1
            end += 1
        if end >= len(text):
            # Unclosed definition. Keep the old behaviour: the value ends at
            # the first "}" on the same line, or the text is left untouched.
            if close == -1 or "\n" in text[start:close]:
                parts.append(text[i:start + 2])
                i = start + 2
                continue
            end = close

        value = text[value_start:end]
        if _has_top_level_pipe(value):
            value = "{" + value + "}"
        definitions.append((name.strip().lstrip("!"), value))
        parts.append(text[i:start])
        i = end + 1
    parts.append(text[i:])
    return definitions, "".join(parts)


UNDEFINED_VARIABLE_RE = re.compile(r"\$\{([^{}\n]*)\}")


def drop_undefined_variables(text, names):
    """Remove every ${name} still in text after resolution, adding each name to names."""
    def drop(match):
        names.add(match.group(1))
        return ""
    return UNDEFINED_VARIABLE_RE.sub(drop, text)


def _find_top_level(text, tokens):
    """Return (index, token) of the first token outside {...} blocks and
    resolved values, or (-1, None)."""
    depth = 0
    for i, ch in enumerate(text):
        if depth == 0:
            for token in tokens:
                if text.startswith(token, i):
                    return i, token
        if ch == "{" or ch == OPEN:
            depth += 1
        elif ch == "}" or ch == CLOSE:
            depth -= 1
    return -1, None


def _chosen_branch(processor, body):
    """Resolve the first branch of an if{...} body that applies, or return ""."""
    body = re.sub(r"\s*\n\s*", "", re.sub(r"#.*", "", body))
    while True:
        end, _ = _find_top_level(body, ("|",))
        branch = body if end == -1 else body[:end]
        colon, _ = _find_top_level(branch, (":",))
        op_at, op = _find_top_level(branch[:colon], ("==", "!=")) if colon != -1 else (-1, None)
        if op is None:
            return processor._process_text(branch)
        left, right = (strip_markers(processor._process_text(side)).strip().casefold()
                       for side in (branch[:op_at], branch[op_at + 2:colon]))
        if (left == right) == (op == "=="):
            return processor._process_text(branch[colon + 1:])
        if end == -1:
            return ""
        body = body[end + 1:]


def resolve_conditions(processor, text):
    """Resolve every if{...} block in text.

    if{a==b:text|a!=c:text|fallback} gives the text of the first branch whose
    comparison holds. A branch without a comparison always holds, so it works
    as the else. With no match the block is empty. Both sides are resolved,
    then compared ignoring case and surrounding spaces. Only the chosen
    branch is resolved, and "|", ":" and "==" inside nested blocks and
    variable values do not split the block.
    """
    parts = []
    pos = 0
    for match in MARKED_CONDITION_START_RE.finditer(text):
        if match.start() < pos:
            continue
        body_start = match.end()
        end, _ = _find_top_level(text[body_start:], ("}",))
        if end == -1:
            continue
        body = text[body_start:body_start + end]
        result = _chosen_branch(processor, body)
        processor.wildcard_log(f"Evaluated if{{{strip_markers(body)}}} -> {strip_markers(result)}", level=1)
        result = processor._protect_resolved_text(result)
        parts.append(text[pos:match.start()])
        parts.append(wrap(f"c{match.group(1)}", result) if match.group(1) else result)
        pos = body_start + end + 1
    parts.append(text[pos:])
    return "".join(parts)
