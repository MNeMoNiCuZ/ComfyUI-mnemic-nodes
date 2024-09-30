import re

def process_text(input_string,
                 collapse_sequential_spaces=False,
                 strip_leading_spaces=False,
                 strip_trailing_spaces=False,
                 strip_leading_symbols=False,
                 strip_trailing_symbols=False,
                 strip_newlines=False,
                 replace_newlines_with_period_space=False,
                 strip_inside_tags=None,
                 strip_leading_custom=None,
                 strip_trailing_custom=None,
                 strip_all_custom=None,
                 find_list=None,
                 replace_list=None):
    """
    Cleans up the input string based on the provided options.

    Args:
        input_string (str): The text to be processed.
        collapse_sequential_spaces (bool): If True, collapse multiple spaces into one.
        strip_leading_spaces (bool): If True, strip leading spaces per line.
        strip_trailing_spaces (bool): If True, strip trailing spaces per line.
        strip_leading_symbols (bool): If True, strip leading punctuation symbols per line.
        strip_trailing_symbols (bool): If True, strip trailing punctuation symbols per line.
        strip_newlines (bool): If True, remove all newlines.
        replace_newlines_with_period_space (bool): If True, replace multiple newlines with '. '.
        strip_inside_tags (list of str): List of character pairs to strip content between.
        strip_leading_custom (list of str): List of custom strings to strip from the start of each line.
        strip_trailing_custom (list of str): List of custom strings to strip from the end of each line.
        strip_all_custom (list of str): List of custom strings to remove throughout the text.
        find_list (list of str): List of strings to find.
        replace_list (list of str): List of strings to replace with.

    Returns:
        str: The processed text.
    """
    # Collapse sequential spaces (First Pass)
    if collapse_sequential_spaces:
        # Replace multiple spaces (2 or more) with a single space
        input_string = re.sub(r' {2,}', ' ', input_string)

    # Replace or strip newlines
    if replace_newlines_with_period_space:
        # Replace one or more consecutive newlines with '. '
        input_string = re.sub(r'\n+', '. ', input_string)
    elif strip_newlines:
        input_string = input_string.replace('\n', '')

    # Strip inside tags
    if strip_inside_tags:
        for tag_pair in strip_inside_tags:
            if len(tag_pair) != 2:
                raise ValueError(f"Each line in 'strip_inside_tags' must have exactly two characters. Found '{tag_pair}'")
            start_char, end_char = tag_pair[0], tag_pair[1]
            pattern = re.escape(start_char) + '.*?' + re.escape(end_char)
            input_string = re.sub(pattern, '', input_string, flags=re.DOTALL)

    # Split input into lines for per-line processing
    lines = input_string.split('\n')

    # Strip leading spaces per line
    if strip_leading_spaces:
        lines = [line.lstrip() for line in lines]

    # Strip trailing spaces per line
    if strip_trailing_spaces:
        lines = [line.rstrip() for line in lines]

    # Strip leading symbols per line
    if strip_leading_symbols:
        pattern = r'^[,\.!\?:;]+'
        lines = [re.sub(pattern, '', line) for line in lines]

    # Strip trailing symbols per line
    if strip_trailing_symbols:
        pattern = r'[,\.!\?:;]+$'
        lines = [re.sub(pattern, '', line) for line in lines]

    # Strip leading custom strings per line
    if strip_leading_custom:
        new_lines = []
        for line in lines:
            original_line = line
            for custom_str in strip_leading_custom:
                if not custom_str:  # Skip empty strings
                    continue
                custom_len = len(custom_str)
                while line.startswith(custom_str) and len(line) >= custom_len:
                    line = line[custom_len:]
            new_lines.append(line)
        lines = new_lines

    # Strip trailing custom strings per line
    if strip_trailing_custom:
        new_lines = []
        for line in lines:
            for custom_str in strip_trailing_custom:
                if not custom_str:  # Skip empty strings
                    continue
                custom_len = len(custom_str)
                while line.endswith(custom_str) and len(line) >= custom_len:
                    line = line[:-custom_len]
            new_lines.append(line)
        lines = new_lines

    # Rejoin lines after per-line processing
    input_string = '\n'.join(lines)

    # Strip custom strings throughout the text
    if strip_all_custom:
        for custom_str in strip_all_custom:
            if not custom_str:  # Skip empty strings
                continue
            input_string = input_string.replace(custom_str, '')

    # Find and replace
    if find_list and replace_list:
        if find_list and any(find_list):
            for find_str, replace_str in zip(find_list, replace_list):
                if not find_str:  # Skip empty find strings
                    continue
                input_string = input_string.replace(find_str, replace_str)
    else:
        # If find_list is empty or None, do nothing
        pass

    # Collapse sequential spaces (Second Pass)
    if collapse_sequential_spaces:
        # Replace multiple spaces (2 or more) with a single space
        input_string = re.sub(r' {2,}', ' ', input_string)

    return input_string
