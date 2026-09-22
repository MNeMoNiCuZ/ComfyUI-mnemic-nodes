# ✂️ String Text Extractor

Pulls out the text sitting between a pair of delimiter characters.

## Inputs

- **input_string** — The text to search.
- **delimiters** — Two characters: the opening one and the closing one, e.g.
  `[]`, `**`, `<>`. The first character opens, the last one closes.

## Outputs

- **extracted_text** — What was inside the first pair found. Empty if there was
  no match.
- **remainder_text** — The input with that first match and its delimiters
  removed. If nothing matched, this is the input unchanged.
- **extracted_list** — Every match in the text, as a list.

## How it works

Matching is non-greedy and spans line breaks, so the shortest run between an
opening and a closing delimiter wins. Fewer than two delimiter characters is
treated as no delimiter at all: nothing is extracted and the input passes
through as `remainder_text`.

## Examples

```
input_string: Some text [with captured content] and [more] text.
delimiters:   []

extracted_text:  with captured content
remainder_text:  Some text  and [more] text.
extracted_list:  [with captured content, more]
```
