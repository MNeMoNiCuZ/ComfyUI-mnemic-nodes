# ✂️ String Text Splitter

Splits text on a delimiter and/or on line breaks, and gives you both the first
piece and everything after it.

## Inputs

- **input_string** — The text to split.
- **delimiter** — The character to split on. Leave empty to split only on line
  breaks (requires the toggle below).
- **split_at_linebreaks** — Also treat line breaks as split points. Works with
  or without a delimiter.
- **target_indices** — Comma-separated 0-based positions to pull out, e.g.
  `0,2`. Leave empty to skip this output.

## Outputs

- **first_chunk** — Everything before the first split point.
- **remainder** — Everything after it, still unsplit.
- **chunk_list** — Every piece, as a list. Empty pieces are dropped, so
  repeated delimiters do not create blanks.
- **targeted_chunks** — Just the pieces named in `target_indices`, one per
  line.

## How it works

With no delimiter and line-break splitting off, nothing is split: the text
comes out of `first_chunk` unchanged. Out-of-range target indices are ignored,
and a malformed `target_indices` prints a console warning rather than failing
the run.

## Examples

```
input_string: part1|part2|part3
delimiter:    |

first_chunk:      part1
remainder:        part2|part3
chunk_list:       [part1, part2, part3]
target_indices 0,2 -> targeted_chunks: "part1\npart3"
```
