# 🔠 Tiktoken Tokenizer Info

Counts tokens in text using OpenAI's `tiktoken` encoders, and breaks the text
into tokens and size-capped chunks. The token count is shown on the node.

Useful for checking a prompt against a model's context limit, or splitting a
long text into pieces that fit.

## Inputs

- **input_string** — The text to measure.
- **encoding_type** — Which encoder to use:
  - `cl100k_base` — GPT-3.5 / GPT-4 family
  - `o200k_base` — GPT-4o family
  - `gpt-4`, `gpt-4o` — resolved through the model name instead of the encoder
    name; same result
- **token_chunk_size** *(optional)* — Token budget per chunk for the three
  chunk outputs. Default 75.

## Outputs

- **token_count** / **character_count** / **word_count** — Totals.
- **split_string** / **split_string_list** — The text as individual token
  strings.
- **split_token_ids** / **split_token_ids_list** — The same as numeric IDs.
- **text_hash** — Hash of the input, for change detection.
- **special_tokens_used** / **special_tokens_used_list** — Any special tokens
  found.
- **token_chunk_by_size** — Chunks cut at exactly the token budget.
- **token_chunk_by_size_to_word** — Chunks moved back to the nearest word
  boundary, so no token is lost.
- **token_chunk_by_size_to_section** — Chunks moved back to the nearest line
  break, period or comma.

## Notes

The paired `..._list` outputs carry the same data as their non-list twin but
are flagged as lists, so downstream nodes iterate over them instead of
receiving one value. Token counts are OpenAI's, not CLIP's or T5's — treat them
as an indication for image models, not an exact figure.
