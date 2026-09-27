import os
import re
from typing import List
from ..utils.replace_tokens import replace_tokens
from folder_paths import get_output_directory

from comfy_api.latest import io

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

class SaveTextFile(io.ComfyNode):
    # Keep the prefix input id for existing workflow connections.
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_SaveTextFile",
            display_name="💾 Save Text File With Path",
            category="⚡ MNeMiC Nodes",
            description="Saves text to a named file under ComfyUI's output folder.",
            inputs=[
                io.String.Input("file_text", force_input=True, tooltip="The text to save."),
                io.String.Input(
                    "path",
                    default='[time(%Y-%m-%d)]/',
                    multiline=False,
                    tooltip="Folder under ComfyUI's output folder. Empty uses the output folder itself; date and hostname tokens are supported.",
                ),
                io.String.Input(
                    "prefix",
                    display_name="filename",
                    default="[time(%Y-%m-%d - %H.%M.%S)].txt",
                    multiline=False,
                    placeholder="[time(%Y-%m-%d)].txt",
                    tooltip="Filename, with or without an extension. Supports date and hostname tokens.",
                ),
                io.String.Input(
                    "suffix",
                    default="",
                    advanced=True,
                    tooltip="Optional text after the filename and before its extension. Empty adds nothing; date and hostname tokens are supported.",
                ),
                io.String.Input(
                    "output_extension",
                    display_name="extension",
                    default="",
                    multiline=False,
                    tooltip="Override the filename extension, with or without a leading dot. Empty uses the filename extension, or txt if there is none.",
                ),
                io.DynamicCombo.Input(
                    "existing_file", display_name="if file exists",
                    tooltip="Overwrite replaces the file; ignore keeps it; increment filename saves to the next available numbered name.",
                    options=[
                        io.DynamicCombo.Option("overwrite", []),
                        io.DynamicCombo.Option("ignore", []),
                        io.DynamicCombo.Option("increment filename", [
                            io.Combo.Input(
                                "separator", options=["underscore", "hyphen", "space", "none"], default="underscore",
                                tooltip="Between the filename and a new number: underscore (_), hyphen (-), space or nothing. An existing trailing number keeps its separator.",
                            ),
                            io.Combo.Input(
                                "number_format", display_name="number format", options=["1", "01", "001", "0001"], default="1",
                                tooltip="Padding for a new number. An existing trailing number keeps at least its current number of digits.",
                            ),
                        ]),
                    ],
                ),
            ],
            outputs=[
                io.String.Output(display_name="output_full_path", tooltip="Full path to the saved file, including its extension."),
                io.String.Output(display_name="output_name", tooltip="Saved filename without its extension."),
                io.String.Output(display_name="output_path", tooltip="Containing folder of the saved file."),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, file_text, path, prefix='[time(%Y-%m-%d - %H.%M.%S)].txt', suffix='', output_extension='', existing_file=None) -> io.NodeOutput:
        existing_file = existing_file or {"existing_file": "overwrite"}
        mode = existing_file["existing_file"]
        if mode not in ("overwrite", "ignore", "increment filename"):
            raise ValueError(f"Unknown existing-file action: {mode}")
        separators = {"underscore": "_", "hyphen": "-", "space": " ", "none": ""}
        separator = separators[existing_file.get("separator", "underscore")] if mode == "increment filename" else ""
        number_format = existing_file.get("number_format", "1")
        if mode == "increment filename" and number_format not in ("1", "01", "001", "0001"):
            raise ValueError("Choose a supported number format.")
        # Inspect literal text so dots inside time tokens are not extensions.
        filename_extension = os.path.splitext(re.sub(r'\[[^\]]*\]', 'token', prefix).strip())[1]
        path = replace_tokens(path)
        prefix = replace_tokens(prefix)
        suffix = replace_tokens(suffix)

        if filename_extension and prefix.rstrip().endswith(filename_extension):
            prefix = prefix.rstrip()[:-len(filename_extension)]
        extension = output_extension.strip().lstrip('.') or filename_extension.lstrip('.') or 'txt'
        if sanitize_filename(extension) != extension:
            raise ValueError("The extension contains invalid filename characters.")

        # Sanitize filename components
        prefix = sanitize_filename(prefix)
        suffix = sanitize_filename(suffix)
        if not prefix:
            raise ValueError("Filename cannot be empty.")

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

        file_extension = f'.{extension}'
        filename = cls.save_with_conflict_handling(
            full_path, prefix + suffix, file_extension, file_text,
            mode, separator, len(number_format),
        )
        file_path = os.path.join(full_path, filename)

        # Remove extension from output_name
        output_name = os.path.splitext(filename)[0]

        return io.NodeOutput(file_path, output_name, full_path)

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        # File conflicts can change between otherwise identical queued runs.
        return float("nan")

    @classmethod
    def save_with_conflict_handling(cls, path, stem, extension, content, mode, separator, padding):
        filename = stem + extension
        if mode == "overwrite":
            cls.writeTextFile(os.path.join(path, filename), content)
            return filename

        match = re.fullmatch(r"(.*?)(\d+)", stem)
        if match:
            numbered_stem = match.group(1)
            counter = int(match.group(2)) + 1
            padding = max(padding, len(match.group(2)))
        else:
            numbered_stem = stem + separator
            counter = 1

        while True:
            file_path = os.path.join(path, filename)
            try:
                # Exclusive creation also protects against another queued writer.
                cls.writeTextFile(file_path, content, mode="x")
                return filename
            except FileExistsError:
                if not os.path.isfile(file_path):
                    raise
                if mode == "ignore":
                    return filename
                filename = f"{numbered_stem}{counter:0{padding}}{extension}"
                counter += 1

    @classmethod
    def writeTextFile(cls, file, content, mode="w"):
        """Write the content to the specified file."""
        try:
            with open(file, mode, encoding='utf-8', newline='\n') as f:
                f.write(content)
        except FileExistsError:
            raise
        except OSError as e:
            print(f"Unable to save file `{file}`: {e}")
            raise
