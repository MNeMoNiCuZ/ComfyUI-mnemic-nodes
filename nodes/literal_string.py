class LiteralString:
    """
    A simple literal string input node.
    Provides a multiline text input field.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Text string value. Supports multiple lines."
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)
    FUNCTION = "get_value"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "A simple string literal input. Enter any text, supports multiple lines."

    def get_value(self, value):
        return (value,)

NODE_CLASS_MAPPINGS = {
    "LiteralString": LiteralString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LiteralString": "Literal String",
}
