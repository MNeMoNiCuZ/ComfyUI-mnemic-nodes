# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects. Some nodes are forks or versions of  nodes from other packs, some are bespoke and useful, and some are experimental and are quite useless, so they have been marked with a `Caution` label in this document.

[📁 Get File Path](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-get-file-path) - Returns the file path in different formats to a file in your /input-folder.

[💾 Save Text File With Path Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-save-text-file-with-path-node) - Save text file, and return the saved file's path.

[🖼️ Download Image from URL Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#%EF%B8%8F-download-image-from-url-node) - Download an image from the web.

[🔠 Tiktoken Tokenizer Info](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-tiktoken-tokenizer-info) - Returns token information about input text and lets you split it.

[🧹 String Cleaning](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-string-cleaning) - Cleans up text strings.

[✨💬 Groq LLM API Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-llm-api-node) - Query Groq large language model.

[✨📷 Groq VLM API Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-vlm-api-node) - Query Groq vision language model.

[✨📝 Groq ALM API Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-alm-api-node) - Query Groq Audio Model.

[⛔ Generate Negative Prompt Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-generate-negative-prompt-node) - Generate negative prompts automatically.


# Installation instructions

You may need to manually install the requirements. They should be listed in `requirements.txt`
You may need to install the following libraries using `pip install XXX`:
```
configparser
groq
transformers
torch
```

## Configuration (only needed for Groq nodes)

1. Copy `.env.example` to `.env`
2. Edit `.env` and add any relevant API-keys or other configurations that are available

## 📁 Get File Path

This node returns the file path of a given file in the \input-folder.

![image](https://github.com/user-attachments/assets/1fd9bfdc-f92d-4f33-a992-a5af66029a9f)

It is meant to have a browse-button so you can browse to any file, but it doesn't yet.

**If you know how to add this, please let me know or do a pull request.**


## 💾 Save Text File With Path Node

This node is adapted and enhanced from the Save Text File node found in the [YMC GitHub ymc-node-suite-comfyui pack](https://github.com/YMC-GitHub/ymc-node-suite-comfyui).

The node can now give you a full file path output if you need it, as well as output the file-name as a separate output, in case you need it for something else.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/bf43ec1e-3717-46b9-8241-7165a537a416)

> [!IMPORTANT]
> #### 2024-06-05 - Version 1.1.1
> The node was severely updated so existing workflows are going to break. I won't do another overhaul like this.
>
> The new node is more consistent in functionality and more intentional with the inputs and outputs.
>
> It now handles more edge cases and supports both a prefix, suffix, a dynamic counting with customizable separator before/after the counter in the right circumstances.
>
> Sorry for any troubles caused.


## 🖼️ Download Image from URL Node

This node downloads an image from an URL and lets you use it.

It also outputs the Width/Height of the image.

* By default, it will save the image to the /input directory.
  * Clear the `save_path` line to prevent saving the image (it will still be saved in the TEMP-folder).
* If you enter a name in the `save_file_name_override` section, the file will be saved with this name.
  * You can enter or ignore the file extension.
  * If you enter one, it will rename the file to the chosen extension without converting the image.
* Supported image formats: JPG, JPEG, PNG, WEBP.
* Does not support saving with transparency.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/16401f43-5f7b-4590-908f-a71bbefc467b)

> [!IMPORTANT]
> #### 2024-09-14 - Version 1.2.0
> This node was renamed in the code to match the functionality. This may break existing nodes.

## 🔠 Tiktoken Tokenizer Info
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

## 🧹 String Cleaning
This node helps you quickly clean up and format strings by letting you remove leading or trailing spaces, periods, commas, or custom text, as well as removing linebreaks, or replacing them with a period.
- `input_string`: Your input string. Use [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) for looping through a list of strings.
- `collapse_sequential_spaces`: Collapses sequential spaces (" ") in a string into one.
- `strip_leading_spaces`: Removes any leading spaces from each line of the input string.
- `strip_trailing_spaces`: Removes any trailing spaces from each line of the input string.
- `strip_leading_symbols`: Removes leading punctuation symbols (, . ! ? : ;) from each line of the input string.
- `strip_trailing_symbols`: Removes leading punctuation symbols (, . ! ? : ;) from each line of the input string.
- `strip_inside_tags`: Removes any tags and the characters inside. <> would strip out anything like `<html>` or `</div>`, including the `<` and `>`
- `strip_newlines`: Removes any linebreaks in the input string.
- `replace_newlines_with_period_space`: Replaces any linebreaks in the input string with a ". ". If multiple linebreaks are found in a row, they will be replaced with a single ". ".
- `strip_leading_custom`: Removes any leading characters, words or symbols from each line of the input string. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `strip_trailing_custom`: Removes any trailing characters, words or symbols from each line of the input string. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `strip_all_custom`: Removes any characters, words or symbols found anywhere in the text. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `multiline_find`: Find and replace for multiple entries. Will be processed in order.
- `multiline_replace`: Find and replace for multiple entries. Will be processed in order.

---
### Clean up HTML
![image](https://github.com/user-attachments/assets/3d622652-5e49-41f0-9f9b-4aabcdd978ac)

---

### Make a salad
![image](https://github.com/user-attachments/assets/ba7678d4-d027-42cb-9330-b62de1a26a36)

---

### Work on your novel
![image](https://github.com/user-attachments/assets/c5a250f8-2aee-43c3-9394-f5a728e68a91)


## ✨💬 Groq LLM API Node
> [!IMPORTANT]
> #### 2025-01-12 - Version 1.2.4
> Moved groq API key to a .env instead of a config.ini-file. This will cause existing config setups to break with an update. Apologies for the inconvenience.
> #### 2024-09-14 - Version 1.2.0
> This node was renamed to match the new VLM and ALM nodes added.

This node makes an API call to groq, and returns the response in text format.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/807eb22d-c48b-4156-9d36-d2abdb987910)

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `GroqConfig.ini` file.

Currently, the Groq API can be used for free, with very friendly and generous [rate limits](https://console.groq.com/docs/rate-limits).


### Settings
**model**: Choose from a drop-down one of the available models. The list need to be manually updated when they add additional models.

**preset**: This is a dropdown with a few preset prompts, the user's own presets, or the option to use a fully custom prompt. See examples and presets below.

**system_message**: The system message to send to the API. This is only used with the `Use [system_message] and [user_input]` option in the preset list. The other presets provide their own system message.

**user_input**: This is used with the `Use [system_message] and [user_input]`, but can also be used with presets. In the system message, just mention the USER to refer to this input field. See the presets for examples.

**temperature**: Controls the randomness of the response. A higher temperature leads to more varied responses.

**max_tokens**: The maximum number of tokens that the model can process in a single response. Limits can be found [here](https://console.groq.com/docs/models).

**top_p**: The threshold for the most probable next token to use. Higher values result in more predictable results.

**seed**: Random seed. Change the `control_after_generate` option below if you want to re-use the seed or get a new generation each time.

**control_after_generate**: Standard comfy seed controls. Set it to `fixed` or `randomize` based on your needs.

**stop**: Enter a word or stopping sequence which will terminate the AI's output. The string itself will not be returned.

* Note: `stop` is not compatible with `json_mode`.

**json_mode**: If enabled, the model will output the result in JSON format.

* Note: You must include a description of the desired JSON format in the system message. See the examples below.

* Note: `json_mode` is not compatible with `stop`.

### Examples and presets
The following presets can be found in the `\nodes\groq\DefaultPrompts.json` file. They can be edited, but it's better to copy the presets to the `UserPrompts.json`-file.

-------------------------------
#### Use [system_message] and [user_input]

This preset, (default), means that the next two fields are fully utilized. Manually enter the instruction to the AI in the `system_message` field, and if you have any specific requests in the `user_input` field. Combined they make up the complete instruction to the LLM. Sometimes a system message is enough, and inside the system message you could even refer to the contents of the user input.
![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/0f06fb97-3553-4e3e-8e93-c587d0947006)

-------------------------------
#### Generate a prompt about [user_input]
This is a tailored instruction that will return a randomized Stable Diffusion-like prompt. If you enter some text in the `user_input` area, you should get a prompt about this subject. You can also leave it empty and it will create its own examples based on the underlying prompt.

You should get better result from providing it with a short sentence to start it off.
![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/96c47711-19e1-444d-a12a-1e95aaac4f26)

-------------------------------
#### Create a negative prompt for [user_input]
This will return a negative prompt which intends to be used together with the `user_input` string to complement it and enhance a resulting image.
![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/83dfe7f2-6d70-4cd4-9f15-66d78f6e88a7)


-------------------------------
#### List 10 ideas about [user_input]
This will return a list format of 10 subjects for an image, described in a simple and short style. These work good as `user_input` for the `Generate a prompt about [user_input]` preset.
![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/0d690ce2-1fda-46b5-8ad1-2f13b3f15d60)

-------------------------------
#### Return a JSON prompt about [user_input]
You should also manually turn on `json_mode` when using this prompt. You should get a stable json formatted output from it in a similar style to the `Generate a prompt about [user_input]` above.

Note: You can actually use the entire result (JSON and all), as your prompt. Stable Diffusion seem to handle it quite fine.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/5ed52bb2-3a1e-4ca3-9b2e-a7cbd53beae4)


### Create your own presets
Edit the `\nodes\groq\UserPrompts.json` file to create your own presets.

Follow the existing structure and look at the `DefaultPrompts.json` for examples.

## ✨📷 Groq VLM API Node
> [!IMPORTANT]
> #### 2024-09-27 - Version 1.2.1
> Added new Llama 3.2 vision model to the list, but this model is not yet officially available. Once it is, this should automatically work.

[Groq Vision Documentation](https://console.groq.com/docs/vision)

This node makes an API call to groq with an attached image and then uses Vision Language Models to return a description of the image, or answer to a question about the image in text format.

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `GroqConfig.ini` file.

Currently, the Groq API can be used for free, with very friendly and generous [rate limits](https://console.groq.com/docs/rate-limits).

### Restrictions
**Image Size Limit**: The maximum allowed size for a request containing an image URL as input is 20MB. Requests larger than this limit will return a 400 error.

**Request Size Limit (Base64 Enconded Images)**: The maximum allowed size for a request containing a base64 encoded image is 4MB. Requests larger than this limit will return a 413 error.

### Example: Custom prompt
![image](https://github.com/user-attachments/assets/783c85ea-cb3e-4338-903c-e8c9b30eaff3)

-------------------------------

### Example: Short Caption

![image](https://github.com/user-attachments/assets/e1c86199-1b1b-4e45-9203-f766bcc1f1ad)

-------------------------------

### Example: Medium Caption

![image](https://github.com/user-attachments/assets/804c38c9-5923-47fd-93a4-1716fff7508c)

-------------------------------

### Example: Long Caption

![image](https://github.com/user-attachments/assets/7cd027b3-a1df-48e3-a699-95d9a15350e9)

-------------------------------

### Example: Primary Color

![image](https://github.com/user-attachments/assets/b5e212f9-8d3f-47c5-8666-7762467cddc2)


-------------------------------



## ✨📝 Groq ALM API Node

[Groq Speech Documentation](https://console.groq.com/docs/speech-text)

This node makes an API call to groq with an attached audio file and then uses Audio Language Models to transcribe the audio and return the text in different output formats.

The model `distil-whisper-large-v3-en` only supports the language `en`.
The model `whisper-large-v3` supports the languages listed below. It can also be left empty, but this provides worse results than running the model locally.

> [!NOTE]
> The presets / prompt do very little. They are meant to help you guide the output, but I don't get any relevant results.

You can convert the `file_path` to input to use the [Get File Path](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/edit/main/README.md#-get-file-path) node to find your files.


### Supported Languages
[https://www.wikiwand.com/en/articles/List_of_ISO_639_language_codes](https://www.wikiwand.com/en/articles/List_of_ISO_639_language_codes)
> is tg uz zh ru tr hi la tk haw fr vi cs hu kk he cy bs sw ht mn gl si mg sa es ja pt lt mr fa sl kn uk ms ta hr bg pa yi fo th lv ln ca br sq jv sn gu ba te bn et sd tl ha de hy so oc nn az km yo ko pl da mi ml ka am tt su yue nl no ne mt my ur ps ar id fi el ro as en it sk be lo lb bo sv sr mk eu

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `GroqConfig.ini` file.

Currently, the Groq API can be used for free, with very friendly and generous [rate limits](https://console.groq.com/docs/rate-limits).

### Example: Transcribe meeting notes

![image](https://github.com/user-attachments/assets/4b9d2e31-96df-462e-bc18-eba6e381fa34)

-------------------------------

### Example: Generate image based on voice description or a story

![image](https://github.com/user-attachments/assets/926a6086-dccc-47dd-9f3b-86326976a62d)


-------------------------------

### Example: Transcribe song lyrics

![image](https://github.com/user-attachments/assets/2ec34e49-fbea-465a-9653-6bc1fbb34a13)

-------------------------------

### Karaoke?
You can use this to generate files to use in a [Karaoke app](https://github.com/MNeMoNiCuZ/whisper-karaoke). 

![image](https://github.com/user-attachments/assets/e4d7160b-90ab-4630-8568-2a65b7a79575)



## ⛔ Generate Negative Prompt Node

> [!CAUTION]
> This node is highly experimental, and does not produce any useful result right now. It also requires you to download a specially trained model for it. It's just not worth the effort. It's mostly here to share a work in progress project.

This node utilizes a GPT-2 text inference model to generate a negative prompt that is supposed to enhance the aspects of the positive prompt.

![Generate Negative Prompt Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/fcb3e8cc-30ec-4f56-838d-777657aee90b)

![Generated Negative Prompt Example](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/a3decef7-917f-4a98-beef-66dd403bca23)

> [!IMPORTANT]
> **Installation Step:**
> Download the [weights.pt file](https://huggingface.co/mnemic/NegativePromptGenerator/blob/main/weights.pt) from the project's [Hugging Face repository](https://huggingface.co/mnemic/NegativePromptGenerator/tree/main).
>
> Place the `weights.pt` file in the following directory of your ComfyUI setup without renaming it:
> ```
> \ComfyUI\custom_nodes\ComfyUI-mnemic-nodes\nodes\negativeprompt
> ```
> The directory should resemble the following structure:
>
> ![Installation Directory](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/8deb9cba-2800-4ab9-a391-832661bda7bd)

For additional information, please visit the [project's GitHub page](https://github.com/MNeMoNiCuZ/NegativePromptGenerator).
