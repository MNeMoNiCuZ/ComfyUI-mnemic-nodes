# 🖼️📊 Metadata Extractor (Single)

Extracts metadata from a single image selected from an input source.

The input images are loaded via a path, either directly to an image file or to a folder with multiple images. The metadata should work on both jpg and png images, and it will do what it can to extract from A1111/Forge/ComfyUI image metadata.

<img width="1570" height="1223" alt="image" src="https://github.com/user-attachments/assets/a7260261-b755-4e15-be33-749e3035f801" />

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

- **Inputs**:
    - `seed`: An integer that sets the starting index for selecting image-metadata pairs. Use the `increment` option in workflow settings to cycle through pairs sequentially.
    - `input_path`: A string specifying the path to a folder containing images or a single image file. Only used if `image_input` is not provided.
    - `image_input`: A single image or a batch/list of images. Takes priority over `input_path`.
    - `filter_params`: A comma-separated string of case-insensitive keys (e.g., `steps, sampler, seed`) to extract specific metadata parameters.

- **Outputs**:
    - `image`: The single image selected based on the `seed` index from the input list.
    - `positive_prompt`: The positive prompt extracted from the selected image's metadata.
    - `negative_prompt`: The negative prompt extracted from the selected image's metadata.
    - `parsed_params_json`: All parsed metadata parameters from the selected image, returned as a JSON string.
    - `filtered_params_list`: Specific metadata values requested in `filter_params` from the selected image, returned as a multi-line string.
    - `raw_metadata_json`: The complete, unprocessed metadata of the selected image, formatted as a JSON string.
