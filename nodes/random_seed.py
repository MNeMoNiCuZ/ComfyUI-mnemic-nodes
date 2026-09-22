import random
import time

from comfy_api.latest import io


class RandomSeed(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_RandomSeed",
            display_name="🎲 Random Seed",
            category="⚡ MNeMiC Nodes",
            description="Generates a random seed value (0 to 2^64-1). Useful for feeding into other nodes that accept seed inputs. Regenerates on each execution.",
            inputs=[],
            outputs=[
                io.Int.Output(display_name="seed", tooltip="A fresh random seed, 0 to 2^64-1. Re-rolls on every run."),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return time.time()

    @classmethod
    def execute(cls) -> io.NodeOutput:
        return io.NodeOutput(random.randint(0, 0xffffffffffffffff))
