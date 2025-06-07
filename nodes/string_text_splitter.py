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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("first_chunk", "remainder", "chunk_list",)
    OUTPUT_TOOLTIPS = (
        "The part of the string before the first delimiter.",
        "The remainder string after the first delimiter.",
        "A list of all items split by the delimiter.",
    )

    def split_text(self, input_string, delimiter):
        if not delimiter:
            return (input_string, "", [input_string])

        parts = input_string.split(delimiter, 1)
        all_parts = input_string.split(delimiter)
        
        if len(parts) == 1:
            # Delimiter not found
            return (parts[0], "", all_parts)
        else:
            return (parts[0], parts[1], all_parts)

NODE_CLASS_MAPPINGS = {
    "StringTextSplitter": StringTextSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringTextSplitter": "String Text Splitter",
}