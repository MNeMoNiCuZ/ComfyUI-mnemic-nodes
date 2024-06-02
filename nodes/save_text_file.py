import os
import re
import logging
from ..utils.replace_tokens import replace_tokens
from folder_paths import get_output_directory

class SaveTextFile:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {"forceInput": True}),
                "path": ("STRING", {"default": '[time(%Y-%m-%d)]/', "multiline": False}),
                "filename_prefix": ("STRING", {"default": "[time(%Y-%m-%d - %H.%M.%S)]"}),
                "filename_suffix": ("STRING", {"default": ""}),
                "filename_padding_delimiter": ("STRING", {"default": "_"}),
                "filename_padding_length": ("INT", {"default": 3, "min": 0, "max": 24, "step": 1}),
                "output_file_extension": ("STRING", {"default": "txt"}),
                "overwrite_mode": (["false", "prefix_as_filename"],)
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("output_file_path", "output_file_name", "output_file_extension")
    FUNCTION = "save_text_file"
    CATEGORY = "⚡ MNeMiC Nodes"

    def save_text_file(self, input_text, path, filename_prefix='[time(%Y-%m-%d %H.%M.%S)]', filename_suffix='', filename_padding_delimiter='_', filename_padding_length=3, output_file_extension='txt', overwrite_mode='false'):
        path = replace_tokens(path)
        filename_prefix = replace_tokens(filename_prefix)
        filename_suffix = replace_tokens(filename_suffix)

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

        if input_text.strip() == '':
            raise ValueError("There is no text specified to save! Text is empty.")

        delimiter = filename_padding_delimiter
        number_padding = int(filename_padding_length)
        file_extension = f'.{output_file_extension}'

        filename, counter = self.generate_filename(full_path, filename_prefix, filename_suffix, delimiter, number_padding, file_extension, overwrite_mode)
        file_path = os.path.join(full_path, filename)

        # Remove extension from output_file_name
        output_file_name = os.path.splitext(filename)[0]

        self.writeTextFile(file_path, input_text)

        return file_path, output_file_name, output_file_extension

    def generate_filename(self, path, prefix, suffix, delimiter, number_padding, extension, overwrite_mode):
        if overwrite_mode == 'prefix_as_filename':
            return f"{prefix}{extension}", 0

        if suffix:
            pattern = f"{re.escape(prefix)}(\\d{{{number_padding}}}){delimiter}{re.escape(suffix)}"
        else:
            pattern = f"{re.escape(prefix)}(\\d{{{number_padding}}})"

        existing_counters = [
            int(re.search(pattern, filename).group(1))
            for filename in os.listdir(path)
            if re.match(pattern, filename)
        ]
        existing_counters.sort(reverse=True)

        if existing_counters:
            counter = existing_counters[0] + 1
        else:
            counter = 1

        if number_padding > 0:
            if suffix:
                filename = f"{prefix}{counter:0{number_padding}}{delimiter}{suffix}{extension}"
            else:
                filename = f"{prefix}{counter:0{number_padding}}{extension}"
        else:
            filename = f"{prefix}{suffix}{extension}"

        return filename, counter

    def writeTextFile(self, file, content):
        try:
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
        except OSError:
            logging.error(f"Unable to save file `{file}`")
