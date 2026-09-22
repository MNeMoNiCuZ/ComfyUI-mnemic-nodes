from comfy_api.latest import io


class LiteralString(io.ComfyNode):
    """
    A simple literal string input node.
    Provides a multiline text input field.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LiteralString",
            display_name="✏️ Literal String",
            category="⚡ MNeMiC Nodes",
            description="A simple string literal input. Enter any text, supports multiple lines.",
            inputs=[
                io.String.Input(
                    "value",
                    default="",
                    multiline=True,
                    tooltip="Text string value. Supports multiple lines.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="value", tooltip="The text entered above, passed straight through."),
            ],
        )

    @classmethod
    def execute(cls, value) -> io.NodeOutput:
        return io.NodeOutput(value)
