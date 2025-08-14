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
