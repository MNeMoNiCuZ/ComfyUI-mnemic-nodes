class LiteralInt:
    """
    A simple literal integer input node.
    Provides an input field for integer values.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("INT", {
                    "default": 0,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Integer value."
                }),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "get_value"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "A simple integer literal input. Enter any whole number."

    def get_value(self, value):
        return (value,)

NODE_CLASS_MAPPINGS = {
    "LiteralInt": LiteralInt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LiteralInt": "Literal Int",
}
