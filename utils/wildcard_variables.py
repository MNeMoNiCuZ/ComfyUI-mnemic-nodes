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
