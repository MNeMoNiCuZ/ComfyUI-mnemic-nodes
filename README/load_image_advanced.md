# 🖼️ Load Image Advanced

The `Load Image Advanced` node is an enhanced version of the default `Load Image` node in ComfyUI. It not only loads an image but also extracts useful information from it, providing multiple outputs for a more streamlined workflow.

<img width="1933" height="875" alt="image" src="https://github.com/user-attachments/assets/43dc1746-e4f4-40d8-9d95-6a4ee637e5cf" />

## Features

-   **Image Loading**: Loads an image from your input directory or via direct upload.
-   **Metadata Extraction**: Automatically extracts the positive prompt from the image's metadata, if available. This is useful for re-using prompts from previously generated images.
-   **Alpha Channel as Mask**: If the image has an alpha channel (transparency), it is output as a separate mask.
-   **Dimension Outputs**: Provides the width and height of the image as separate integer outputs.
-   **File Path Output**: Outputs the full path to the loaded image file.

## Inputs

-   `image`: An image file to load. You can select a file from your ComfyUI `input` folder or upload a new one.

## Outputs

-   `image`: The loaded image, ready to be used in your workflow (IMAGE tensor).
-   `mask`: The alpha channel of the image as a MASK tensor. If the image has no alpha channel, a solid black mask is generated.
-   `image_path`: The full file path of the loaded image (STRING).
-   `positive_prompt`: The positive prompt extracted from the image's metadata (STRING).
-   `width`: The width of the image in pixels (INT).
-   `height`: The height of the image in pixels (INT).

## Example Workflow

You can use this node to easily load an image and reuse its prompt, or use its alpha channel as a mask for inpainting or other operations. The width and height outputs are useful for dynamically setting resolutions in your workflow.

*(placeholder for an image of the node in action)*
