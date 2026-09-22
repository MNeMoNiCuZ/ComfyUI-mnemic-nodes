import random

from comfy_api.latest import io


class RandomFloatInRange(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomFloatInRange",
            display_name="🎲 Random Float in Range",
            category="⚡ MNeMiC Nodes",
            description="Generates a random floating-point number within the specified range. Optionally round to specified decimal places. Use seed for reproducibility or -1 for random results.",
            inputs=[
                io.Float.Input(
                    "min_value",
                    default=0.0,
                    min=-1e10,
                    max=1e10,
                    step=0.001,
                    tooltip="Minimum value for the random float (inclusive).",
                ),
                io.Float.Input(
                    "max_value",
                    default=1.0,
                    min=-1e10,
                    max=1e10,
                    step=0.001,
                    tooltip="Maximum value for the random float (inclusive).",
                ),
                io.Int.Input(
                    "decimals",
                    optional=True,
                    default=-1,
                    min=-1,
                    max=10,
                    tooltip="Number of decimal places to round to. Use -1 for no rounding (full precision).",
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
                io.Float.Output(display_name="random_float", tooltip="The rolled number, inside the range set above."),
            ],
        )

    @classmethod
    def execute(cls, min_value, max_value, decimals=-1, seed=-1) -> io.NodeOutput:
        if min_value > max_value:
            min_value, max_value = max_value, min_value

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.uniform(min_value, max_value)
        else:
            result = random.uniform(min_value, max_value)

        if decimals >= 0:
            result = round(result, decimals)

        return io.NodeOutput(result)
