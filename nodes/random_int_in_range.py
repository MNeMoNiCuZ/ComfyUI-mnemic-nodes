import random

from comfy_api.latest import io


class RandomIntInRange(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomIntInRange",
            display_name="🎲 Random Int in Range",
            category="⚡ MNeMiC Nodes",
            description="Generates a random integer within the specified range (min to max, inclusive). Use seed for reproducibility or -1 for random results.",
            inputs=[
                io.Int.Input(
                    "min_value",
                    default=0,
                    min=-0xffffffffffffffff,
                    max=0xffffffffffffffff,
                    tooltip="Minimum value for the random integer (inclusive).",
                ),
                io.Int.Input(
                    "max_value",
                    default=100,
                    min=-0xffffffffffffffff,
                    max=0xffffffffffffffff,
                    tooltip="Maximum value for the random integer (inclusive).",
                ),
                io.Int.Input(
                    "seed",
                    optional=True,
                    default=-1,
                    min=-1,
                    max=0xffffffffffffffff,
                    tooltip="Seed for random number generator. Use -1 for random seed (different each time), or set a specific value for reproducibility.",
                ),
            ],
            outputs=[
                io.Int.Output(display_name="random_int", tooltip="The rolled number, inside the range set above."),
            ],
        )

    @classmethod
    def execute(cls, min_value, max_value, seed=-1) -> io.NodeOutput:
        if min_value > max_value:
            min_value, max_value = max_value, min_value

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.randint(min_value, max_value)
        else:
            result = random.randint(min_value, max_value)

        return io.NodeOutput(result)
