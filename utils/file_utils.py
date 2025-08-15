from pathlib import Path
import os
import re

def score_filename_match(name, filename, base_path=None):
    """Score how well a filename matches the requested name."""
    p_filename = Path(filename)
    base_name = p_filename.name
    base_name_no_ext = p_filename.stem
    name_no_ext = Path(name).stem
    
    # Calculate path depth score relative to the base_path if provided
    path_depth = 0
    if base_path:
        try:
            # Calculate depth relative to the wildcard folder
            path_depth = len(p_filename.relative_to(base_path).parts)
        except ValueError:
            # This can happen if the file is not in the base_path, fallback to absolute depth
            path_depth = len(p_filename.parts) - 1
    else:
        path_depth = len(p_filename.parts) - 1
        
    path_penalty = path_depth * 0.0001
    
    # If searching for a numbered variant, also match the base name
    base_search_name = re.sub(r'\d+$', '', name_no_ext).rstrip('-')
    
    # Perfect path match (highest priority)
    if filename == name:
        return (200, "perfect path match")

    # Exact match gets high priority
    if base_name_no_ext == name_no_ext:
        return (100 - path_penalty, f"exact match (depth: {path_depth})")
    
    # Base version match when searching for numbered variant
    if base_name_no_ext == base_search_name:
        return (90 - path_penalty, f"base version match (depth: {path_depth})")
    
    # Check if it's a numbered variant of the exact name
    if base_name.startswith(name + "-"):
        try:
            num = int(re.findall(r'-(\d+)', base_name)[0])
            return (80 + (num * 0.001) - path_penalty, f"numbered variant ({num}, depth: {path_depth})")
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
                    return (95 - path_penalty, f"exact number match ({target_number}, depth: {path_depth})")
                return (85 - (number_diff * 0.1) - path_penalty, f"number near match ({file_number}, depth: {path_depth})")
            except (IndexError, ValueError):
                pass
    
    # Simple startswith match
    if base_name_no_ext.startswith(name):
        return (50 - path_penalty, f"prefix match (depth: {path_depth})")
        
    # Contains match (lower priority)
    if name in base_name_no_ext:
        return (40 - path_penalty, f"contains match (depth: {path_depth})")

    return (0, "no match")

def find_best_match(search_term, file_list, log=False, wildcard_paths=None):
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

        score, reason = score_filename_match(search_term, file_path, base_path=base_path)
        if score > 0:
            base_name = Path(file_path).name
            if base_name in seen_filenames:
                seen_filenames[base_name] = True
            else:
                seen_filenames[base_name] = False
            matches.append((score, file_path, reason, base_path))
    
    matches.sort(key=lambda x: x[0], reverse=True)
    
    if log and matches:
        print("\nCandidate files (sorted by relevance):")
        for score, file, reason, base_path in matches:
            base_name = Path(file).name
            try:
                display_name = str(Path(file).relative_to(base_path)) if base_path else base_name
            except (ValueError, TypeError):
                display_name = base_name
            
            print(f"  {display_name:<60} : {score:>5.1f} ({reason})")
        
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