# 🖼️ Load Images From Path

A lightweight image loader that supports loading multiple images, one at a time from a folder.

## Usage

Set the `seed iteration type` to `INCREMENT` to step through the images of the input folder with 1 per generation.

Set the initial seed to 0 to start with the first image.

<img width="1645" height="525" alt="Load Images From Path Node" src="https://github.com/user-attachments/assets/example-screenshot2.png" />

## Inputs

-   `seed`: The index of the image to load from the directory. The count wraps around, so if you provide a seed of 5 and there are only 5 images, it will load the first image (index 0).
-   `input_path`: The path to a folder containing images or to a single image file.
    -   If the path is to a single file, it will be loaded directly.
    -   If the path is to a directory, the node will iterate through all supported image files (`PNG`, `JPG`, `JPEG`, `WEBP`, `BMP`, `GIF`) within it.
    -   Relative paths are resolved from ComfyUI's `input` directory. If the path is left empty, it defaults to the `input` directory.

## Outputs

-   `image`: The loaded image (IMAGE tensor).
-   `mask`: The alpha channel of the image as a MASK tensor. If the image has no alpha channel, a solid black mask is generated.
-   `image_path`: The full absolute path to the loaded image file (STRING).
-   `current_index`: The zero-based index of the currently loaded image from the directory (INT).
-   `total_count`: The total number of images found in the directory (INT).
