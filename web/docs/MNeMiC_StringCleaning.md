# 🧹 String Cleaning

Cleans text with operations applied from top to bottom. Each step shows only its own fields.

## Inputs

- **input_string**: Text to clean.
- **Operation**: First step; defaults to **Collapse Spaces**.
- **Add Operation**: Append another step and choose its operation.
- **Remove Last Operation**: Remove the last added step.

Every operation and field has an example in its tooltip.

| Operation | Settings | Input | Output |
| --- | --- | --- | --- |
| **Whitespace** | | | |
| Collapse Spaces | None | `"red   fox"` | `"red fox"` |
| Trim Whitespace | None | `"  red fox  "` | `"red fox"` |
| Trim Each Line | None | `"  red  \n  fox  "` | `"red\nfox"` |
| Trim Line Starts | None | `"  red fox"` | `"red fox"` |
| Trim Line Ends | None | `"red fox  "` | `"red fox"` |
| Normalize Whitespace | None | `"  red\t fox\n "` | `"red fox"` |
| Remove All Spaces | None | `"red fox"` | `"redfox"` |
| **Lines** | | | |
| Normalize Line Breaks | None | `"red\r\nfox\rcat"` | `"red\nfox\ncat"` |
| Remove Empty Lines | None | `"red\n\nfox"` | `"red\nfox"` |
| Remove Duplicate Lines | None | `"red\nfox\nred"` | `"red\nfox"` |
| Remove Line Breaks | None | `"red\nfox"` | `"redfox"` |
| Line Breaks to Sentences | None | `"Hello\nWorld"` | `"Hello. World"` |
| **Punctuation** | | | |
| Remove Leading Punctuation | None | `"...Hello"` | `"Hello"` |
| Remove Trailing Punctuation | None | `"Hello!!!"` | `"Hello"` |
| **Text removal** | | | |
| Remove Line Prefix | Text: `"Chapter "` | `"Chapter 1: Hello"` | `"1: Hello"` |
| Remove Line Suffix | Text: `" END"` | `"Hello END"` | `"Hello"` |
| Remove Text | Text: `cat` | `"cat and cat"` | `" and "` |
| Remove Before Marker | Markers: `<START>` | `"Header<START>Hello"` | `"Hello"` |
| Remove After Marker | Markers: `<END>` | `"Hello<END>Footer"` | `"Hello"` |
| Remove From Start Until | Delimiter: `/` | `"folder/sub/file.txt"` | `"sub/file.txt"` |
| Remove From End Until | Delimiter: `.` | `"photo.v2.png"` | `"photo.v2"` |
| Remove Bracketed Content | Character Pairs: `()` | `"Hello (draft)world"` | `"Hello world"` |
| Remove Between Tags | Opening: `<think>`, Closing: `</think>` | `"<think>draft</think>Hello"` | `"Hello"` |
| **Replacement and case** | | | |
| Find and Replace | Find: `cat`, Replace With: `dog` | `"a cat"` | `"a dog"` |
| Case | Format: `camelCase` | `"red fox"` | `"redFox"` |

Quotes show spaces; do not enter the quotes. `\t` is a tab, `\r` is CR, and `\n` is LF (a line break).

### Case formats

| Format | Input | Output |
| --- | --- | --- |
| lowercase | `Red FOX` | `red fox` |
| UPPERCASE | `Red fox` | `RED FOX` |
| Title Case | `the red fox` | `The Red Fox` |
| Sentence case | `HELLO. GOODBYE!` | `Hello. Goodbye!` |
| camelCase | `red fox` | `redFox` |
| PascalCase | `red fox` | `RedFox` |
| snake_case | `RedFox` | `red_fox` |
| CONSTANT_CASE | `red fox` | `RED_FOX` |
| kebab-case | `red fox` | `red-fox` |
| Train-Case | `red fox` | `Red-Fox` |
| dot.case | `red fox` | `red.fox` |
| tOGGLE cASE | `Red FOX` | `rED fox` |

Joined formats split words at whitespace, punctuation and case boundaries:
`HTTPServer` becomes `http_server` with snake_case. Other case formats keep
punctuation and spacing. Sentence case treats `.`, `!`, `?` and line breaks as sentence boundaries.

## Outputs

- **cleaned_string**: Text after all operations.

## Examples

1. **Remove Line Prefix**, Text `"Chapter "`: `"Chapter  red   fox"` becomes `" red   fox"`.
2. **Trim Line Starts**: becomes `"red   fox"`.
3. **Collapse Spaces**: becomes `"red fox"`.

## Notes

- Text fields take one entry per line, applied in order. Matching is case-sensitive.
- Prefix/suffix removal repeats at the selected end of each line. Spaces are significant except around marker entries.
- Remove All Spaces removes ordinary spaces, keeping tabs and line breaks.
- Normalize Whitespace also replaces tabs and line breaks with spaces. Remove Duplicate Lines keeps the first exact match; trim lines first to ignore surrounding whitespace.
- Remove From Start/End Until uses the first/last delimiter in the whole string. Empty or missing delimiters leave text unchanged. **Keep Delimiter** retains it: `photo.v2.png` becomes `photo.v2.` when trimming from the end with `.`.
- Character Pairs needs two characters per nonempty line. Opening/Closing Tags need equal nonempty line counts.
- Brackets and tags match across lines to the nearest closing delimiter; nesting is not supported.
- Find and Replace needs equal line counts. Empty Find lines are skipped; empty replacements delete matches.
