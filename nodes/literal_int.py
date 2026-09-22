from comfy_api.latest import io


class LiteralInt(io.ComfyNode):
    """
    A simple literal integer input node.
    Provides an input field for integer values.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LiteralInt",
            display_name="✏️ Literal Int",
            category="⚡ MNeMiC Nodes",
            description="A simple integer literal input. Enter any whole number.",
            inputs=[
                io.Int.Input(
                    "value",
                    default=0,
                    min=-0xffffffffffffffff,
                    max=0xffffffffffffffff,
                    tooltip="Integer value.",
                ),
            ],
            outputs=[
                io.Int.Output(display_name="value", tooltip="The number entered above, passed straight through."),
            ],
        )

    @classmethod
    def execute(cls, value) -> io.NodeOutput:
        return io.NodeOutput(value)
