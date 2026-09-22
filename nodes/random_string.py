import random

from comfy_api.latest import io


class RandomString(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomString",
            display_name="🎲 Random String",
            category="⚡ MNeMiC Nodes",
            description="Randomly selects one string from a newline-separated list of options. Empty lines are ignored. Use seed for reproducibility or -1 for random results.",
            inputs=[
                io.String.Input(
                    "input_list",
                    multiline=True,
                    default="option1\noption2\noption3",
                    tooltip="Newline-separated list of strings to randomly choose from. Each line is one option.",
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
                io.String.Output(display_name="random_choice", tooltip="One line picked at random from the list above. Empty if the list has no usable lines."),
            ],
        )

    @classmethod
    def execute(cls, input_list, seed=-1) -> io.NodeOutput:
        lines = [line.strip() for line in input_list.split('\n') if line.strip()]

        if not lines:
            return io.NodeOutput("")

        if seed >= 0:
            rng = random.Random(seed)
            result = rng.choice(lines)
        else:
            result = random.choice(lines)

        return io.NodeOutput(result)
