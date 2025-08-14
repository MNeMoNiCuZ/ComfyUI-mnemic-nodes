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
<img width="1649" height="417" alt="image" src="https://github.com/user-attachments/assets/ed495b54-3e53-44d7-8655-d7b5f105cc1f" />



## 📁 Get File Path
Returns the file path in different formats to a file in your /input-folder.
[Link to documentation](./README/get_file_path.md)
<img width="1645" height="525" alt="image" src="https://github.com/user-attachments/assets/7fc63f03-bb52-484e-8288-1a51a04cb545" />


## 💾 Save Text File With Path
Save text file, and return the saved file's path.
[Link to documentation](./README/save_text_file.md)
<img width="1650" height="415" alt="image" src="https://github.com/user-attachments/assets/f283be20-dc90-4139-958c-5db5e8a8250d" />


## 🖼️ Download Image from URL
Download an image from the web.
[Link to documentation](./README/download_image_from_url.md)
<img width="1649" height="438" alt="image" src="https://github.com/user-attachments/assets/314e8bef-4eab-4ffb-b21e-6fe13413820f" />


## 🔠 Tiktoken Tokenizer Info
Returns token information about input text and lets you split it.
[Link to documentation](./README/tiktoken_tokenizer.md)
<img width="1641" height="320" alt="image" src="https://github.com/user-attachments/assets/b4680677-1d78-4d85-b7e0-d37a91a83904" />


## 🧹 String Cleaning
Cleans up text strings, strip leading/trailing spaces or collapse them, remove newlines and much more.
[Link to documentation](./README/string_cleaning.md)
<img width="1659" height="646" alt="image" src="https://github.com/user-attachments/assets/ffb05b11-a78c-468a-81ed-2aa38cce4549" />


## ✂️ String Text Splitter
Splits a string by the first occurrence of a delimiter.
[Link to documentation](./README/string_text_splitter.md)
<img width="1613" height="652" alt="image" src="https://github.com/user-attachments/assets/e634a287-2334-49f2-81c3-a2fdb44d6db0" />


## ✂️ String Text Extractor
Extracts the first occurrence of text between a pair of characters.
[Link to documentation](./README/string_text_extractor.md)
<img width="1629" height="551" alt="image" src="https://github.com/user-attachments/assets/01ea196e-b0b7-4d23-87d4-203303643b65" />



## 📅 Format Date Time
Converts date / time into literal outputs. Useful for saving paths and files.
[Link to documentation](./README/format_date_time.md)
<img width="1660" height="376" alt="image" src="https://github.com/user-attachments/assets/c44cdf70-acee-4062-aeb7-4d64b58e3a52" />



## 🖼️+📝 Load Text-Image Pairs
Loads a folder of text and image pairs like a dataset, and gives you the image and string as separate outputs.
[Link to documentation](./README/load_text_image_pairs.md)
<img width="1615" height="553" alt="image" src="https://github.com/user-attachments/assets/7a013b7f-b600-4ffb-88ae-e81c33779cd2" />


## 🖼️📊 Metadata Extractor
Extracts metadata from input images.
[Link to documentation](./README/metadata_extractor.md)
<img width="1600" height="753" alt="image" src="https://github.com/user-attachments/assets/3a58899f-c479-4fcd-bfc6-f573e30a028a" />


## 🏷️ LoRA Loader Prompt Tags
Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.
[Link to documentation](./README/lora_tag_loader.md)
<img width="1645" height="548" alt="image" src="https://github.com/user-attachments/assets/1f7a35b8-6ca8-4099-90d8-0e7b9fa4cd87" />


## 📐 Resolution Image Size Selector
Creates resolutions and a latent from presets, user presets, or input images.
[Link to documentation](./README/resolution_selector.md)
<img width="1464" height="428" alt="image" src="https://github.com/user-attachments/assets/3bd379ee-0c02-4382-8e2c-0b75a1a607ef" />


## ✨💬 Groq LLM API
Query Groq large language model.
[Link to documentation](./README/groq_api_llm.md)
<img width="1590" height="489" alt="image" src="https://github.com/user-attachments/assets/6743639e-4cfd-4cc5-9283-a8ab165c364e" />


## ✨📷 Groq VLM API
Query Groq vision language model.
[Link to documentation](./README/groq_api_vlm.md)
<img width="1602" height="270" alt="image" src="https://github.com/user-attachments/assets/1b3bb243-daa0-4058-a1a3-3dd7faee6376" />


## ✨📝 Groq ALM API - Transcribe
Query Groq Audio Model to transcribe audio.
[Link to documentation](./README/groq_api_alm_transcribe.md)
<img width="1623" height="214" alt="image" src="https://github.com/user-attachments/assets/b5f2e3fe-7b72-42e4-8201-27cbcefac258" />


## ⛔ Generate Negative Prompt
Generate negative prompts automatically.
[Link to documentation](./README/generate_negative_prompt.md)
<img width="1577" height="359" alt="image" src="https://github.com/user-attachments/assets/a126dd5d-2d92-4069-8998-0f19ed5bcd2b" />

