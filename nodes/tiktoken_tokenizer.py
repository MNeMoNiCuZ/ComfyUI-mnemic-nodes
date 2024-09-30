import tiktoken
import hashlib
import re

class TiktokenTokenizer:
    OUTPUT_NODE = True
    RETURN_TYPES = (
        "INT", "INT", "INT",       # token_count, character_count, word_count
        "LIST", "LIST",            # split_string, split_string_list
        "LIST", "LIST",            # split_token_ids, split_token_ids_list
        "STRING",                  # text_hash
        "LIST", "LIST",            # special_tokens_used, special_tokens_used_list
        "LIST", "LIST", "LIST"     # token_chunk_by_size, token_chunk_by_size_to_word, token_chunk_by_size_to_section
    )
    RETURN_NAMES = (
        "token_count", "character_count", "word_count",
        "split_string", "split_string_list",
        "split_token_ids", "split_token_ids_list",
        "text_hash", "special_tokens_used",
        "special_tokens_used_list",
        "token_chunk_by_size",
        "token_chunk_by_size_to_word",
        "token_chunk_by_size_to_section"
    )
    OUTPUT_IS_LIST = (
        False, False, False,
        False, True,
        False, True,
        False,
        False, True,
        True, True, True
    )
    OUTPUT_TOOLTIPS = (
        "Total number of tokens in the input text",
        "Total number of characters in the input text",
        "Total number of words in the input text",
        "Tokenized list of strings",
        "Tokenized list of strings (output as list)",
        "List of token IDs",
        "List of token IDs (output as list)",
        "Hash of the input text",
        "List of special tokens used",
        "Special tokens used (output as list)",
        "Chunks of input text based on token length limit",
        "Chunks adjusted to the nearest complete word (no tokens lost)",
        "Chunks adjusted to the nearest section (newline, period, or comma)"
    )
    FUNCTION = "tokenize_text"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Tokenizes input text and returns various tokenization details, including token count, special tokens used, and more."
    DOCUMENTATION = "This node uses tiktoken to tokenize input text."

    @classmethod
    def INPUT_TYPES(cls):
        valid_encodings = ["gpt-4", "gpt-4o", "cl100k_base", "o200k_base"]

        return {
            "required": {
                "input_string": ("STRING", {"multiline": True, "tooltip": "Enter the text to be tokenized."}),
                # Use the 'label' field to show custom display names while keeping actual encoding values
                "encoding_type": (
                    valid_encodings,
                    {
                        "default": "cl100k_base",
                        "tooltip": "Select the encoding model you want to use for tokenization.",
                        "label": {
                            "gpt-4": "gpt3.5 + gpt4",
                            "gpt-4o": "gpt-4o + gpt-4o mini",
                            "cl100k_base": "cl100k_base",
                            "o200k_base": "o200k_base"
                        }
                    }
                ),
            },
            "optional": {
                "token_chunk_size": ("INT", {
                    "label": "Token Chunk Size (optional)",
                    "optional": True,
                    "tooltip": "Optional token length limit for chunking the input text.",
                    "min": 1,
                    "default": 75
                }),
            }
        }

    def tokenize_text(self, input_string, encoding_type, token_chunk_size=None):
        try:
            # Use encoding_for_model for OpenAI models like gpt-4, gpt-3.5-turbo, and gpt-4o
            if encoding_type in ["gpt-4", "gpt-4o"]:
                tokenizer = tiktoken.encoding_for_model(encoding_type)
            # Use get_encoding for other encodings like cl100k_base and o200k_base
            elif encoding_type in ["cl100k_base", "o200k_base"]:
                tokenizer = tiktoken.get_encoding(encoding_type)
            else:
                raise ValueError(f"Unsupported encoding type: {encoding_type}")

            # Get the dictionary of special tokens (maps special token strings to their token IDs)
            special_tokens = tokenizer._special_tokens

            # Tokenize the input text
            token_ids = tokenizer.encode(input_string, allowed_special="all")

            # Get the corresponding tokens in string form
            tokens = [tokenizer.decode([token_id]) for token_id in token_ids]

            # Calculate counts
            token_count = len(token_ids)
            character_count = len(input_string)
            word_count = len(input_string.split())

            # Keep the list form for split_string and split_token_ids
            split_string = tokens
            split_token_ids = token_ids

            # Generate the list versions (output as actual lists)
            split_string_list = tokens
            split_token_ids_list = token_ids

            # Generate a hash of the input string
            text_hash = hashlib.sha256(input_string.encode('utf-8')).hexdigest()

            # Detect special tokens from tokenizer
            special_tokens_used = [token for token, token_id in special_tokens.items() if token_id in token_ids]

            # Additionally, detect special tokens inside <| and |>
            special_tokens_used_regex = re.findall(r"<\|[^|]+\|>", input_string)
            special_tokens_used.extend(special_tokens_used_regex)

            # Initialize outputs for chunking
            token_chunk_by_size = []
            token_chunk_by_size_to_word = []
            token_chunk_by_size_to_section = []

            if token_chunk_size:
                # Ensure token_chunk_size is an integer
                token_chunk_size = int(token_chunk_size)

                # Function to chunk tokens based on size
                def chunk_by_size(token_ids, tokenizer, token_chunk_size):
                    num_tokens = len(token_ids)
                    chunks = []
                    for i in range(0, num_tokens, token_chunk_size):
                        chunk_ids = token_ids[i:i + token_chunk_size]
                        chunk_text = tokenizer.decode(chunk_ids)
                        chunks.append(chunk_text)
                    return chunks

                # Function to chunk tokens to nearest word
                def chunk_by_size_to_word(token_ids, tokenizer, token_chunk_size):
                    chunks = []
                    total_tokens = len(token_ids)
                    i = 0

                    if total_tokens <= token_chunk_size:
                        # If the entire token list is smaller than or equal to the chunk size, return it as a single chunk
                        chunk_text = tokenizer.decode(token_ids)
                        chunks.append(chunk_text)
                        return chunks

                    while i < total_tokens:
                        max_chunk_size = token_chunk_size  # Keep chunk size as user input

                        # Select the next chunk of tokens
                        chunk_ids = token_ids[i:i + max_chunk_size]
                        chunk_text = tokenizer.decode(chunk_ids)

                        # Find the last space in the chunk_text
                        last_space = chunk_text.rfind(' ')

                        if last_space > 0:
                            adjusted_chunk_text = chunk_text[:last_space]
                            adjusted_chunk_ids = tokenizer.encode(adjusted_chunk_text)

                            # Ensure that adjusted_chunk_ids align with the original tokens
                            if adjusted_chunk_ids == token_ids[i:i + len(adjusted_chunk_ids)]:
                                i += len(adjusted_chunk_ids)
                                chunks.append(adjusted_chunk_text)
                            else:
                                # If alignment fails, use the unadjusted chunk
                                i += len(chunk_ids)
                                chunks.append(chunk_text)
                        else:
                            # No space found, use the chunk as is
                            i += len(chunk_ids)
                            chunks.append(chunk_text)

                    return chunks

                # Function to chunk tokens to nearest section (newline, period, or comma)
                def chunk_by_size_to_section(token_ids, tokenizer, token_chunk_size):
                    chunks = []
                    total_tokens = len(token_ids)
                    i = 0

                    if total_tokens <= token_chunk_size:
                        # If the entire token list is smaller than or equal to the chunk size, return it as a single chunk
                        chunk_text = tokenizer.decode(token_ids)
                        chunks.append(chunk_text)
                        return chunks

                    while i < total_tokens:
                        max_chunk_size = token_chunk_size  # Keep chunk size as user input

                        # Select the next chunk of tokens
                        chunk_ids = token_ids[i:i + max_chunk_size]
                        chunk_text = tokenizer.decode(chunk_ids)

                        # Find the last section boundary
                        last_newline = chunk_text.rfind('\n')
                        last_period = chunk_text.rfind('.')
                        last_comma = chunk_text.rfind(',')
                        last_section = max(last_newline, last_period, last_comma)

                        if last_section > 0:
                            # Adjust the chunk to the last section boundary
                            adjusted_chunk_text = chunk_text[:last_section + 1]
                            adjusted_chunk_ids = tokenizer.encode(adjusted_chunk_text)

                            if len(adjusted_chunk_ids) == 0:
                                # Adjustment resulted in zero tokens, use the untrimmed chunk
                                adjusted_chunk_text = chunk_text
                                adjusted_chunk_ids = chunk_ids
                            i += len(adjusted_chunk_ids)
                        else:
                            # No section boundary found, use the chunk as is
                            adjusted_chunk_text = chunk_text
                            adjusted_chunk_ids = chunk_ids
                            i += len(adjusted_chunk_ids)

                        chunks.append(adjusted_chunk_text)

                    return chunks

                # Compute token_chunk_by_size
                token_chunk_by_size = chunk_by_size(token_ids, tokenizer, token_chunk_size)

                # Compute token_chunk_by_size_to_word
                token_chunk_by_size_to_word = chunk_by_size_to_word(token_ids, tokenizer, token_chunk_size)

                # Compute token_chunk_by_size_to_section
                token_chunk_by_size_to_section = chunk_by_size_to_section(token_ids, tokenizer, token_chunk_size)

            else:
                # If token_chunk_size is not provided, set outputs to empty lists
                token_chunk_by_size = []
                token_chunk_by_size_to_word = []
                token_chunk_by_size_to_section = []

            # Return all outputs
            return (
                token_count,                   # Total number of tokens
                character_count,               # Total number of characters
                word_count,                    # Total number of words
                split_string,                  # Tokenized list of strings (original)
                split_string_list,             # Tokenized list of strings (output as list)
                split_token_ids,               # List of token IDs (original)
                split_token_ids_list,          # List of token IDs (output as list)
                text_hash,                     # Text hash
                special_tokens_used,           # Special tokens used (original)
                special_tokens_used,           # Special tokens used (output as list)
                token_chunk_by_size,           # Chunks based on token length limit
                token_chunk_by_size_to_word,   # Chunks adjusted to nearest word
                token_chunk_by_size_to_section # Chunks adjusted to nearest section
            )

        except Exception as e:
            print(f"Error tokenizing text: {str(e)}")
            return None, None, None, None, None, None, None, None, None, None, None, None, None

# Export the node to ComfyUI
NODE_CLASS_MAPPINGS = {
    "TiktokenTokenizer": TiktokenTokenizer
}