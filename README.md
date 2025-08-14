# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects. Some nodes are forks or versions of  nodes from other packs, some are bespoke, and some are experimental and are quite useless, so they have been marked with a `Caution` label in this document.

# Installation instructions
## Configuration (only needed for Groq nodes)

1. Make a copy of `.env.example` and remove the `.example` from the name.
2. The new file should now be named `.env` without a normal file name, just a .env extension.
3. The file should be in the root of the node pack, so the same directory that the .example was in.
4. Edit `.env` with a text editor and edit the API key value inside.

# Nodes

## 📝 Wildcard Processor
A versatile text processor that replaces wildcards with content from wildcard files or inline lists.
[Link to documentation](./README/wildcard_processor.md)


## 📁 Get File Path
Returns the file path in different formats to a file in your /input-folder.
[Link to documentation](./README/get_file_path.md)


## 💾 Save Text File With Path
Save text file, and return the saved file's path.
[Link to documentation](./README/save_text_file.md)


## 🖼️ Download Image from URL
Download an image from the web.
[Link to documentation](./README/download_image_from_url.md)


## 🔠 Tiktoken Tokenizer Info
Returns token information about input text and lets you split it.
[Link to documentation](./README/tiktoken_tokenizer.md)


## 🧹 String Cleaning
Cleans up text strings, strip leading/trailing spaces or collapse them, remove newlines and much more.
[Link to documentation](./README/string_cleaning.md)


## ✂️ String Text Splitter
Splits a string by the first occurrence of a delimiter.
[Link to documentation](./README/string_text_splitter.md)


## ✂️ String Text Extractor
Extracts the first occurrence of text between a pair of characters.
[Link to documentation](./README/string_text_extractor.md)


## 📅 Format Date Time
Converts date / time into literal outputs. Useful for saving paths and files.
[Link to documentation](./README/format_date_time.md)


## 🖼️+📝 Load Text-Image Pairs
Loads a folder of text and image pairs like a dataset, and gives you the image and string as separate outputs.
[Link to documentation](./README/load_text_image_pairs.md)


## 🖼️📊 Metadata Extractor
Extracts metadata from input images.
[Link to documentation](./README/metadata_extractor.md)


## 🏷️ LoRA Loader Prompt Tags
Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.
[Link to documentation](./README/lora_tag_loader.md)


## 📐 Resolution Image Size Selector
Creates resolutions and a latent from presets, user presets, or input images.
[Link to documentation](./README/resolution_selector.md)


## ✨💬 Groq LLM API
Query Groq large language model.
[Link to documentation](./README/groq_api_llm.md)


## ✨📷 Groq VLM API
Query Groq vision language model.
[Link to documentation](./README/groq_api_vlm.md)


## ✨📝 Groq ALM API - Transcribe
Query Groq Audio Model to transcribe audio.
[Link to documentation](./README/groq_api_alm_transcribe.md)


## ⛔ Generate Negative Prompt
Generate negative prompts automatically.
[Link to documentation](./README/generate_negative_prompt.md)
![screenshot](https://via.placeholder.com/150)
