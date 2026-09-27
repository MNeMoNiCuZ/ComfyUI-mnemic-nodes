import json
import re

from comfy_api.latest import io

from ..utils.string_clean import process_text


_CASE_TOOLTIPS = {
    "lowercase": "Lowercase letters; keep punctuation and spacing. Example: 'Red FOX' -> 'red fox'.",
    "UPPERCASE": "Uppercase letters; keep punctuation and spacing. Example: 'Red fox' -> 'RED FOX'.",
    "Title Case": "Capitalize each word; keep punctuation and spacing. Example: 'the red fox' -> 'The Red Fox'.",
    "Sentence case": "Lowercase text, then capitalize the first letter and letters after . ! ? or a line break. Example: 'HELLO. GOODBYE!' -> 'Hello. Goodbye!'.",
    "camelCase": "Join words with an initial lowercase word and capitalized following words. Example: 'red fox' -> 'redFox'.",
    "PascalCase": "Join words with each word capitalized. Example: 'red fox' -> 'RedFox'.",
    "snake_case": "Join lowercase words with underscores. Example: 'RedFox' -> 'red_fox'.",
    "CONSTANT_CASE": "Join uppercase words with underscores. Example: 'red fox' -> 'RED_FOX'.",
    "kebab-case": "Join lowercase words with hyphens. Example: 'red fox' -> 'red-fox'.",
    "Train-Case": "Join capitalized words with hyphens. Example: 'red fox' -> 'Red-Fox'.",
    "dot.case": "Join lowercase words with dots. Example: 'red fox' -> 'red.fox'.",
    "tOGGLE cASE": "Invert each letter's case; keep punctuation and spacing. Example: 'Red FOX' -> 'rED fox'.",
}


def _change_case(text, case_format):
    if case_format == "lowercase":
        return text.lower()
    if case_format == "UPPERCASE":
        return text.upper()
    if case_format == "tOGGLE cASE":
        return text.swapcase()
    if case_format == "Title Case":
        return re.sub(r"[^\W_]+(?:'[^\W_]+)*", lambda match: match.group().capitalize(), text)
    if case_format == "Sentence case":
        result = []
        capitalize_next = True
        for char in text.lower():
            if char.isalpha() and capitalize_next:
                result.append(char.upper())
                capitalize_next = False
            else:
                result.append(char)
            if char in ".!?\r\n":
                capitalize_next = True
        return "".join(result)
    if case_format not in _CASE_TOOLTIPS:
        raise ValueError(f"Unknown case format: {case_format}")

    # Split punctuation, whitespace, camelCase and acronym boundaries while
    # keeping Unicode letters and digits. HTTPServer becomes HTTP + Server.
    words = []
    for token in re.findall(r"[^\W_]+", text):
        start = 0
        for index in range(1, len(token)):
            previous, current = token[index - 1], token[index]
            following = token[index + 1] if index + 1 < len(token) else ""
            if current.isupper() and (previous.islower() or previous.isdigit() or (previous.isupper() and following.islower())):
                words.append(token[start:index].lower())
                start = index
        words.append(token[start:].lower())
    if case_format == "camelCase":
        return words[0] + "".join(word.capitalize() for word in words[1:]) if words else ""
    if case_format == "PascalCase":
        return "".join(word.capitalize() for word in words)
    if case_format == "CONSTANT_CASE":
        return "_".join(words).upper()
    if case_format == "Train-Case":
        return "-".join(word.capitalize() for word in words)
    return {"snake_case": "_", "kebab-case": "-", "dot.case": "."}[case_format].join(words)


_SIMPLE_OPERATIONS = {
    "Collapse Spaces": ("collapse_sequential_spaces", "Replaces consecutive spaces with one space. Keeps tabs and line breaks."),
    "Trim Line Starts": ("strip_leading_spaces", "Removes whitespace from the start of each line."),
    "Trim Line Ends": ("strip_trailing_spaces", "Removes whitespace from the end of each line."),
    "Remove Empty Lines": ("strip_empty_lines", "Removes empty lines and lines containing only whitespace."),
    "Remove Leading Punctuation": ("strip_leading_symbols", "Removes consecutive , . ! ? : ; characters at the start of each line."),
    "Remove Trailing Punctuation": ("strip_trailing_symbols", "Removes consecutive , . ! ? : ; characters at the end of each line."),
    "Remove Line Breaks": ("strip_newlines", "Deletes line breaks without inserting spaces."),
    "Line Breaks to Sentences": ("replace_newlines_with_period_space", "Replaces each run of line breaks with a period and a space."),
}

_TEXT_OPERATIONS = {
    "Remove Line Prefix": ("strip_leading_custom", "Removes matching text repeatedly from the start of each line. Matching is case-sensitive."),
    "Remove Line Suffix": ("strip_trailing_custom", "Removes matching text repeatedly from the end of each line. Matching is case-sensitive."),
    "Remove Text": ("strip_all_custom", "Removes every occurrence of the specified text. Matching is case-sensitive."),
    "Remove Before Marker": ("remove_text_before", "Removes everything before the first occurrence of each marker, including the marker."),
    "Remove After Marker": ("remove_text_after", "Removes everything after the first occurrence of each marker, including the marker."),
}

_OPERATION_TOOLTIPS = {
    **{name: tooltip for name, (_, tooltip) in _SIMPLE_OPERATIONS.items()},
    **{name: tooltip for name, (_, tooltip) in _TEXT_OPERATIONS.items()},
    "Remove Bracketed Content": "Removes character pairs and the text between them, including across lines. Matches the nearest closing character.",
    "Remove Between Tags": "Removes opening tags, closing tags and the text between them, including across lines. Matches the nearest closing tag.",
    "Find and Replace": "Replaces literal text using one find/replacement pair per line. Matching is case-sensitive.",
    "Remove From Start Until": "Removes text from the start of the whole string through the first delimiter. Empty or missing delimiters leave text unchanged.",
    "Remove From End Until": "Removes text from the end of the whole string back through the last delimiter. Empty or missing delimiters leave text unchanged.",
    "Trim Whitespace": "Removes whitespace from both ends of the whole string, including blank lines at its edges.",
    "Trim Each Line": "Removes whitespace from both ends of every line, keeping line breaks.",
    "Normalize Whitespace": "Replaces runs of spaces, tabs and line breaks with one space, then trims both ends.",
    "Normalize Line Breaks": "Converts Windows CRLF and old Mac CR line breaks to LF, keeping all lines.",
    "Remove Duplicate Lines": "Keeps the first occurrence of each exact line, in original order. Matching is case-sensitive and spaces are significant.",
    "Case": "Converts text to the selected case format, including word-separated and joined formats.",
}

_OPERATION_EXAMPLES = {
    "Collapse Spaces": "'red   fox' -> 'red fox'.",
    "Remove All Spaces": "'red fox' -> 'redfox'.",
    "Trim Line Starts": "'  red fox' -> 'red fox'.",
    "Trim Line Ends": "'red fox  ' -> 'red fox'.",
    "Remove Empty Lines": "'red\\n\\nfox' -> 'red\\nfox' (\\n means a line break).",
    "Remove Leading Punctuation": "'...Hello' -> 'Hello'.",
    "Remove Trailing Punctuation": "'Hello!!!' -> 'Hello'.",
    "Remove Line Breaks": "'red\\nfox' -> 'redfox' (\\n means a line break).",
    "Line Breaks to Sentences": "'Hello\\nWorld' -> 'Hello. World' (\\n means a line break).",
    "Remove Line Prefix": "Text 'Chapter ': 'Chapter 1: Hello' -> '1: Hello'. The space after Chapter is included.",
    "Remove Line Suffix": "Text ' END': 'Hello END' -> 'Hello'. The space before END is included.",
    "Remove Text": "Text 'cat': 'cat and cat' -> ' and '. Surrounding spaces stay.",
    "Remove Before Marker": "Marker '<START>': 'Header<START>Hello' -> 'Hello'.",
    "Remove After Marker": "Marker '<END>': 'Hello<END>Footer' -> 'Hello'.",
    "Remove Bracketed Content": "Pairs '()': 'Hello (draft)world' -> 'Hello world'.",
    "Remove Between Tags": "Tags '<think>' and '</think>': '<think>draft</think>Hello' -> 'Hello'.",
    "Find and Replace": "Find 'cat', Replace With 'dog': 'a cat' -> 'a dog'.",
    "Remove From Start Until": "Delimiter '/': 'folder/sub/file.txt' -> 'sub/file.txt'. Keep Delimiter on gives '/sub/file.txt'.",
    "Remove From End Until": "Delimiter '.': 'photo.v2.png' -> 'photo.v2'. Keep Delimiter on gives 'photo.v2.'.",
    "Trim Whitespace": "'  red fox  ' -> 'red fox'.",
    "Trim Each Line": "'  red  \\n  fox  ' -> 'red\\nfox' (\\n means a line break).",
    "Normalize Whitespace": "'  red\\t fox\\n ' -> 'red fox' (\\t is a tab, \\n a line break).",
    "Normalize Line Breaks": "'red\\r\\nfox\\rcat' -> 'red\\nfox\\ncat' (\\r is CR, \\n is LF).",
    "Remove Duplicate Lines": "'red\\nfox\\nred' -> 'red\\nfox' (\\n means a line break).",
    "Case": "'red fox' -> 'redFox' with camelCase, 'RedFox' with PascalCase, or 'RED_FOX' with CONSTANT_CASE.",
}
_OPERATION_TOOLTIPS["Remove All Spaces"] = "Removes every ordinary space. Keeps tabs and line breaks."
_OPERATION_TOOLTIPS = {
    name: f"{tooltip}\nExample: {_OPERATION_EXAMPLES[name]}"
    for name, tooltip in _OPERATION_TOOLTIPS.items()
}

_OPERATION_GROUPS = {
    "Whitespace": ["Collapse Spaces", "Trim Whitespace", "Trim Each Line", "Trim Line Starts", "Trim Line Ends", "Normalize Whitespace", "Remove All Spaces"],
    "Lines": ["Normalize Line Breaks", "Remove Empty Lines", "Remove Duplicate Lines", "Remove Line Breaks", "Line Breaks to Sentences"],
    "Punctuation": ["Remove Leading Punctuation", "Remove Trailing Punctuation"],
    "Text Removal": ["Remove Line Prefix", "Remove Line Suffix", "Remove Text", "Remove Before Marker", "Remove After Marker", "Remove From Start Until", "Remove From End Until", "Remove Bracketed Content", "Remove Between Tags"],
    "Replacement and Case": ["Find and Replace", "Case"],
}


class StringCleaning(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        options = [io.DynamicCombo.Option(name, []) for name in _SIMPLE_OPERATIONS]
        options.insert(1, io.DynamicCombo.Option("Remove All Spaces", []))
        options.extend(io.DynamicCombo.Option(name, []) for name in (
            "Trim Whitespace", "Trim Each Line", "Normalize Whitespace", "Normalize Line Breaks",
            "Remove Duplicate Lines",
        ))
        options.extend([
            io.DynamicCombo.Option("Remove Bracketed Content", [
                io.String.Input(
                    "pairs", display_name="Character Pairs", default="", multiline=True,
                    tooltip="Exactly two characters per nonempty line. Empty leaves the text unchanged.\nExample: pairs '()' turn 'Hello (draft)world' into 'Hello world'.",
                    placeholder="()\n[]\n{}",
                ),
            ]),
            io.DynamicCombo.Option("Remove Between Tags", [
                io.String.Input(
                    "start_tags", display_name="Opening Tags", default="", multiline=True,
                    tooltip="One opening tag per line, paired with Closing Tags. Both empty leaves text unchanged.\nExample: '<think>' with '</think>' removes '<think>draft</think>' from '<think>draft</think>Hello'.",
                ),
                io.String.Input(
                    "end_tags", display_name="Closing Tags", default="", multiline=True,
                    tooltip="One closing tag per line; match the number of nonempty Opening Tags lines.\nExample: '</think>' with '<think>' turns '<think>draft</think>Hello' into 'Hello'.",
                ),
            ]),
        ])
        for name in _TEXT_OPERATIONS:
            is_marker = name in ("Remove Before Marker", "Remove After Marker")
            options.append(io.DynamicCombo.Option(name, [
                io.String.Input(
                    "text", display_name="Markers" if is_marker else "Text",
                    default="", multiline=True,
                    tooltip=(
                        "One marker per line, applied in order. Surrounding whitespace is ignored; missing markers leave text unchanged."
                        if is_marker else
                        "One literal string per line, applied in order. Spaces are significant; empty lines are ignored."
                    ) + f"\nExample: {_OPERATION_EXAMPLES[name]}",
                ),
            ]))
        for name, delimiter in (("Remove From Start Until", "/"), ("Remove From End Until", ".")):
            options.append(io.DynamicCombo.Option(name, [
                io.String.Input(
                    "delimiter", display_name="Delimiter", default=delimiter, multiline=False,
                    tooltip="Literal, case-sensitive text to stop at; can be one or several characters. Empty or missing leaves text unchanged.\nExample: " + _OPERATION_EXAMPLES[name],
                ),
                io.Boolean.Input(
                    "keep_delimiter", display_name="Keep Delimiter", default=False,
                    tooltip=(
                        "Keep the matched delimiter at the start of the result.\nExample: 'folder/file.txt' with '/' gives '/file.txt' when on, 'file.txt' when off."
                        if delimiter == "/" else
                        "Keep the matched delimiter at the end of the result.\nExample: 'photo.png' with '.' gives 'photo.' when on, 'photo' when off."
                    ),
                ),
            ]))
        options.append(io.DynamicCombo.Option("Find and Replace", [
            io.String.Input(
                "find", display_name="Find", default="", multiline=True,
                tooltip="One literal string per line. Empty lines are skipped; spaces are significant.\nExample: Find 'cat' and Replace With 'dog' turn 'a cat' into 'a dog'.",
            ),
            io.String.Input(
                "replace", display_name="Replace With", default="", multiline=True,
                tooltip="One replacement per Find line; line counts must match. Empty deletes the match.\nExample: 'dog' replaces 'cat' in 'a cat' to produce 'a dog'.",
            ),
        ]))
        options.append(io.DynamicCombo.Option("Case", [
            io.Combo.Input(
                "case_format", display_name="Format", options=list(_CASE_TOOLTIPS), default="lowercase",
                tooltip="Case format. Example: 'red fox' becomes 'redFox' with camelCase or 'RedFox' with PascalCase.",
                extra_dict={"case_tooltips": _CASE_TOOLTIPS},
            ),
        ]))
        order = [name for group in _OPERATION_GROUPS.values() for name in group]
        options.sort(key=lambda option: order.index(option.key))
        return io.Schema(
            node_id="MNeMiC_StringCleaning",
            display_name="🧹 String Cleaning",
            category="⚡ MNeMiC Nodes",
            description="Cleans text with an ordered sequence of whitespace, punctuation, text removal and replacement operations.",
            inputs=[
                io.String.Input(
                    "input_string",
                    multiline=True,
                    force_input=True,
                    tooltip="The text to clean, in operation order.\nExample: '  red   fox' with Trim Line Starts then Collapse Spaces becomes 'red fox'.",
                ),
                io.DynamicCombo.Input(
                    "operation", display_name="Operation", options=options,
                    tooltip=_OPERATION_TOOLTIPS["Collapse Spaces"],
                    extra_dict={"operation_tooltips": _OPERATION_TOOLTIPS, "case_tooltips": _CASE_TOOLTIPS},
                ),
                io.String.Input(
                    "extra_operations", default="[]", optional=True,
                    tooltip="Additional cleaning steps in order. Example: trim line starts, then remove empty lines.",
                ),
            ],
            outputs=[
                io.String.Output(
                    display_name="cleaned_string",
                    tooltip="Text after all operations, in order. Example: 'red fox' becomes 'redfox' with Remove All Spaces.",
                ),
            ],
        )

    @classmethod
    def execute(cls, input_string: str, operation: dict, extra_operations: str = "[]") -> io.NodeOutput:
        try:
            extra = json.loads(extra_operations)
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid additional cleaning operations.") from error
        if not isinstance(extra, list) or any(not isinstance(item, dict) for item in extra):
            raise ValueError("Additional cleaning operations must be a list of operations.")
        for index, step in enumerate([operation, *extra], start=1):
            try:
                input_string = cls.clean_once(input_string, step)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Operation {index}: {error}") from error
        return io.NodeOutput(input_string)

    @classmethod
    def clean_once(cls, input_string: str, operation: dict) -> str:
        name = operation["operation"]
        settings = {}
        if name == "Trim Whitespace":
            return input_string.strip()
        if name == "Trim Each Line":
            return "\n".join(line.strip() for line in input_string.split("\n"))
        if name == "Normalize Whitespace":
            return re.sub(r"\s+", " ", input_string).strip()
        if name == "Normalize Line Breaks":
            return input_string.replace("\r\n", "\n").replace("\r", "\n")
        if name == "Remove Duplicate Lines":
            return "\n".join(dict.fromkeys(input_string.split("\n")))
        if name in ("Case", "Lowercase", "Uppercase"):
            legacy = {"Lowercase": "lowercase", "Uppercase": "UPPERCASE"}
            return _change_case(input_string, legacy.get(name, operation.get("case_format", "lowercase")))
        if name == "Remove All Spaces":
            return input_string.replace(" ", "")
        if name in ("Remove From Start Until", "Remove From End Until"):
            delimiter = operation.get("delimiter", "/" if name == "Remove From Start Until" else ".")
            if not delimiter:
                return input_string
            from_start = name == "Remove From Start Until"
            index = input_string.find(delimiter) if from_start else input_string.rfind(delimiter)
            if index == -1:
                return input_string
            keep = operation.get("keep_delimiter", False)
            if from_start:
                return input_string[index if keep else index + len(delimiter):]
            return input_string[:index + len(delimiter) if keep else index]
        if name in _SIMPLE_OPERATIONS:
            settings[_SIMPLE_OPERATIONS[name][0]] = True
        elif name in _TEXT_OPERATIONS:
            lines = operation.get("text", "").split("\n")
            if name in ("Remove Before Marker", "Remove After Marker"):
                lines = [line.strip() for line in lines if line.strip()]
            else:
                lines = [line for line in lines if line != ""]
            settings[_TEXT_OPERATIONS[name][0]] = lines
        elif name == "Remove Bracketed Content":
            pairs = [line for line in operation.get("pairs", "").split("\n") if line != ""]
            if any(len(pair) != 2 for pair in pairs):
                raise ValueError("Each Character Pairs line must contain exactly two characters.")
            settings["strip_inside_tags"] = pairs
        elif name == "Remove Between Tags":
            starts = [line for line in operation.get("start_tags", "").split("\n") if line != ""]
            ends = [line for line in operation.get("end_tags", "").split("\n") if line != ""]
            if len(starts) != len(ends):
                raise ValueError("Opening Tags and Closing Tags must have the same number of nonempty lines.")
            settings["strip_between_start"] = starts
            settings["strip_between_end"] = ends
        elif name == "Find and Replace":
            finds = operation.get("find", "").split("\n")
            replacements = operation.get("replace", "").split("\n")
            if len(finds) != len(replacements):
                raise ValueError("Find and Replace With must have the same number of lines.")
            pairs = [(find, replacement) for find, replacement in zip(finds, replacements) if find]
            settings["find_list"] = [find for find, _ in pairs]
            settings["replace_list"] = [replacement for _, replacement in pairs]
        else:
            raise ValueError(f"Unknown cleaning operation: {name}")
        return process_text(input_string=input_string, **settings)
