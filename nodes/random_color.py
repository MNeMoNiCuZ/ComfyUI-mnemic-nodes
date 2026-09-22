import random

from comfy_api.latest import io


class RandomColor(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomColor",
            display_name="🎲 Random Color",
            category="⚡ MNeMiC Nodes",
            description="Generates a random RGB color. Returns both hex format (#RRGGBB) and individual RGB values (0-255). Use seed for reproducibility or -1 for random results.",
            inputs=[
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
                io.String.Output(display_name="hex_color", tooltip="The rolled colour as #RRGGBB."),
                io.Int.Output(display_name="red", tooltip="Red channel of the rolled colour, 0-255."),
                io.Int.Output(display_name="green", tooltip="Green channel of the rolled colour, 0-255."),
                io.Int.Output(display_name="blue", tooltip="Blue channel of the rolled colour, 0-255."),
            ],
        )

    @classmethod
    def execute(cls, seed=-1) -> io.NodeOutput:
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

        return io.NodeOutput(hex_color, r, g, b)
