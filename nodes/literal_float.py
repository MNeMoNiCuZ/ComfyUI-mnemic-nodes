class LiteralFloat:
    """
    A simple literal floating-point input node.
    Provides an input field for decimal values.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e10,
                    "max": 1e10,
                    "step": 0.001,
                    "tooltip": "Floating-point value."
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "get_value"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "A simple floating-point literal input. Enter any decimal number."

    def get_value(self, value):
        return (value,)

NODE_CLASS_MAPPINGS = {
    "LiteralFloat": LiteralFloat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LiteralFloat": "Literal Float",
}
