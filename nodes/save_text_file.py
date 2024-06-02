import os
import re
from ..utils.replace_tokens import replace_tokens

class SaveTextFile:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "path": ("STRING", {"default": './output/[time(%Y-%m-%d)]/', "multiline": False}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "filename_suffix": ("STRING", {"default": "", "multiline": False}),
                "filename_delimiter": ("STRING", {"default": "_"}),
                "filename_number_padding": ("INT", {"default": 4, "min": 2, "max": 9, "step": 1}),
                "overwrite_mode": (["false", "prefix_as_filename"],),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "output_file_name")
    FUNCTION = "save_text_file"
    CATEGORY = "⚡ MNeMiC Nodes"

    def save_text_file(self, text, path, filename_prefix='ComfyUI', filename_suffix='', filename_delimiter='_', filename_number_padding=4, overwrite_mode='false'):
        path = replace_tokens(path)
        filename_prefix = replace_tokens(filename_prefix)
        filename_suffix = replace_tokens(filename_suffix)

        if not os.path.exists(path):
            print(f"Warning: The path `{path}` doesn't exist! Creating it...")
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                print(f"Error: The path `{path}` could not be created! Is there write access?\n{e}")

        if text.strip() == '':
            print(f"There is no text specified to save! Text is empty.").error.print()

        delimiter = filename_delimiter
        number_padding = int(filename_number_padding)
        file_extension = '.txt'

        filename, counter = self.generate_filename(path, filename_prefix, filename_suffix, delimiter, number_padding, file_extension)
        if overwrite_mode == 'prefix_as_filename':
            filename = f"{filename_prefix}{file_extension}"
        file_path = os.path.join(path, filename)

        output_file_name = f"{filename_prefix}{delimiter}{str(counter).zfill(number_padding)}{delimiter}{filename_suffix}"

        self.writeTextFile(file_path, text)

        return text, output_file_name

    def generate_filename(self, path, prefix, suffix, delimiter, number_padding, extension):
        pattern = f"{re.escape(prefix)}{re.escape(delimiter)}(\\d{{{number_padding}}}){re.escape(delimiter)}{re.escape(suffix)}"
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

        filename = f"{prefix}{delimiter}{counter:0{number_padding}}{delimiter}{suffix}{extension}"
        return filename, counter

    def writeTextFile(self, file, content):
        try:
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
        except OSError:
            print(f"Unable to save file `{file}`").error.print()
