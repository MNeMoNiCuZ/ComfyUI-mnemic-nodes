from pathlib import Path
import os
import re

# Caps how many candidate files get printed when logging a wildcard search.
# Wildcard folders can hold hundreds of matches (especially with fuzzy word
# matching), so the console log only shows the most relevant ones.
MAX_LOGGED_CANDIDATES = 15

def score_filename_match(name, filename, base_path=None, fuzzy_search=False):
    """Score how well a filename matches the requested name."""
    p_filename = Path(filename)
    base_name = p_filename.name
    base_name_no_ext = p_filename.stem
    p_name = Path(name)
    name_no_ext = p_name.stem

    # Calculate path depth, and the file's directory parts relative to the
    # wildcard folder if provided (used both for the depth penalty and for
    # comparing against any directory components in the search term).
    if base_path:
        try:
            rel_parts = p_filename.relative_to(base_path).parts
        except ValueError:
            # This can happen if the file is not in the base_path, fallback to absolute parts
            rel_parts = p_filename.parts
    else:
        rel_parts = p_filename.parts

    path_depth = len(rel_parts)
    file_dir_parts = tuple(part.lower() for part in rel_parts[:-1])
    name_dir_parts = tuple(part.lower() for part in p_name.parts[:-1])

    # Explicit, whole-number path priority tiers. A score is a percentage of
    # a perfect match, so a match can only ever be penalized down from its
    # base tier value (e.g. 100 for an exact name match) — never boosted
    # above it. Penalties are kept well under the smallest gap between match
    # types (5 points), so this only orders candidates within one match
    # type — it never lets a weaker match type outrank a stronger one.
    #
    # Search has NO subfolder in it (e.g. "hair_color"):
    #   root-level file (depth 1)       -> no penalty  (best)
    #   1 subfolder deep                -> -1
    #   2 subfolders deep               -> -2
    #   ... capped at -3
    #
    # Search HAS subfolder(s) in it (e.g. "POS/head"):
    #   file sits in that exact subfolder   -> no penalty (best, still 100%)
    #   file sits at the root, no subfolder -> -2
    #   file sits in a different subfolder  -> -4 (worst)
    if name_dir_parts:
        if len(file_dir_parts) >= len(name_dir_parts) and file_dir_parts[-len(name_dir_parts):] == name_dir_parts:
            path_penalty = 0.0
            path_bonus_note = ", exact subfolder match"
        elif not file_dir_parts:
            path_penalty = 2.0
            path_bonus_note = ", root-level file"
        else:
            path_penalty = 4.0
            path_bonus_note = ", wrong subfolder"
    else:
        path_penalty = min(max(path_depth - 1, 0) * 1.0, 3.0)
        path_bonus_note = ""

    # If searching for a numbered variant, also match the base name
    base_search_name = re.sub(r'\d+$', '', name_no_ext).rstrip('-')

    # Perfect path match (highest priority) — still capped at 100, a perfect match is 100%
    if filename == name:
        return (100, "perfect path match")

    # Exact match gets high priority
    if base_name_no_ext == name_no_ext:
        return (100 - path_penalty, f"exact match (depth: {path_depth}{path_bonus_note})")

    # Base version match when searching for numbered variant
    if base_name_no_ext == base_search_name:
        return (90 - path_penalty, f"base version match (depth: {path_depth}{path_bonus_note})")

    # Check if it's a numbered variant of the exact name
    if base_name.startswith(name + "-"):
        try:
            num = int(re.findall(r'-(\d+)', base_name)[0])
            return (80 + (num * 0.001) - path_penalty, f"numbered variant ({num}, depth: {path_depth}{path_bonus_note})")
        except (IndexError, ValueError):
            pass

    # Check if we're looking for a specific number
    number_search = re.search(r'(\d+)$', name)
    if number_search:
        base_without_number = name[:-len(number_search.group(1))]
        target_number = int(number_search.group(1))
        if base_name.startswith(base_without_number):
            try:
                file_number = int(re.findall(r'-(\d+)', base_name)[0])
                number_diff = abs(target_number - file_number)
                if number_diff == 0:
                    return (95 - path_penalty, f"exact number match ({target_number}, depth: {path_depth}{path_bonus_note})")
                return (85 - (number_diff * 0.1) - path_penalty, f"number near match ({file_number}, depth: {path_depth}{path_bonus_note})")
            except (IndexError, ValueError):
                pass

    # Fuzzy word match: treat underscore/hyphen/space as interchangeable word
    # delimiters, so "color_hair", "color-hair" and "color hair" all match
    # "hair_color" regardless of word order. Only kicks in for multi-word
    # names — a single word with no delimiters falls through to the
    # prefix/contains checks below as before.
    word_split = re.compile(r'[\s_-]+')
    name_words = [w for w in word_split.split(name_no_ext.lower()) if w]
    file_words = [w for w in word_split.split(base_name_no_ext.lower()) if w]
    if fuzzy_search and len(name_words) > 1:
        if sorted(name_words) == sorted(file_words):
            return (70 - path_penalty, f"fuzzy match, reordered words (depth: {path_depth}{path_bonus_note})")

    # Simple startswith match
    if base_name_no_ext.startswith(name):
        return (50 - path_penalty, f"prefix match (depth: {path_depth}{path_bonus_note})")

    # Contains match (lower priority)
    if name in base_name_no_ext:
        return (40 - path_penalty, f"contains match (depth: {path_depth}{path_bonus_note})")

    # Fuzzy word match (lower priority): some, but not all, words shared
    if fuzzy_search and len(name_words) > 1 and file_words:
        shared = set(name_words) & set(file_words)
        if shared:
            overlap = len(shared) / len(set(name_words))
            return (30 * overlap - path_penalty, f"fuzzy match, {len(shared)}/{len(set(name_words))} words matched (depth: {path_depth}{path_bonus_note})")

    return (0, "no match")

def find_best_match(search_term, file_list, log=False, wildcard_paths=None, fuzzy_search=False, max_logged=MAX_LOGGED_CANDIDATES):
    """Find the best matching file from a list based on scoring."""
    matches = []
    if log:
        print(f"\nFinding matches for '{search_term}':")

    seen_filenames = {}

    # Convert wildcard_paths to Path objects for comparison
    path_wildcard_paths = [Path(p) for p in wildcard_paths] if wildcard_paths else []

    for file_path in file_list:
        p_file_path = Path(file_path)
        base_path = None
        if path_wildcard_paths:
            # Find which wildcard_path this file belongs to.
            possible_bases = [p for p in path_wildcard_paths if p in p_file_path.parents]
            if possible_bases:
                # Get the longest path, which is the most specific base path.
                base_path = max(possible_bases, key=lambda p: len(p.as_posix()))

        score, reason = score_filename_match(search_term, file_path, base_path=base_path, fuzzy_search=fuzzy_search)
        if score > 0:
            base_name = Path(file_path).name
            if base_name in seen_filenames:
                seen_filenames[base_name] = True
            else:
                seen_filenames[base_name] = False
            matches.append((score, file_path, reason, base_path))
    
    matches.sort(key=lambda x: x[0], reverse=True)
    
    if log and matches:
        print(f"\nCandidate files (sorted by relevance, showing top {min(len(matches), max_logged)} of {len(matches)}):")
        for score, file, reason, base_path in matches[:max_logged]:
            base_name = Path(file).name
            try:
                display_name = str(Path(file).relative_to(base_path)) if base_path else base_name
            except (ValueError, TypeError):
                display_name = base_name

            print(f"  {display_name:<60} : {score:>5.1f} ({reason})")
        if len(matches) > max_logged:
            print(f"  ... and {len(matches) - max_logged} more not shown")

        _score, selected_path_str, _reason, selected_base_path = matches[0]
        selected_path = Path(selected_path_str)
        try:
            selected_display = str(selected_path.relative_to(selected_base_path)) if selected_base_path else selected_path.name
        except (ValueError, TypeError):
            selected_display = selected_path.name
            
        print(f"\nSelected: {selected_display}")
    elif log:
        print("  No matching files found")
    
    return matches[0][1] if matches else None

def find_image_text_pairs(folder_path, text_format_extension="txt"):
    """
    Finds pairs of image and text files with matching basenames in a folder.
    Returns a sorted list of tuples, where each tuple contains (image_path, text_path, basename).
    """
    if not os.path.isdir(folder_path):
        return []

    image_files = {}
    text_files = {}
    image_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
    text_exts = [f'.{text_format_extension.lower()}']

    for f in sorted(os.listdir(folder_path)):
        basename, ext = os.path.splitext(f)
        if ext.lower() in image_exts:
            image_files[basename] = os.path.join(folder_path, f)
        elif ext.lower() in text_exts:
            text_files[basename] = os.path.join(folder_path, f)

    pairs = []
    for basename in sorted(image_files.keys()):
        if basename in text_files:
            pairs.append((image_files[basename], text_files[basename], basename))
            
    return pairs