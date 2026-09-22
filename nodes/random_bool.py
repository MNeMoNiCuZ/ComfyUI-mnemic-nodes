import random

from comfy_api.latest import io


class RandomBool(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomBool",
            display_name="🎲 Random Bool",
            category="⚡ MNeMiC Nodes",
            description="Generates a random boolean value (True/False). Adjust probability to weight the randomness. Use seed for reproducibility or -1 for random results.",
            inputs=[
                io.Float.Input(
                    "true_probability",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Probability of returning True (0.0 = always False, 1.0 = always True, 0.5 = 50/50).",
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
                io.Boolean.Output(display_name="random_bool", tooltip="The rolled value: True with the probability set above."),
            ],
        )

    @classmethod
    def execute(cls, true_probability, seed=-1) -> io.NodeOutput:
        if seed >= 0:
            rng = random.Random(seed)
            result = rng.random() < true_probability
        else:
            result = random.random() < true_probability

        return io.NodeOutput(result)
