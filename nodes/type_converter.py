import re
import time

class TypeConverter:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("*", {
                    "tooltip": (
                        "The value to be converted.\n"
                        "INT -> INT, FLOAT, STRING, BOOLEAN\n"
                        "FLOAT -> INT (rounded), FLOAT, STRING, BOOLEAN\n"
                        "STRING -> INT (if parsable), FLOAT (if parsable), STRING, BOOLEAN (if 'true', 'false', etc.)\n"
                        "BOOLEAN -> INT (0 or 1), FLOAT (0.0 or 1.0), STRING, BOOLEAN"
                    )
                }),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING", "BOOLEAN",)
    RETURN_NAMES = ("INT_OUT", "FLOAT_OUT", "STRING_OUT", "BOOLEAN_OUT",)
    OUTPUT_TOOLTIPS = {
        "INT_OUT": "Integer output. Can be converted from INT, FLOAT (rounded), STRING (if parsable), or BOOLEAN (0 or 1).",
        "FLOAT_OUT": "Float output. Can be converted from INT, FLOAT, STRING (if parsable), or BOOLEAN (0.0 or 1.0).",
        "STRING_OUT": "String output. Can be converted from any input type.",
        "BOOLEAN_OUT": "Boolean output. Can be converted from INT (0 is False), FLOAT (0.0 is False), STRING ('true', 'false', etc.), or BOOLEAN."
    }
    FUNCTION = "convert"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "A versatile type converter that processes multiple inputs and converts them to various output formats. For each output type, it returns the first successfully converted value from the inputs."

    def IS_CHANGED(self, *args, **kwargs):
        return time.time()

    def _to_int(self, value):
        """Converts a value to an integer."""
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                word_map = {
                    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
                    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
                }
                return word_map.get(value.lower())
        return None

    def _to_float(self, value):
        """Converts a value to a float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None

    def _to_string(self, value):
        """Converts a value to a string."""
        return str(value)

    def _to_boolean(self, value):
        """Converts a value to a boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            val_lower = value.lower()
            if val_lower in ["true", "yes", "1"]:
                return True
            if val_lower in ["false", "no", "0"]:
                return False
        return None

    def convert(self, input):
        """
        Performs type conversion on the provided input.
        """
        outputs = {
            "INT_OUT": self._to_int(input),
            "FLOAT_OUT": self._to_float(input),
            "STRING_OUT": self._to_string(input),
            "BOOLEAN_OUT": self._to_boolean(input)
        }

        return (outputs["INT_OUT"], outputs["FLOAT_OUT"], outputs["STRING_OUT"], outputs["BOOLEAN_OUT"])
