import re

from comfy_api.latest import io


class StringTextSplitter(io.ComfyNode):
    """
    A node to split a string by the first occurrence of a delimiter.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_StringTextSplitter",
            display_name="✂️ String Text Splitter",
            category="⚡ MNeMiC Nodes",
            description="Splits a string by the first occurrence of a delimiter.\n\nExample:\n- input_string: part1|part2|part3\n- delimiter: |\n- first_chunk: part1\n- remainder: part2|part3",
            inputs=[
                io.String.Input(
                    "input_string",
                    multiline=True,
                    tooltip="The input text to split.",
                    placeholder="Text to be split...",
                ),
                io.String.Input(
                    "delimiter",
                    multiline=False,
                    tooltip="The character to split the text on. The node will split at the first time this character appears.",
                    placeholder="e.g., |",
                ),
                io.Boolean.Input(
                    "split_at_linebreaks",
                    default=False,
                    tooltip="If true, also split at line breaks. Can be used with or without a delimiter.",
                ),
                io.String.Input(
                    "target_indices",
                    default="",
                    multiline=False,
                    tooltip="Comma-separated list of indices (0-based) of chunks to extract. E.g., '0,2' for the first and third chunk. Leave empty to ignore.",
                    placeholder="e.g., 0,1,5",
                ),
            ],
            outputs=[
                io.String.Output(
                    display_name="first_chunk",
                    tooltip="The part of the string before the first delimiter.",
                ),
                io.String.Output(
                    display_name="remainder",
                    tooltip="The remainder string after the first delimiter.",
                ),
                io.String.Output(
                    display_name="chunk_list",
                    tooltip="A list of all items split by the delimiter.",
                ),
                io.String.Output(
                    display_name="targeted_chunks",
                    tooltip="A multiline string of chunks at the specified target indices.",
                ),
            ],
        )

    @classmethod
    def execute(cls, input_string, delimiter, split_at_linebreaks=False, target_indices="") -> io.NodeOutput:
        # Determine the regex pattern for splitting
        split_pattern = None

        if split_at_linebreaks:
            if not delimiter:
                split_pattern = r'[\n\r]+'  # Split by one or more linebreaks
            else:
                # Split by delimiter OR linebreaks
                split_pattern = f'{re.escape(delimiter)}|[\n\r]+'
        elif delimiter:
            # Only delimiter is active, escape it for regex
            split_pattern = re.escape(delimiter)

        if not split_pattern:
            # No delimiter and no linebreak splitting enabled
            return io.NodeOutput(input_string, "", [input_string], "")

        # Perform the first split (for first_chunk and remainder)
        parts = re.split(split_pattern, input_string, 1)

        first_chunk = parts[0]
        remainder = parts[1] if len(parts) > 1 else ""

        # Perform the full split (for chunk_list)
        all_parts = re.split(split_pattern, input_string)
        # Filter out empty strings that might result from regex splits (e.g., multiple delimiters in a row)
        all_parts = [p for p in all_parts if p]

        # Extract targeted chunks
        targeted_chunks_list = []
        if target_indices:
            try:
                indices_to_extract = [int(idx.strip()) for idx in target_indices.split(',') if idx.strip()]
                for idx in indices_to_extract:
                    if 0 <= idx < len(all_parts):
                        targeted_chunks_list.append(all_parts[idx])
            except ValueError:
                print(f"Warning: Invalid target_indices format: '{target_indices}'. Skipping targeted chunk extraction.")

        targeted_chunks_output = "\n".join(targeted_chunks_list)

        return io.NodeOutput(first_chunk, remainder, all_parts, targeted_chunks_output)
