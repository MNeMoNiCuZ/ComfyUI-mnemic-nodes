from comfy_api.latest import io


class FindReplaceText(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_FindReplaceText",
            display_name="🔄 Find / Replace Text",
            category="⚡ MNeMiC Nodes",
            description="Replaces every occurrence of literal text with another string.",
            inputs=[
                io.String.Input(
                    "string", default="", multiline=False,
                    tooltip="The text to process.",
                ),
                io.String.Input(
                    "find", default="", multiline=False,
                    tooltip="Literal text to find. Matching is case-sensitive; empty leaves the string unchanged.",
                ),
                io.String.Input(
                    "replace", default="", multiline=False,
                    tooltip="Replacement text for every match. Empty deletes the matched text.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="string", tooltip="The text with every matching occurrence replaced."),
            ],
        )

    @classmethod
    def execute(cls, string: str, find: str, replace: str) -> io.NodeOutput:
        return io.NodeOutput(string.replace(find, replace) if find else string)
