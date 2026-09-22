from comfy_api.latest import io

from ..utils.string_clean import process_text


class StringCleaning(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_StringCleaning",
            display_name="🧹 String Cleaning",
            category="⚡ MNeMiC Nodes",
            description="Cleans up the input text based on various stripping options.",
            inputs=[
                io.String.Input(
                    "input_string",
                    multiline=True,
                    force_input=True,
                    tooltip="Enter the text to be cleaned.",
                ),
                io.Boolean.Input(
                    "collapse_sequential_spaces",
                    default=False,
                    tooltip="Replace multiple spaces with a single space.",
                ),
                io.Boolean.Input(
                    "strip_leading_spaces",
                    default=False,
                    tooltip="Strip leading spaces from each line in the text.",
                ),
                io.Boolean.Input(
                    "strip_trailing_spaces",
                    default=False,
                    tooltip="Strip trailing spaces from each line in the text.",
                ),
                io.Boolean.Input(
                    "strip_empty_lines",
                    default=False,
                    tooltip="Remove empty or whitespace-only lines from the text.",
                ),
                io.Boolean.Input(
                    "strip_leading_symbols",
                    default=False,
                    tooltip="Strip leading punctuation symbols (, . ! ? : ;) from each line.",
                ),
                io.Boolean.Input(
                    "strip_trailing_symbols",
                    default=False,
                    tooltip="Strip trailing punctuation symbols (, . ! ? : ;) from each line.",
                ),
                io.Boolean.Input(
                    "strip_newlines",
                    default=False,
                    tooltip="Remove all newlines from the text.",
                ),
                io.Boolean.Input(
                    "replace_newlines_with_period_space",
                    default=False,
                    tooltip="Replace one or multiple newlines with a period followed by a space.",
                ),
                io.String.Input(
                    "strip_inside_tags",
                    multiline=True,
                    default="",
                    tooltip="Enter pairs of characters to strip content between them (one pair per line).\nExample Input:\n()\n[]\n{}\nInput: 'Hello (world) and [text]'\nOutput: 'Hello and'",
                    placeholder="Strip Content Between Character Pairs\nExample: ()",
                ),
                io.String.Input(
                    "strip_between_start",
                    multiline=True,
                    default="",
                    tooltip="Enter start tags to strip content from (one per line).\nExample: '<think>'\nInput: '<think>Hmm, so the user has asked us to...</think> The answer is 24'\nOutput: 'The answer is 24'",
                    placeholder="Strip Between Tags Start Tag\nExample: <think>",
                ),
                io.String.Input(
                    "strip_between_end",
                    multiline=True,
                    default="",
                    tooltip="Enter end tags to strip content to (one per line).\nMust match number of Start Tags lines.\nExample: '</think>'",
                    placeholder="Strip Between Tags End Tag\nExample: </think>",
                ),
                io.String.Input(
                    "strip_leading_custom",
                    multiline=True,
                    default="",
                    tooltip="Enter custom strings to strip from the start of each line.\nExample Input: 'Chapter'\nInput: 'Chapter 1: Hello\nChapter 2: World'\nOutput: '1: Hello\n2: World'",
                    placeholder="Remove Text From Line Starts\nExample: Chapter",
                ),
                io.String.Input(
                    "strip_trailing_custom",
                    multiline=True,
                    default="",
                    tooltip="Enter custom strings to strip from the end of each line.\nExample Input: 'END'\nInput: 'Hello END\nWorld END'\nOutput: 'Hello\nWorld'",
                    placeholder="Remove Text From Line Ends\nExample: END",
                ),
                io.String.Input(
                    "strip_all_custom",
                    multiline=True,
                    default="",
                    tooltip="Enter custom strings to remove throughout the text.\nExample Input: 'the'\nInput: 'the cat and the dog'\nOutput: 'cat and dog'",
                    placeholder="Remove Text Everywhere\nExample: the",
                ),
                io.String.Input(
                    "remove_text_before",
                    multiline=True,
                    default="",
                    tooltip="Enter markers to find. All text before (and including) these markers will be removed.\nExample: '<START>'\nInput: 'Header <START> Content'\nOutput: ' Content'",
                    placeholder="Remove Text Before Marker\nExample: <START>",
                ),
                io.String.Input(
                    "remove_text_after",
                    multiline=True,
                    default="",
                    tooltip="Enter markers to find. All text after (and including) these markers will be removed.\nExample: '<END>'\nInput: 'Content <END> Footer'\nOutput: 'Content '",
                    placeholder="Remove Text After Marker\nExample: <END>",
                ),
                io.String.Input(
                    "multiline_find",
                    multiline=True,
                    default="",
                    tooltip="Enter strings to find (one per line).\nExample: 'old' to be replaced with 'new'\nMust match number of Replace Strings lines",
                    placeholder="Find Text To Replace\nExample: old",
                ),
                io.String.Input(
                    "multiline_replace",
                    multiline=True,
                    default="",
                    tooltip="Enter replacement strings (one per line).\nExample: 'new' to replace 'old'\nMust match number of Find Strings lines",
                    placeholder="Replace Found Text With\nExample: new",
                ),
            ],
            outputs=[
                io.String.Output(
                    display_name="cleaned_string",
                    tooltip="The string after all the selected cleaning operations have been applied.",
                ),
            ],
        )

    @classmethod
    def execute(cls,
                input_string,
                collapse_sequential_spaces=False,
                strip_leading_spaces=False,
                strip_trailing_spaces=False,
                strip_empty_lines=False,
                strip_leading_symbols=False,
                strip_trailing_symbols=False,
                strip_newlines=False,
                replace_newlines_with_period_space=False,
                strip_inside_tags="",
                strip_between_start="",
                strip_between_end="",
                strip_leading_custom="",
                strip_trailing_custom="",
                strip_all_custom="",
                remove_text_before="",
                remove_text_after="",
                multiline_find="",
                multiline_replace=""):
        # Parse multiline custom strings into lists without stripping spaces
        strip_leading_custom_list = [line for line in strip_leading_custom.split('\n') if line != '']
        strip_trailing_custom_list = [line for line in strip_trailing_custom.split('\n') if line != '']
        strip_all_custom_list = [line for line in strip_all_custom.split('\n') if line != '']
        remove_text_before_list = [line.strip() for line in remove_text_before.split('\n') if line.strip()]
        remove_text_after_list = [line.strip() for line in remove_text_after.split('\n') if line.strip()]

        # Parse strip_inside_tags and validate
        strip_inside_tags_list = [line for line in strip_inside_tags.split('\n') if line != '']
        for tag_pair in strip_inside_tags_list:
            if len(tag_pair) != 2:
                raise ValueError(f"Each line in 'Strip Inside Tags' must have exactly two characters. Found '{tag_pair}'")

        # Parse strip between start/end tags
        strip_between_start_list = [line for line in strip_between_start.split('\n') if line != '']
        strip_between_end_list = [line for line in strip_between_end.split('\n') if line != '']

        # Validate that both start and end tag lists have the same number of lines
        if len(strip_between_start_list) != len(strip_between_end_list):
            raise ValueError("The number of lines in 'Strip Between Start Tags' and 'Strip Between End Tags' must be the same.")

        # Parse find and replace lists
        find_list = [line for line in multiline_find.split('\n')]
        replace_list = [line for line in multiline_replace.split('\n')]

        # Remove empty strings from find_list and adjust replace_list accordingly
        find_replace_pairs = [(f, r) for f, r in zip(find_list, replace_list) if f]
        if find_replace_pairs:
            find_list, replace_list = zip(*find_replace_pairs)
        else:
            find_list, replace_list = [], []

        # Validate that both find and replace lists have the same number of lines
        if len(find_list) != len(replace_list):
            raise ValueError("The number of lines in 'Find Strings' and 'Replace Strings' must be the same.")

        # Process the text
        cleaned_text = process_text(
            input_string=input_string,
            collapse_sequential_spaces=collapse_sequential_spaces,
            strip_leading_spaces=strip_leading_spaces,
            strip_trailing_spaces=strip_trailing_spaces,
            strip_empty_lines=strip_empty_lines,
            strip_leading_symbols=strip_leading_symbols,
            strip_trailing_symbols=strip_trailing_symbols,
            strip_newlines=strip_newlines,
            replace_newlines_with_period_space=replace_newlines_with_period_space,
            strip_inside_tags=strip_inside_tags_list,
            strip_between_start=strip_between_start_list,
            strip_between_end=strip_between_end_list,
            strip_leading_custom=strip_leading_custom_list,
            strip_trailing_custom=strip_trailing_custom_list,
            strip_all_custom=strip_all_custom_list,
            remove_text_before=remove_text_before_list,
            remove_text_after=remove_text_after_list,
            find_list=find_list,
            replace_list=replace_list
        )

        return io.NodeOutput(cleaned_text)
