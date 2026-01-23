import random

class RandomString:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_list": ("STRING", {
                    "multiline": True,
                    "default": "option1\noption2\noption3",
                    "tooltip": "Newline-separated list of strings to randomly choose from. Each line is one option."
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

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("random_choice",)
    FUNCTION = "choose_random_string"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Randomly selects one string from a newline-separated list of options. Empty lines are ignored. Use seed for reproducibility or -1 for random results."

    def choose_random_string(self, input_list, seed=-1):
        lines = [line.strip() for line in input_list.split('\n') if line.strip()]
        
        if not lines:
            return ("",)

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.choice(lines)
        else:
            result = random.choice(lines)

        return (result,)

NODE_CLASS_MAPPINGS = {
    "RandomString": RandomString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomString": "Random String",
}
