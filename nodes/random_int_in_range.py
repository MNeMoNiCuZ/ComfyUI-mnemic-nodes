import random

class RandomIntInRange:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("INT", {
                    "default": 0,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Minimum value for the random integer (inclusive)."
                }),
                "max_value": ("INT", {
                    "default": 100,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Maximum value for the random integer (inclusive)."
                }),
            },
            "optional": {
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Seed for random number generator. Use -1 for random seed (different each time), or set a specific value for reproducibility."
                }),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("random_int",)
    FUNCTION = "generate_random_int"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Generates a random integer within the specified range (min to max, inclusive). Use seed for reproducibility or -1 for random results."

    def generate_random_int(self, min_value, max_value, seed=-1):
        if min_value > max_value:
            min_value, max_value = max_value, min_value

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.randint(min_value, max_value)
        else:
            result = random.randint(min_value, max_value)

        return (result,)

NODE_CLASS_MAPPINGS = {
    "RandomIntInRange": RandomIntInRange,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomIntInRange": "Random Int in Range",
}
