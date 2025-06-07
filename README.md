# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects. Some nodes are forks or versions of  nodes from other packs, some are bespoke and useful, and some are experimental and are quite useless, so they have been marked with a `Caution` label in this document.

[📝 Wildcard Processor](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-wildcard-processor) - A versatile text processor that replaces wildcards with content from files or inline lists.

[📁 Get File Path](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-get-file-path) - Returns the file path in different formats to a file in your /input-folder.

[💾 Save Text File With Path](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-save-text-file-with-path) - Save text file, and return the saved file's path.

[🖼️ Download Image from URL](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#%EF%B8%8F-download-image-from-url) - Download an image from the web.

[🔠 Tiktoken Tokenizer Info](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-tiktoken-tokenizer-info) - Returns token information about input text and lets you split it.

[🧹 String Cleaning](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-string-cleaning) - Cleans up text strings.

[✂️ String Text Splitter](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#%EF%B8%8F-string-text-splitter) - Splits a string by the first occurrence of a delimiter.

[✂️ String Text Extractor](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#%EF%B8%8F-string-text-extractor) - Extracts the first occurrence of text between a pair of characters.

[🏷️ LoRA Loader Prompt Tags](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#%EF%B8%8F-lora-loader-prompt-tags) - Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.

[📐 Resolution Image Size Selector](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/tree/main?tab=readme-ov-file#-resolution-image-size-selector) - Creates resolutions and a latent from presets, user presets, or input images.

[✨💬 Groq LLM API](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-llm-api) - Query Groq large language model.

[✨📷 Groq VLM API](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-vlm-api) - Query Groq vision language model.

[✨📝 Groq ALM API](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-groq-alm-api) - Query Groq Audio Model.

[⛔ Generate Negative Prompt](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes?tab=readme-ov-file#-generate-negative-prompt) - Generate negative prompts automatically.


# Installation instructions
## Configuration (only needed for Groq nodes)

1. Make a copy of `.env.example` and remove the `.example` from the name.
2. The new file should now be named `.env` without a normal file name, just a .env extension.
3. The file should be in the root of the node pack, so the same directory that the .example was in.
4. Edit `.env` with a text editor and edit the API key value inside.

# Nodes

## 📝 Wildcard Processor

This node adds powerful dynamic capabilities to your prompts. Wildcards are generally used to randomize your output, by writing the prompt in a specific format, or loading random lines from text-files.

Here is a summary of the features and syntax.

### Smart Wildcard Matching
Smart wildcard matching:\nThe node will try to find the best match for a wildcard, even if the name is not an exact match. It will search for files in the wildcards directories and use the best match based on a scoring system. Exact matches have priority, and more root level files have priority after that.

### Multiple Wildcard Paths
Wildcards can be placed in different directories. It's recommended to only use one, but they can all be combined.
Paths:
- `ComfyUI/wildcards`
- `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards`

or in a user-defined path in:

- `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json`

### File Wildcards

Loads a random line from a text-file in the wildcards directory.

![image](https://github.com/user-attachments/assets/0c57e27c-2e78-41c4-afde-62c6de186141)

-   **Syntax**: `__filename__`
-   **Description**: Inserts a random line from a `.txt` file found in one of the supported `wildcards` directories.
    -   `ComfyUI/wildcards/`
    -   `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards/`
    -   or in a user-defined path in
        -   `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json`
-   **Example**: `A photo of a __color__ __animal__.` -> `A photo of a blue frog.`
-   Empty lines are automatically discarded.
-   Comments can be made using `# commented line`

---

### Inline Wildcards

Creates a wildcard right in the prompt instead of loading from a file.

![image](https://github.com/user-attachments/assets/848e6b2a-5a13-48ee-8063-8935337fe2eb)

-   **Syntax**: `{option1|option2|option3}`
-   **Description**: Chooses one of the provided options.
-   **Example**: `A {red|green|blue} car.` -> `A green car.`

---

### Weighted Choices

Makes one entry more likely to be chosen than others.

![image](https://github.com/user-attachments/assets/bbceea2a-3c23-4c3c-b19d-efc91bf705a1)

-   **Syntax**: `{weight::option1|option2}`
-   **Description**: Changes the chance that an option gets randomly selected. `weight` is an integer number (e.g., `5`). Default weight is 1.
-   **Example**: `A {4::red|2::green|blue} car.` -> `A red car.`
    -   Red is chosen randomly 4 times more often than Blue
    -   Green is twice as likely to be chosen as Blue
    -   Red is twice as likely to be chosen as Green

---

### Multiple Selections (Fixed & Ranged)

Returns X number of wildcard results based the input number. The input can also be a range.

![image](https://github.com/user-attachments/assets/9251f16c-6824-49e0-a560-91c71dd4dbe0)


-   **Syntax**: `{N$$...}` for a fixed number, `{N-M$$...}` for a random range.
-   **Description**: Selects multiple unique items from a list, joined by the `multiple_separator` string.
-   **Example (Fixed)**:
    -   **Prompt**: `{2$$red|green|blue|purple}`
    -   **Output**: `red, green`
-   **Example (Range)**:
    -   **Prompt**: `A {1-3$$red|green|blue|purple|white|gold} outfit`
    -   **Output**: `blue, white, purple` (Randomly got 1-4 outputs, we got 3 in this case. Each entry can only be chosen once)
-   There is an option for the separator in the node. This is inserted between each selected entry.

---

### Variables

Define a variable to reuse a value. Can be defined directly, or using a wildcard. This can be useful if you want to randomize a part, but want to re-use the randomized value multiple times in your prompt.

![image](https://github.com/user-attachments/assets/d12c52d4-b6e7-4aee-a3bf-ac36edaa708d)


-   **Syntax**: `${var=!{...}}` and `${var}`
-   **Description**: Defines a variable `${var}` with a dynamic value that can be reused.
-   **Example**: `${animal=!__animals__} The ${animal} is friends with the other ${animal}.` -> `The cat is friends with the other cat.`

---

### Nesting

Everything can be combined into more complex prompts.

![image](https://github.com/user-attachments/assets/3ea9a7ce-440b-44f2-91e5-2b1f82dd80f5)


-   **Description**: All features can be nested.
-   **Example**: `A {3::big|small|__color__} __animal__ wearing a {2$$__color__} jacket` -> `A big Panda wearing a pink blue jacket`

---

### Glob Wildcards

Use * as wildcards for your wildcards. Use this when you want to select a random output from multiple files matching the same pattern, or from all files in a folder.

[More information](https://pymotw.com/2/glob/)

![image](https://github.com/user-attachments/assets/bd0d3335-88f2-4a2c-8340-6d89839960dc)

-   **Syntax**: `__*filename*__`
-   **Description**: Uses glob patterns to match multiple files. It collects all lines from all matched files and picks one randomly.
-   **Example**: `a __*color*__ vase` -> `A green vase` (Selected from all wildcard files that has the word `color` in their name)


You can also use it to randomly select a random wildcard file from inside a folder.

![image](https://github.com/user-attachments/assets/b8b1451f-ac93-4cd4-b9b6-fb114e3ac583)


-   **Syntax**: `__path/to/*__`
-   **Description**: Uses glob patterns to match all files inside a folder. A random file is chosen.
-   **Example**: `__environment/*__` -> africa.txt `Majestic views of the Kabylie mountains in Algeria at midday.` (Selected from a random wildcard file in the /environment subfolder)


---

### Seed Output

-   **Description**: The node outputs the integer `seed` that was used for the generation. This is useful if you want to match seeds in multiple nodes.

---

### Tag Extraction

Advanced functionality that lets you extract encapsulated results from the final prompt.

![image](https://github.com/user-attachments/assets/b28b6a71-e19e-46bf-81c1-7276bd59e5a4)


-   **Syntax**: Define delimiter pairs in the `tag_extraction_tags` input (e.g., `[],<>`). Then use them in your prompt: `A prompt with [tagged content] and <more>`.
-   **Description**: Extracts content from the defined tags. The content is processed for wildcards and removed from the main prompt.
-   **Outputs**:
    - `processed_text`: The prompt with tags removed.
    - `extracted_tags_string`: Processed content from tags, joined by `|`.
    - `extracted_tags_list`: A list of the processed tag contents.
    - `raw_tags_string`: The re-assembled tags (including delimiters) with their content processed.
    - `raw_tags_list`: A list of the re-assembled, processed tags.
-   **Tip**: Use the `String Text Splitter` node to split the `extracted_tags_string` output.
-   **Tip**: Use the `String Text Extractor` node to capture the values of the `raw_tags_string` output.

---

## 📁 Get File Path

This node returns the file path of a given file in the \input-folder.

![image](https://github.com/user-attachments/assets/1fd9bfdc-f92d-4f33-a992-a5af66029a9f)

It is meant to have a browse-button so you can browse to any file, but it doesn't yet.

**If you know how to add this, please let me know or do a pull request.**


## 💾 Save Text File With Path

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


## 🖼️ Download Image from URL

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
### Remove \<think\> tags
![image](https://github.com/user-attachments/assets/fe120033-c6c8-4ea6-a204-a8dbb270a6a9)

---

### Clean up HTML
![image](https://github.com/user-attachments/assets/3d622652-5e49-41f0-9f9b-4aabcdd978ac)

---

### Make a salad
![image](https://github.com/user-attachments/assets/ba7678d4-d027-42cb-9330-b62de1a26a36)

---

### Work on your novel
![image](https://github.com/user-attachments/assets/c5a250f8-2aee-43c3-9394-f5a728e68a91)

## ✂️ String Text Splitter

![image](https://github.com/user-attachments/assets/431ccbfe-3d33-4e5b-b813-9d824bb20bb6)

-   **Description**: Splits a string by a delimiter.
-   **Inputs**:
    -   `input_string`: The text to split.
    -   `delimiter`: The character to split on.
-   **Outputs**:
    -   `first_chunk`: The part of the string before the first delimiter.
    -   `remainder`: The rest of the string after the first delimiter.
    -   `chunk_list`: A list of all items split by the delimiter.

## ✂️ String Text Extractor

![image](https://github.com/user-attachments/assets/68a745b5-9b63-4796-8fd2-f1224d0e1510)

-   **Description**: Extracts text between a pair of delimiters.
-   **Inputs**:
    -   `input_string`: The text to search within.
    -   `delimiters`: The pair of characters to use as delimiters (e.g., `[]`, `**`).
-   **Outputs**:
    -   `extracted_text`: The content found inside the first pair of delimiters.
    -   `remainder_text`: The rest of the text after the extracted content and its delimiters are removed.
    -   `extracted_list`: A list of all items found between the delimiters.

## 🏷️ LoRA Loader Prompt Tags

Loads LoRA models using `<lora:MyLoRA:1>` in the prompt.

![image](https://github.com/user-attachments/assets/595fdb36-1442-4c0a-abf4-b1779674c515)

Route the model and clip through the node.

Use the output [STRING] to have the prompt without the `<lora::>`-tags.

## 📐 Resolution Image Size Selector

Creates resolutions and a latent from presets, user presets, or input images.

![image](https://github.com/user-attachments/assets/d40e27d7-e17d-4750-b88b-9cf39b654823)

Use the preset drop-down for some image generation standard resolutions.

The preset_user input will be created on first launch, and you can edit the config for this in: `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/resolution_selector/user_resolution.json`

The custom width and height values are only used with the `Custom` preset.

The multiply scale multiplies the final results and outputs them as `multiplied_width` and `multiplied_height`. This is useful when it comes to figuring out a desired upscale resolution based on variable inputs.

The `swap_width_and_height` option swaps the final width and height.

The image input can be used. This has the highest priority. If it is used, we then take the image input width and height.

`image_min_length` ensures that an input image size has at least this length on its shortest side.

`image_max_length` ensures that an input image size has at most this length on its longest side.

The `snap_to_nearest` ensures specific snapping on the final output value. This can be set to 8 or 16 for good divisible sizes, or any value that you need to work with.

The `batch_size` option is used to create multiple output latents when you use tha latent output node.


## ✨💬 Groq LLM API
> [!IMPORTANT]
> #### 2025-01-12 - Version 1.2.4
> Moved groq API key to a .env instead of a config.ini-file. This will cause existing config setups to break with an update. Apologies for the inconvenience.
> #### 2024-09-14 - Version 1.2.0
> This node was renamed to match the new VLM and ALM nodes added.

This node makes an API call to groq, and returns the response in text format.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/807eb22d-c48b-4156-9d36-d2abdb987910)

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `.env` file. A template file is provided and can be renamed to `.env` for use.

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

## ✨📷 Groq VLM API
> [!IMPORTANT]
> #### 2024-09-27 - Version 1.2.1
> Added new Llama 3.2 vision model to the list, but this model is not yet officially available. Once it is, this should automatically work.

[Groq Vision Documentation](https://console.groq.com/docs/vision)

This node makes an API call to groq with an attached image and then uses Vision Language Models to return a description of the image, or answer to a question about the image in text format.

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `.env` file. A template file is provided and can be renamed to `.env` for use.

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



## ✨📝 Groq ALM API

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
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `.env` file. A template file is provided and can be renamed to `.env` for use.

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



## ⛔ Generate Negative Prompt

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
