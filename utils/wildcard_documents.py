"""Expand whole-document wildcard content without unbounded include cycles."""

from .wildcard_provenance import InnerMatch, MARKED_WILDCARD_RE, WILDCARD_RE, strip_markers, wrap


def resolve_document_choice(processor, match):
    """Resolve ___{__list__}___ by selecting a row, then loading its whole file.

    A row such as __scene__ must survive selection without being expanded to
    one of scene.txt's lines. The flag applies only while selecting the row;
    ordinary wildcards inside the selected document keep their normal meaning.
    A ~~folder~~ row loads a whole random file from that folder.
    """
    previous = getattr(processor, "_select_document_reference", False)
    processor._select_document_reference = True
    processor._picked = (None, None)
    try:
        selected = processor.evaluate_curly_braces(InnerMatch(match, "{", "}"))
        selected = strip_markers(processor._restore_protected_text(selected)).strip()
    finally:
        processor._select_document_reference = previous
    row_file = processor._picked[0]

    reference = WILDCARD_RE.fullmatch(selected)
    name = reference.group("wildcard_name") if reference else selected
    delimiter = "~~~" if reference and reference.group("delimiter")[0] == "~" else "___"
    target = MARKED_WILDCARD_RE.fullmatch(f"{delimiter}{name}{delimiter}")
    result = processor._evaluate_marked_wildcard(target) if target else None
    if not target or result == target.group(0):
        # A picked row that is no reference, as in ___{__scene__|~~scenes~~}___,
        # means its own file is the document.
        if reference or not row_file:
            return match.group(0)
        result = resolve_document_file(processor, row_file, match.group(0))
    if not match.group(1):
        return result
    return wrap(f"c{match.group(1)}", result, *processor._picked)


def resolve_document_file(processor, file_path, original):
    """Resolve the whole content of one wildcard file."""
    key = (file_path, True)
    if key not in processor.wildcard_cache:
        processor.wildcard_cache[key] = (file_path, *processor._read_wildcard_file(file_path, True))
    result = resolve_document(processor, file_path, processor.wildcard_cache[key][1][0], original)
    processor._picked = (file_path, None)
    return processor._protect_resolved_text(result)


def resolve_document(processor, wildcard_name, content, original):
    # File contents can include other documents (or themselves). Keep a stack
    # across recursive _process_text calls; leave a cyclic token unresolved.
    stack = getattr(processor, "_document_stack", None)
    if stack is None:
        stack = processor._document_stack = []
    if wildcard_name in stack or len(stack) >= getattr(processor, "max_nested_passes", 10):
        return original
    stack.append(wildcard_name)
    try:
        return processor._process_text(content)
    finally:
        stack.pop()
