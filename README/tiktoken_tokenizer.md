# 🔠 Tiktoken Tokenizer Info
This node takes text as input, and returns a bunch of data from the [tiktoken tokenizer](https://github.com/openai/tiktoken).

It returns the following values:
- `token_count`: Total number of tokens
- `character_count`: Total number of characters
- `word_count`: Total number of words
- `split_string`: Tokenized list of strings
- `split_string_list`: Tokenized list of strings (output as list)
- `split_token_ids`: List of token IDs
- `split_token_ids_list`: List of token IDs (output as list)
- `text_hash`: Text hash
- `special_tokens_used`: Special tokens used
- `special_tokens_used_list`: Special tokens used (output as list) 
- `token_chunk_by_size`: Returns the input text, split into different strings in a list by the `token_chunk_size` value.
- `token_chunk_by_size_to_word`: Same as above but respects "words" by stripping backwards to the nearest space and splitting the chunk there.
- `token_chunk_by_size_to_section`: Same as above, but strips backwards to the nearest newline, period or comma.

### Tokenization & Word Count example
![image](https://github.com/user-attachments/assets/2d26ae1e-3874-4919-be30-f88c59219708)

---

### Chunking Example
![image](https://github.com/user-attachments/assets/74e6ce19-54f8-48eb-9602-ec1fe60200df)
