# 🖼️ Load Images From Path

A lightweight image loader that supports loading multiple images, one at a time from a folder.

<img width="2240" height="775" alt="image" src="https://github.com/user-attachments/assets/71ef1566-7b4b-4030-afbd-3eef9eccf686" />


## Usage
> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

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
