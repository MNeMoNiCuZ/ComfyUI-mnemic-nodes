class StringConcat:
    """
    Concatenates multiple strings together with an optional delimiter.
    Features dynamic input expansion - the node automatically adds new input slots
    as you connect strings, and removes unused slots from the end.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "delimiter": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Optional separator to insert between concatenated strings (e.g., ', ' or ' | '). Leave empty for direct concatenation."
                }),
                "string_0": ("STRING", {
                    "forceInput": True,
                    "tooltip": "String input - connect strings here. More inputs appear as you connect."
                }),
                "string_1": ("STRING", {
                    "forceInput": True,
                    "tooltip": "String input - connect strings here. More inputs appear as you connect."
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("concatenated_string",)
    FUNCTION = "concatenate_strings"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Concatenates multiple strings together with an optional delimiter. Connect strings to the inputs - more inputs automatically appear as needed. Empty inputs are skipped."

    def concatenate_strings(self, delimiter="", **kwargs):
        string_parts = []
        
        sorted_keys = sorted(
            [k for k in kwargs.keys() if k.startswith("string_")],
            key=lambda x: int(x.split("_")[1])
        )
        
        for key in sorted_keys:
            value = kwargs.get(key, "")
            if isinstance(value, str) and value:
                string_parts.append(value)
        
        result = delimiter.join(string_parts)
        
        return (result,)

NODE_CLASS_MAPPINGS = {
    "StringConcat": StringConcat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringConcat": "String Concat / Append",
}
