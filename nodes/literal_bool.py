class LiteralBool:
    """
    A simple literal boolean input node.
    Provides a toggle for True/False values.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Boolean value (True or False)."
                }),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("value",)
    FUNCTION = "get_value"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "A simple boolean literal input. Toggle between True and False."

    def get_value(self, value):
        return (value,)

NODE_CLASS_MAPPINGS = {
    "LiteralBool": LiteralBool,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LiteralBool": "Literal Bool",
}
