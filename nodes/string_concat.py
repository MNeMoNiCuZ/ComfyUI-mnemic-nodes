from comfy_api.latest import io


class StringConcat(io.ComfyNode):
    """
    Concatenates multiple strings together with an optional delimiter.
    Features dynamic input expansion - the node automatically adds new input slots
    as you connect strings, and removes unused slots from the end.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_StringConcat",
            display_name="🔗 String Concat / Append",
            category="⚡ MNeMiC Nodes",
            description="Concatenates multiple strings together with an optional delimiter. Connect strings to the inputs - more inputs automatically appear as needed. Empty inputs are skipped.",
            inputs=[
                io.String.Input(
                    "delimiter",
                    optional=True,
                    default="",
                    multiline=False,
                    tooltip="Optional separator to insert between concatenated strings (e.g., ', ' or ' | '). Leave empty for direct concatenation.",
                ),
                io.String.Input(
                    "string_0",
                    optional=True,
                    force_input=True,
                    tooltip="String input - connect strings here. More inputs appear as you connect.",
                ),
                io.String.Input(
                    "string_1",
                    optional=True,
                    force_input=True,
                    tooltip="String input - connect strings here. More inputs appear as you connect.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="concatenated_string", tooltip="Every connected string joined with the delimiter. Empty inputs are skipped."),
            ],
        )

    @classmethod
    def execute(cls, delimiter="", **kwargs) -> io.NodeOutput:
        string_parts = []

        sorted_keys = sorted(
            [k for k in kwargs.keys() if k.startswith("string_")],
            key=lambda x: int(x.split("_")[1])
        )

        for key in sorted_keys:
            value = kwargs.get(key, "")
            if isinstance(value, str) and value:
                string_parts.append(value)

        result = delimiter.join(string_parts)

        return io.NodeOutput(result)
