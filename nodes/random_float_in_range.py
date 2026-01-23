import random

class RandomFloatInRange:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e10,
                    "max": 1e10,
                    "step": 0.001,
                    "tooltip": "Minimum value for the random float (inclusive)."
                }),
                "max_value": ("FLOAT", {
                    "default": 1.0,
                    "min": -1e10,
                    "max": 1e10,
                    "step": 0.001,
                    "tooltip": "Maximum value for the random float (inclusive)."
                }),
            },
            "optional": {
                "decimals": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 10,
                    "tooltip": "Number of decimal places to round to. Use -1 for no rounding (full precision)."
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Seed for random number generator. Use -1 for random seed (different each time), or set a specific value for reproducibility."
                }),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("random_float",)
    FUNCTION = "generate_random_float"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Generates a random floating-point number within the specified range. Optionally round to specified decimal places. Use seed for reproducibility or -1 for random results."

    def generate_random_float(self, min_value, max_value, decimals=-1, seed=-1):
        if min_value > max_value:
            min_value, max_value = max_value, min_value

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.uniform(min_value, max_value)
        else:
            result = random.uniform(min_value, max_value)

        if decimals >= 0:
            result = round(result, decimals)

        return (result,)

NODE_CLASS_MAPPINGS = {
    "RandomFloatInRange": RandomFloatInRange,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomFloatInRange": "Random Float in Range",
}
