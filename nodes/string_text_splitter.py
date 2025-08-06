import re

class StringTextSplitter:
    """
    A node to split a string by the first occurrence of a delimiter.
    """
    OUTPUT_NODE = True
    FUNCTION = "split_text"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Splits a string by the first occurrence of a delimiter.\n\nExample:\n- input_string: part1|part2|part3\n- delimiter: |\n- first_chunk: part1\n- remainder: part2|part3"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {
                    "multiline": True,
                    "tooltip": "The input text to split.",
                    "placeholder": "Text to be split..."
                }),
                "delimiter": ("STRING", {
                    "multiline": False,
                    "tooltip": "The character to split the text on. The node will split at the first time this character appears.",
                    "placeholder": "e.g., |"
                }),
                "split_at_linebreaks": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "If true, also split at line breaks. Can be used with or without a delimiter."
                }),
                "target_indices": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Comma-separated list of indices (0-based) of chunks to extract. E.g., '0,2' for the first and third chunk. Leave empty to ignore.",
                    "placeholder": "e.g., 0,1,5"
                }),
            }
        }
 
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING",)
    RETURN_NAMES = ("first_chunk", "remainder", "chunk_list", "targeted_chunks",)
    OUTPUT_TOOLTIPS = (
        "The part of the string before the first delimiter.",
        "The remainder string after the first delimiter.",
        "A list of all items split by the delimiter.",
        "A multiline string of chunks at the specified target indices.",
    )
 
    def split_text(self, input_string, delimiter, split_at_linebreaks=False, target_indices=""):
        # Determine the regex pattern for splitting
        split_pattern = None
        
        if split_at_linebreaks:
            if not delimiter:
                split_pattern = r'[\n\r]+' # Split by one or more linebreaks
            else:
                # Split by delimiter OR linebreaks
                split_pattern = f'{re.escape(delimiter)}|[\n\r]+'
        elif delimiter:
            # Only delimiter is active, escape it for regex
            split_pattern = re.escape(delimiter)
        
        if not split_pattern:
            # No delimiter and no linebreak splitting enabled
            return (input_string, "", [input_string])
 
        # Perform the first split (for first_chunk and remainder)
        parts = re.split(split_pattern, input_string, 1)
        
        first_chunk = parts[0]
        remainder = parts[1] if len(parts) > 1 else ""
 
        # Perform the full split (for chunk_list)
        all_parts = re.split(split_pattern, input_string)
        # Filter out empty strings that might result from regex splits (e.g., multiple delimiters in a row)
        all_parts = [p for p in all_parts if p]
        
        # Extract targeted chunks
        targeted_chunks_list = []
        if target_indices:
            try:
                indices_to_extract = [int(idx.strip()) for idx in target_indices.split(',') if idx.strip()]
                for idx in indices_to_extract:
                    if 0 <= idx < len(all_parts):
                        targeted_chunks_list.append(all_parts[idx])
            except ValueError:
                print(f"Warning: Invalid target_indices format: '{target_indices}'. Skipping targeted chunk extraction.")
        
        targeted_chunks_output = "\n".join(targeted_chunks_list)
 
        return (first_chunk, remainder, all_parts, targeted_chunks_output)

NODE_CLASS_MAPPINGS = {
    "StringTextSplitter": StringTextSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringTextSplitter": "String Text Splitter",
}
