import random

class RandomBool:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "true_probability": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Probability of returning True (0.0 = always False, 1.0 = always True, 0.5 = 50/50)."
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

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("random_bool",)
    FUNCTION = "generate_random_bool"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Generates a random boolean value (True/False). Adjust probability to weight the randomness. Use seed for reproducibility or -1 for random results."

    def generate_random_bool(self, true_probability, seed=-1):
        if seed >= 0:
            rng = random.Random(seed)
            result = rng.random() < true_probability
        else:
            result = random.random() < true_probability

        return (result,)

NODE_CLASS_MAPPINGS = {
    "RandomBool": RandomBool,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomBool": "Random Bool",
}
