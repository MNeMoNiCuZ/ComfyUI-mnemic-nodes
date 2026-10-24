"""Expand whole-document wildcard content without unbounded include cycles."""

from .wildcard_provenance import InnerMatch, WILDCARD_RE, strip_markers, wrap


def resolve_document_choice(processor, match):
    """Resolve ___{__list__}___ by selecting a row, then loading its whole file.

    A row such as __scene__ must survive selection without being expanded to
    one of scene.txt's lines. The flag applies only while selecting the row;
    ordinary wildcards inside the selected document keep their normal meaning.
    """
    previous = getattr(processor, "_select_document_reference", False)
    processor._select_document_reference = True
    try:
        selected = processor.evaluate_curly_braces(InnerMatch(match, "{", "}"))
        selected = strip_markers(processor._restore_protected_text(selected)).strip()
    finally:
        processor._select_document_reference = previous

    reference = WILDCARD_RE.fullmatch(selected)
    name = reference.group("wildcard_name") if reference else selected
    target = WILDCARD_RE.fullmatch(f"___{name}___")
    if not target:
        return match.group(0)
    inner = InnerMatch(target, "___", "___", content_group="wildcard_name")
    result = processor._evaluate_file_wildcard(inner, whole_document=True)
    return wrap(f"c{match.group(1)}", result) if match.group(1) else result


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
