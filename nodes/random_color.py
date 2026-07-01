import random

class RandomColor:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Seed for random number generator. Use -1 for random seed (different each time), or set a specific value for reproducibility."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "INT",)
    RETURN_NAMES = ("hex_color", "red", "green", "blue",)
    FUNCTION = "generate_random_color"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Generates a random RGB color. Returns both hex format (#RRGGBB) and individual RGB values (0-255). Use seed for reproducibility or -1 for random results."

    def generate_random_color(self, seed=-1):
        if seed >= 0:
            rng = random.Random(seed)
            r = rng.randint(0, 255)
            g = rng.randint(0, 255)
            b = rng.randint(0, 255)
        else:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)

        hex_color = f"#{r:02X}{g:02X}{b:02X}"

        return (hex_color, r, g, b)

NODE_CLASS_MAPPINGS = {
    "RandomColor": RandomColor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomColor": "Random Color",
}
