import re

from comfy_api.latest import io


class StringTextExtractor(io.ComfyNode):
    """
    A node to extract the first occurrence of text between specified delimiters.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_StringTextExtractor",
            display_name="✂️ String Text Extractor",
            category="⚡ MNeMiC Nodes",
            description="Extracts the text between two delimiter characters, e.g. 'red fox' from 'a [red fox] in the snow' with delimiters []. Also outputs the leftover text and a list of every match.",
            inputs=[
                io.String.Input(
                    "input_string",
                    multiline=True,
                    tooltip="The text to search. The content of the first delimiter pair comes out as extracted_text, the rest as remainder_text.",
                    placeholder="A photo of a [red fox] in the snow.\n\nWith delimiters [] this gives:\nextracted_text: red fox\nremainder_text: A photo of a  in the snow.",
                ),
                io.String.Input(
                    "delimiters",
                    multiline=False,
                    tooltip="Two characters: the opening one, then the closing one, e.g. [] () <> {}. Use the same character twice for marks like ** or \"\". Fewer than two characters extracts nothing.",
                    placeholder="[]  (opening + closing character)",
                ),
            ],
            outputs=[
                io.String.Output(
                    display_name="extracted_text",
                    tooltip="The content found inside the first instance of the specified delimiters.",
                ),
                io.String.Output(
                    display_name="remainder_text",
                    tooltip="The rest of the text after the extracted content and its delimiters have been removed.",
                ),
                io.String.Output(
                    display_name="extracted_list",
                    tooltip="A list of all items found between the delimiters.",
                ),
            ],
        )

    @classmethod
    def execute(cls, input_string, delimiters) -> io.NodeOutput:
        if not delimiters or len(delimiters) < 2:
            # If delimiters are invalid, return original text as remainder
            return io.NodeOutput("", input_string, [])

        start_delim = re.escape(delimiters[0])
        end_delim = re.escape(delimiters[-1])

        # Find all non-overlapping matches for the list output
        all_captures = re.findall(f"{start_delim}(.*?){end_delim}", input_string, re.DOTALL)

        # Non-greedy search for the content between the first pair of delimiters
        match = re.search(f"{start_delim}(.*?){end_delim}", input_string, re.DOTALL)

        if match:
            extracted_text = match.group(1)
            # The remainder is the part before the match plus the part after the match
            remainder_text = input_string[:match.start()] + input_string[match.end():]
            return io.NodeOutput(extracted_text, remainder_text, all_captures)
        else:
            # No match found
            return io.NodeOutput("", input_string, [])
