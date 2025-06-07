import re

class StringTextExtractor:
    """
    A node to extract the first occurrence of text between specified delimiters.
    """
    OUTPUT_NODE = True
    FUNCTION = "extract_text"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Extracts the first occurrence of text between a pair of characters (delimiters)."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {
                    "multiline": True,
                    "tooltip": "The input text to search within.",
                    "placeholder": "Some text [with captured content] and more text."
                }),
                "delimiters": ("STRING", {
                    "multiline": False,
                    "tooltip": "The pair of characters to use as delimiters.\nExample: [], **, <>",
                    "placeholder": "e.g., []"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("extracted_text", "remainder_text", "extracted_list",)
    OUTPUT_TOOLTIPS = (
        "The content found inside the first instance of the specified delimiters.",
        "The rest of the text after the extracted content and its delimiters have been removed.",
        "A list of all items found between the delimiters.",
    )

    def extract_text(self, input_string, delimiters):
        if not delimiters or len(delimiters) < 2:
            # If delimiters are invalid, return original text as remainder
            return ("", input_string, [])

        start_delim = re.escape(delimiters[0])
        end_delim = re.escape(delimiters[-1])

        # Find all non-overlapping matches for the list output
        all_captures = re.findall(f"{start_delim}(.*?){end_delim}", input_string, re.DOTALL)

        # Non-greedy search for the content between the first pair of delimiters
        match = re.search(f"{start_delim}(.*?){end_delim}", input_string, re.DOTALL)

        if match:
            extracted_text = match.group(1)
            # The remainder is the part before the match plus the part after the match
            remainder_text = input_string[:match.start()] + input_string[match.end():]
            return (extracted_text, remainder_text, all_captures)
        else:
            # No match found
            return ("", input_string, [])

NODE_CLASS_MAPPINGS = {
    "StringTextExtractor": StringTextExtractor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringTextExtractor": "String Text Extractor",
}