from comfy_api.latest import io


class LiteralFloat(io.ComfyNode):
    """
    A simple literal floating-point input node.
    Provides an input field for decimal values.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LiteralFloat",
            display_name="✏️ Literal Float",
            category="⚡ MNeMiC Nodes",
            description="A simple floating-point literal input. Enter any decimal number.",
            inputs=[
                io.Float.Input(
                    "value",
                    default=0.0,
                    min=-1e10,
                    max=1e10,
                    step=0.001,
                    tooltip="Floating-point value.",
                ),
            ],
            outputs=[
                io.Float.Output(display_name="value", tooltip="The number entered above, passed straight through."),
            ],
        )

    @classmethod
    def execute(cls, value) -> io.NodeOutput:
        return io.NodeOutput(value)
