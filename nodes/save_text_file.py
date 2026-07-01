import os
import re
from typing import List
from ..utils.replace_tokens import replace_tokens
from folder_paths import get_output_directory

def sanitize_filename(string):
    """
    Sanitize a string to be safe for use as a filename on Windows/Linux.
    Preserves Unicode characters while removing reserved characters and control codes.
    """
    # Define invalid characters: < > : " / \ | ? * and control characters
    # We use a blacklist approach to preserve foreign characters (UTF-8)
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    
    # Remove invalid characters
    sanitized = re.sub(invalid_chars, '', string)
    
    # Strip leading/trailing whitespaces and dots (Windows doesn't like trailing dots/spaces)
    sanitized = sanitized.strip('. ')
    
    return sanitized

class SaveTextFile:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_text": ("STRING", {"forceInput": True, "tooltip": "The text to save."}),
                "path": ("STRING", {"default": '[time(%Y-%m-%d)]/', "multiline": False, "tooltip": "The folder path to save the file to.\n\nThe following creates a date folder:\n[time(%Y-%m-%d)]"}),
                "prefix": ("STRING", {"default": "[time(%Y-%m-%d - %H.%M.%S)]", "tooltip": "The prefix to add to the file name.\n\nThe following creates a file with a date and timestamp:\n[time(%Y-%m-%d - %H.%M.%S)]"}),
                "counter_separator": ("STRING", {"default": "_", "tooltip": "The separator to use between the file name and the counter."}),
                "counter_length": ("INT", {"default": 3, "min": 0, "max": 24, "step": 1, "tooltip": "The number of digits to use in the counter."}),
                "suffix": ("STRING", {"default": "", "tooltip": "The suffix to add to the file name after the counter."}),
                "output_extension": ("STRING", {"default": "txt", "tooltip": "The extension to use for the output file."}),
            }
        } #{prefix}{separator}{counter_str}{separator}{suffix}{extension}

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("output_full_path", "output_name", "output_path",)
    OUTPUT_TOOLTIPS = ("The full path to the saved file", "The name of the saved file", "The formatted path to the saved file (excluding filename)",)
    FUNCTION = "save_text_file"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Saves text to a file with specified parameters."

    def save_text_file(self, file_text, path, prefix='[time(%Y-%m-%d %H.%M.%S)]', counter_separator='_', counter_length=3, suffix='', output_extension='txt'):
        path = replace_tokens(path)
        prefix = replace_tokens(prefix)
        suffix = replace_tokens(suffix)

        # Sanitize filename components
        prefix = sanitize_filename(prefix)
        suffix = sanitize_filename(suffix)

        # Truncate to avoid MAX_PATH issues (Windows limit is 260 chars usually)
        # User requested a limit of 250 chars max for the filename parts
        # We assume some buffer for extension (e.g. .txt) and counter (e.g. _001)
        # 250 - ~15 chars buffer = 235 chars available for prefix + suffix
        max_filename_len = 235
        
        current_len = len(prefix) + len(suffix)
        if current_len > max_filename_len:
            # If combined length exceeds limit, truncate suffix first, then prefix
            if len(prefix) < max_filename_len:
                # Prefix fits, but combined doesn't; truncate suffix
                remaining_space = max_filename_len - len(prefix)
                suffix = suffix[:remaining_space]
            else:
                # Prefix itself is too long; truncate prefix and remove suffix
                prefix = prefix[:max_filename_len]
                suffix = ""

        # Safety check to ensure the extension is not empty
        if not output_extension.strip():
            raise ValueError("The output extension cannot be empty.")

        # Safety check to prevent directory traversal
        if '..' in path or any(esc in path for esc in ['..\\', '../']):
            raise ValueError("The specified path contains invalid characters that navigate outside the output directory.")

        # Get the base output directory from folder_paths
        output_base_dir = get_output_directory()
        full_path = os.path.join(output_base_dir, path)
        full_path = os.path.abspath(full_path)

        # Ensure the path is within the allowed directory
        if not full_path.startswith(output_base_dir):
            raise ValueError("The specified path is outside the allowed output directory")

        if not os.path.exists(full_path):
            print(f"Warning: The path `{full_path}` doesn't exist! Creating it...")
            try:
                os.makedirs(full_path, exist_ok=True)
            except OSError as e:
                print(f"Error: The path `{full_path}` could not be created! Is there write access?\n{e}")

        # if file_text.strip() == '':
        #     raise ValueError("There is no text specified to save! Text is empty.")

        separator = counter_separator
        number_padding = int(counter_length)
        file_extension = f'.{output_extension}'

        filename, counter = self.generate_filename(full_path, prefix, suffix, separator, number_padding, file_extension)
        file_path = os.path.join(full_path, filename)

        # Remove extension from output_name
        output_name = os.path.splitext(filename)[0]

        self.writeTextFile(file_path, file_text)

        return file_path, output_name, full_path

    def generate_filename(self, path, prefix, suffix, separator, number_padding, extension):
        """Generate a unique filename based on the provided parameters."""
        pattern_parts = [re.escape(prefix)]
        if number_padding > 0:
            pattern_parts.append(f"{separator}(\\d{{{number_padding}}})")
        if suffix:
            pattern_parts.append(f"{separator}{re.escape(suffix)}")
        pattern_parts.append(re.escape(extension))

        pattern = ''.join(pattern_parts)
        
        # Find existing counters
        existing_counters = []
        for filename in os.listdir(path):
            match = re.match(pattern, filename)
            if match:
                try:
                    counter_value = int(match.group(1)) if number_padding > 0 else 0
                    existing_counters.append(counter_value)
                except (IndexError, ValueError):
                    continue

        existing_counters.sort(reverse=True)

        # Determine the next counter value
        counter = existing_counters[0] + 1 if existing_counters else 1
        counter_str = f"{counter:0{number_padding}}" if number_padding > 0 else ""

        # Construct the filename
        if number_padding > 0:
            if suffix:
                filename = f"{prefix}{separator}{counter_str}{separator}{suffix}{extension}"
            else:
                filename = f"{prefix}{separator}{counter_str}{extension}"
        else:
            filename = f"{prefix}{suffix}{extension}"

        return filename, counter

    def writeTextFile(self, file, content):
        """Write the content to the specified file."""
        try:
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
        except OSError as e:
            print(f"Unable to save file `{file}`: {e}")
            raise
