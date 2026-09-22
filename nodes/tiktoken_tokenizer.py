import tiktoken
import hashlib
import re

from comfy_api.latest import io, ui

LIST = io.Custom("LIST")


class TiktokenTokenizer(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        valid_encodings = ["gpt-4", "gpt-4o", "cl100k_base", "o200k_base"]

        return io.Schema(
            node_id="MNeMiC_TiktokenTokenizer",
            display_name="🔠 Tiktoken Tokenizer Info",
            category="⚡ MNeMiC Nodes",
            description="Tokenizes input text and returns various tokenization details, including token count, special tokens used, and more.",
            inputs=[
                io.String.Input(
                    "input_string",
                    multiline=True,
                    tooltip="Enter the text to be tokenized.",
                ),
                io.Combo.Input(
                    "encoding_type",
                    options=valid_encodings,
                    default="cl100k_base",
                    tooltip="Select the encoding model you want to use for tokenization.",
                ),
                io.Int.Input(
                    "token_chunk_size",
                    optional=True,
                    min=1,
                    default=75,
                    tooltip="Optional token length limit for chunking the input text.",
                ),
            ],
            outputs=[
                io.Int.Output(display_name="token_count", tooltip="Total number of tokens in the input text"),
                io.Int.Output(display_name="character_count", tooltip="Total number of characters in the input text"),
                io.Int.Output(display_name="word_count", tooltip="Total number of words in the input text"),
                LIST.Output(display_name="split_string", tooltip="Tokenized list of strings"),
                LIST.Output(display_name="split_string_list", tooltip="Tokenized list of strings (output as list)", is_output_list=True),
                LIST.Output(display_name="split_token_ids", tooltip="List of token IDs"),
                LIST.Output(display_name="split_token_ids_list", tooltip="List of token IDs (output as list)", is_output_list=True),
                io.String.Output(display_name="text_hash", tooltip="Hash of the input text"),
                LIST.Output(display_name="special_tokens_used", tooltip="List of special tokens used"),
                LIST.Output(display_name="special_tokens_used_list", tooltip="Special tokens used (output as list)", is_output_list=True),
                LIST.Output(display_name="token_chunk_by_size", tooltip="Chunks of input text based on token length limit", is_output_list=True),
                LIST.Output(display_name="token_chunk_by_size_to_word", tooltip="Chunks adjusted to the nearest complete word (no tokens lost)", is_output_list=True),
                LIST.Output(display_name="token_chunk_by_size_to_section", tooltip="Chunks adjusted to the nearest section (newline, period, or comma)", is_output_list=True),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, input_string, encoding_type, token_chunk_size=None) -> io.NodeOutput:
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
            return io.NodeOutput(
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
                token_chunk_by_size_to_section, # Chunks adjusted to nearest section
                ui=ui.PreviewText(
                    f"{token_count} tokens · {word_count} words · {character_count} characters"
                ),
            )

        except Exception as e:
            print(f"Error tokenizing text: {str(e)}")
            return io.NodeOutput(*((None,) * 13))
