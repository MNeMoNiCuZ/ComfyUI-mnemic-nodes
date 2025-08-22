# 📐 Resolution Image Size Selector

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
