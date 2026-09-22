# 🧹 String Cleaning

Runs a chain of clean-up passes over text: trimming whitespace, stripping
punctuation and tags, removing chunks between markers, and find/replace.
Everything is off by default, so the node passes text through untouched until
you enable something.

## Inputs

Whitespace:

- **collapse_sequential_spaces** — Several spaces in a row become one.
- **strip_leading_spaces** / **strip_trailing_spaces** — Trim each line.
- **strip_empty_lines** — Drop lines that are empty or whitespace only.

Symbols, newlines and text removal:

- **strip_leading_symbols** / **strip_trailing_symbols** — Trim `, . ! ? : ;`
  from the ends of each line.
- **strip_newlines** — Remove every line break.
- **replace_newlines_with_period_space** — Turn runs of line breaks into `". "`.
- **strip_inside_tags** — One character *pair* per line, e.g. `()`. Content
  between them, and the brackets, are removed.
- **strip_between_start** / **strip_between_end** — Opening and closing markers,
  one per line. Both fields must have the same number of lines. Everything
  between a pair is removed.
- **strip_leading_custom** / **strip_trailing_custom** — Text to strip from the
  start / end of each line, one entry per line.
- **strip_all_custom** — Text to remove wherever it appears.
- **remove_text_before** / **remove_text_after** — Markers; everything before
  (or after) the marker, including the marker itself, is removed.
- **multiline_find** / **multiline_replace** — Line-for-line find/replace pairs.
  The two fields must have the same number of lines.

## Outputs

- **cleaned_string** — The text after every enabled pass.

## Notes

Mismatched line counts in the paired fields (`strip_between_*`,
`multiline_find`/`multiline_replace`) stop the run with an error rather than
silently guessing. A `strip_inside_tags` line that is not exactly two
characters does the same.

## Examples

```
strip_between_start: <think>
strip_between_end:   </think>

Input:  <think>Hmm, the user wants...</think> The answer is 24
Output: The answer is 24
```
