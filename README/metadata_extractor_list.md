# 🖼️📊 Metadata Extractor (List)

Extracts metadata from a list of images or a folder of images.

The input images are loaded via a path. Either directly to an image file, or to a folder with multiple images. The metadata should work on both jpg and png images, and it will do what it can to extract from A1111/Forge/ComfyUI image metadata.

<img width="2204" height="1155" alt="image" src="https://github.com/user-attachments/assets/fbb48ea8-e9f9-44b2-b661-11527d0288dc" />


> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

> [!WARNING]
> Be mindful of the `max_file_count` setting when working with large folders. Loading a large number of images can consume a significant amount of memory and slow down your workflow. It is recommended to set a reasonable limit to avoid performance issues.

Without a `max_file_count` limit, things will take a long time to load each time and comfy will get super laggy if you load a folder with hundreds or thousands of images. Each will be loaded into memory at the same time.

<img width="1604" height="680" alt="image" src="https://github.com/user-attachments/assets/00b6a7b2-f5a7-4fad-9d9c-be2b3a0bd485" />

Use the [Metadata Extractor (Single)](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/edit/main/README/metadata_extractor_single.md) if you only need one image at a time!

- **Inputs**:
    - `seed`: An integer that sets the starting index for selecting image-metadata pairs. Use the `increment` option in workflow settings to cycle through pairs sequentially.
    - `input_path`: A string specifying the path to a folder containing images or a single image file. Only used if `image_input` is not provided.
    - `image_input`: A single image or a batch/list of images. Takes priority over `input_path`.
    - `filter_params`: A comma-separated string of case-insensitive keys (e.g., `steps, sampler, seed`) to extract specific metadata parameters.
    - `max_file_count`: An integer limiting the total number of image-metadata pairs returned. Set to 0 to include all available pairs.

- **Outputs**:
    - `image`: A list of all images from the input, scaled to match the aspect ratio of the first image and cropped to its resolution.
    - `positive_prompt`: A list of all positive prompts extracted from the input images' metadata.
    - `negative_prompt`: A list of all negative prompts extracted from the input images' metadata.
    - `parsed_params_json`: A list of all parsed metadata parameter sets, each as a JSON string.
    - `filtered_params_grouped`: A list of all filtered metadata parameter sets, each as a multi-line string.
    - `raw_metadata_json`: A list of all raw metadata sets, each formatted as a JSON string.

For extracted params, you can use the [String Text Splitter](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/blob/main/README/string_text_splitter.md) node to further split up the results into usable chunks.

<img width="2142" height="724" alt="image" src="https://github.com/user-attachments/assets/3cb4fe24-780d-4fd9-be90-bf90bfd81377" />
