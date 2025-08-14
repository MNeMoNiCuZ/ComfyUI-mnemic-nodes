# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects. Some nodes are forks or versions of  nodes from other packs, some are bespoke and useful, and some are experimental and are quite useless, so they have been marked with a `Caution` label in this document.

# Installation instructions
## Configuration (only needed for Groq nodes)

1. Make a copy of `.env.example` and remove the `.example` from the name.
2. The new file should now be named `.env` without a normal file name, just a .env extension.
3. The file should be in the root of the node pack, so the same directory that the .example was in.
4. Edit `.env` with a text editor and edit the API key value inside.

# Nodes

## Wildcard Processor
A versatile text processor that replaces wildcards with content from files or inline lists.
[Link to documentation](./README/wildcard_processor.md)
![screenshot](https://via.placeholder.com/150)

## Get File Path
Returns the file path in different formats to a file in your /input-folder.
[Link to documentation](./README/get_file_path.md)
![screenshot](https://via.placeholder.com/150)

## Save Text File With Path
Save text file, and return the saved file's path.
[Link to documentation](./README/save_text_file.md)
![screenshot](https://via.placeholder.com/150)

## Download Image from URL
Download an image from the web.
[Link to documentation](./README/download_image_from_url.md)
![screenshot](https://via.placeholder.com/150)

## Tiktoken Tokenizer Info
Returns token information about input text and lets you split it.
[Link to documentation](./README/tiktoken_tokenizer.md)
![screenshot](https://via.placeholder.com/150)

## String Cleaning
Cleans up text strings.
[Link to documentation](./README/string_cleaning.md)
![screenshot](https://via.placeholder.com/150)

## String Text Splitter
Splits a string by the first occurrence of a delimiter.
[Link to documentation](./README/string_text_splitter.md)
![screenshot](https://via.placeholder.com/150)

## String Text Extractor
Extracts the first occurrence of text between a pair of characters.
[Link to documentation](./README/string_text_extractor.md)
![screenshot](https://via.placeholder.com/150)

## Format Date Time
Converts date / time into literal outputs.
[Link to documentation](./README/format_date_time.md)
![screenshot](https://via.placeholder.com/150)

## Load Text-Image Pairs
Loads a folder of text and image pairs, like a dataset.
[Link to documentation](./README/load_text_image_pairs.md)
![screenshot](https://via.placeholder.com/150)

## Metadata Extractor
Extracts metadata from input images.
[Link to documentation](./README/metadata_extractor.md)
![screenshot](https://via.placeholder.com/150)

## LoRA Loader Prompt Tags
Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.
[Link to documentation](./README/lora_tag_loader.md)
![screenshot](https://via.placeholder.com/150)

## Resolution Image Size Selector
Creates resolutions and a latent from presets, user presets, or input images.
[Link to documentation](./README/resolution_selector.md)
![screenshot](https://via.placeholder.com/150)

## Groq LLM API
Query Groq large language model.
[Link to documentation](./README/groq_api_llm.md)
![screenshot](https://via.placeholder.com/150)

## Groq VLM API
Query Groq vision language model.
[Link to documentation](./README/groq_api_vlm.md)
![screenshot](https://via.placeholder.com/150)

## Groq ALM API Transcribe
Query Groq Audio Model to transcribe audio.
[Link to documentation](./README/groq_api_alm_transcribe.md)
![screenshot](https://via.placeholder.com/150)

## Groq ALM API Translate
Query Groq Audio Model to translate audio.
[Link to documentation](./README/groq_api_alm_translate.md)
![screenshot](https://via.placeholder.com/150)

## Groq Completion API
Query Groq to complete text.
[Link to documentation](./README/groq_api_completion.md)
![screenshot](https://via.placeholder.com/150)

## Generate Negative Prompt
Generate negative prompts automatically.
[Link to documentation](./README/generate_negative_prompt.md)
![screenshot](https://via.placeholder.com/150)