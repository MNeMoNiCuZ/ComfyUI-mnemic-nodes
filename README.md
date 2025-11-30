# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects. Some nodes are forks or versions of  nodes from other packs, some are bespoke, and some are experimental and are quite useless, so they have been marked with a `Caution` label in this document.

# Installation instructions
## Configuration (only needed for Groq nodes)

1. Make a copy of `.env.example` and remove the `.example` from the name.
2. The new file should now be named `.env` without a normal file name, just a .env extension.
3. The file should be in the root of the node pack, so the same directory that the .example was in.
4. Edit `.env` with a text editor and edit the API key value inside.

# Nodes

## 📝 [Wildcard Processor](./README/wildcard_processor.md)
A versatile text processor that replaces wildcards with content from wildcard files or inline lists.
<img width="1649" height="417" alt="image" src="https://github.com/user-attachments/assets/ed495b54-3e53-44d7-8655-d7b5f105cc1f" />

## 🏷️ [LoRA Loader Prompt Tags](./README/lora_tag_loader.md)
Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.
<img width="1645" height="548" alt="image" src="https://github.com/user-attachments/assets/1f7a35b8-6ca8-4099-90d8-0e7b9fa4cd87" />


## ⚙️ [Prompt Property Extractor](./README/prompt_property_extractor.md)
Extract generation settings from your input prompt. Use it to randomize your generation settings, checkpoint, step count, seed, or include negative prompt with the normal prompt, load wildcards, or LoRAs, all at the same time. 
<img width="1667" height="515" alt="image" src="https://github.com/user-attachments/assets/e85cdcb5-d953-4be4-a73c-32e14b2c1550" />


## 📁 [Get File Path](./README/get_file_path.md)
Returns the file path in different formats to a file in your /input-folder.
<img width="1645" height="525" alt="image" src="https://github.com/user-attachments/assets/7fc63f03-bb52-484e-8288-1a51a04cb545" />


## ✂️ [String Text Splitter](./README/string_text_splitter.md)
Splits a string by the first occurrence of a delimiter.
<img width="1613" height="652" alt="image" src="https://github.com/user-attachments/assets/e634a287-2334-49f2-81c3-a2fdb44d6db0" />


## ✂️ [String Text Extractor](./README/string_text_extractor.md)
Extracts the first occurrence of text between a pair of characters.
<img width="1629" height="551" alt="image" src="https://github.com/user-attachments/assets/01ea196e-b0b7-4d23-87d4-203303643b65" />


## 💾 [Save Text File With Path](./README/save_text_file.md)
Save text file, and return the saved file's path.
<img width="1650" height="415" alt="image" src="https://github.com/user-attachments/assets/f283be20-dc90-4139-958c-5db5e8a8250d" />


## 🖼️ [Download Image from URL](./README/download_image_from_url.md)
Download an image from the web.
<img width="1649" height="438" alt="image" src="https://github.com/user-attachments/assets/314e8bef-4eab-4ffb-b21e-6fe13413820f" />


## 🔠 [Tiktoken Tokenizer Info](./README/tiktoken_tokenizer.md)
Returns token information about input text and lets you split it.
<img width="1641" height="320" alt="image" src="https://github.com/user-attachments/assets/b4680677-1d78-4d85-b7e0-d37a91a83904" />


## 🧹 [String Cleaning](./README/string_cleaning.md)
Cleans up text strings, strip leading/trailing spaces or collapse them, remove newlines and much more.
<img width="1659" height="646" alt="image" src="https://github.com/user-attachments/assets/ffb05b11-a78c-468a-81ed-2aa38cce4549" />


## 📅 [Format Date Time](./README/format_date_time.md)
Converts date / time into literal outputs. Useful for saving paths and files.
<img width="1660" height="376" alt="image" src="https://github.com/user-attachments/assets/c44cdf70-acee-4062-aeb7-4d64b58e3a52" />


## 🖼️+📝 [Load Text-Image Pairs](./README/load_text_image_pairs.md)
Loads a folder of text and image pairs like a dataset, and gives you the image and string as separate outputs.
<img width="1615" height="553" alt="image" src="https://github.com/user-attachments/assets/7a013b7f-b600-4ffb-88ae-e81c33779cd2" />


## 🖼️📊 [Metadata Extractor (Single)](./README/metadata_extractor_single.md)
Extracts metadata from a single image selected from an input source.
<img width="2259" height="667" alt="image" src="https://github.com/user-attachments/assets/551f26cb-f913-468a-a479-5d4890887a38" />


## 🖼️📊 [Metadata Extractor (List)](./README/metadata_extractor_list.md)
Extracts metadata from a list of images or a folder of images.
<img width="2420" height="592" alt="image" src="https://github.com/user-attachments/assets/dfe0953f-7802-4701-a2d0-2e16e0e4f475" />


## 🎲 [Load Random Checkpoint](./README/load_random_checkpoint.md)
Load checkpoints with flexible fuzzy matching and repeat control for more varied outputs.
<img width="2381" height="915" alt="image" src="https://github.com/user-attachments/assets/789835ef-45a3-4857-a63c-f6d6dd9b9088" />


## 📐 [Resolution Image Size Selector](./README/resolution_selector.md)
Creates resolutions and a latent from presets, user presets, or input images.
<img width="1464" height="428" alt="image" src="https://github.com/user-attachments/assets/3bd379ee-0c02-4382-8e2c-0b75a1a607ef" />


## 🖼️ [Load Images From Path](./README/load_images_from_path.md)
Load single images or iterate through image directories with mask support.
<img width="2231" height="768" alt="image" src="https://github.com/user-attachments/assets/dddaaea0-aa43-40b6-ad87-9145196e5a74" />


## 🖼️ [Load Image Advanced](./README/load_image_advanced.md)
Loads an image, extracts metadata, provides the alpha channel as a mask, and outputs the image's dimensions.
<img width="1933" height="875" alt="image" src="https://github.com/user-attachments/assets/e70c3c81-637d-4dfc-a20e-3d48409abf4c" />


## 🎨 [Colorful Starting Image](./README/colorful_starting_image.md)
Creates a colorful random shape-based image. Use it as a starting latent for fun and varying shapes. Great for abstract wallpaper creation.
<img width="1766" height="1083" alt="image" src="https://github.com/user-attachments/assets/b135ac20-c28c-40bc-bc55-5d31c0c7fd30" />


## 🎵📊 [Audio Visualizer](./README/audio_visualizer.md)
Creates a visualizer from an input audio. Custom visualizer scripts can be created, and outputs can be saved as images or video.
<img width="2205" height="638" alt="image" src="https://github.com/user-attachments/assets/35e70f68-09f2-4dfe-9676-18fe54a9af89" />


## ✨💬 [Groq LLM API](./README/groq_api_llm.md)
Query Groq large language model.
<img width="1590" height="489" alt="image" src="https://github.com/user-attachments/assets/6743639e-4cfd-4cc5-9283-a8ab165c364e" />


## ✨📷 [Groq VLM API](./README/groq_api_vlm.md)
Query Groq vision language model.
<img width="1602" height="270" alt="image" src="https://github.com/user-attachments/assets/1b3bb243-daa0-4058-a1a3-3dd7faee6376" />


## ✨📝 [Groq ALM API - Transcribe](./README/groq_api_alm_transcribe.md)
Query Groq Audio Model to transcribe audio.
<img width="1623" height="214" alt="image" src="https://github.com/user-attachments/assets/b5f2e3fe-7b72-42e4-8201-27cbcefac258" />


## ⛔ [Generate Negative Prompt](./README/generate_negative_prompt.md)
Generate negative prompts automatically.
<img width="1577" height="359" alt="image" src="https://github.com/user-attachments/assets/a126dd5d-2d92-4069-8998-0f19ed5bcd2b" />
