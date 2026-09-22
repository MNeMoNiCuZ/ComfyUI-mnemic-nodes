from comfy_api.latest import io


class LiteralBool(io.ComfyNode):
    """
    A simple literal boolean input node.
    Provides a toggle for True/False values.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LiteralBool",
            display_name="✏️ Literal Bool",
            category="⚡ MNeMiC Nodes",
            description="A simple boolean literal input. Toggle between True and False.",
            inputs=[
                io.Boolean.Input(
                    "value",
                    default=False,
                    tooltip="Boolean value (True or False).",
                ),
            ],
            outputs=[
                io.Boolean.Output(display_name="value", tooltip="The toggle value, passed straight through."),
            ],
        )

    @classmethod
    def execute(cls, value) -> io.NodeOutput:
        return io.NodeOutput(value)
