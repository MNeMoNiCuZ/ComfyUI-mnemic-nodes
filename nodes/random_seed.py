import random
import time

class RandomSeed:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed",)
    FUNCTION = "generate_random_seed"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Generates a random seed value (0 to 2^64-1). Useful for feeding into other nodes that accept seed inputs. Regenerates on each execution."

    def generate_random_seed(self):
        result = random.randint(0, 0xffffffffffffffff)
        return (result,)

NODE_CLASS_MAPPINGS = {
    "RandomSeed": RandomSeed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomSeed": "Random Seed",
}
