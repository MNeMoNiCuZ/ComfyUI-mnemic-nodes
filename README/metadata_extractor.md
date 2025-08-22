# 🖼️📊 Metadata Extractor

Extracts metadata from input images.

The input images are loaded via a path. Either directly to an image file, or to a folder with multiple images. 

The metadata should work on both jpg and png images, and it will do what it can to extract from A1111/Forge/ComfyUI image metadata.

<img width="1570" height="1223" alt="image" src="https://github.com/user-attachments/assets/a7260261-b755-4e15-be33-749e3035f801" />

Can output both single image metadata (and step through one image at a time), or all images at once into a list.

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

- **Inputs**:
    - `seed`: An integer that sets the starting index for selecting image-metadata pairs. Use the `increment` option in workflow settings to cycle through pairs sequentially.
    - `input_path`: A string specifying the path to a folder containing images or a single image file. Only used if `image_input` is not provided.
    - `image_input`: A single image or a batch/list of images. Takes priority over `input_path`.
    - `filter_params`: A comma-separated string of case-insensitive keys (e.g., `steps, sampler, seed`) to extract specific metadata parameters.
    - `max_file_count`: An integer limiting the total number of image-metadata pairs returned. Set to 0 to include all available pairs.

- **Outputs**:
    - `image_single`: The single image selected based on the `seed` index from the input list.
    - `positive_prompt_single`: The positive prompt extracted from the selected image's metadata.
    - `negative_prompt_single`: The negative prompt extracted from the selected image's metadata.
    - `parsed_params_single_json`: All parsed metadata parameters from the selected image, returned as a JSON string.
    - `filtered_params_single_list`: Specific metadata values requested in `filter_params` from the selected image, returned as a multi-line string.
    - `raw_metadata_single_json`: The complete, unprocessed metadata of the selected image, formatted as a JSON string.
    - `image_list`: A list of all images from the input, scaled to match the aspect ratio of the first image and cropped to its resolution.
    - `positive_prompt_list`: A list of all positive prompts extracted from the input images' metadata.
    - `negative_prompt_list`: A list of all negative prompts extracted from the input images' metadata.
    - `parsed_params_list_json`: A list of all parsed metadata parameter sets, each as a JSON string.
    - `filtered_params_list_grouped`: A list of all filtered metadata parameter sets, each as a multi-line string.
    - `raw_metadata_list_json`: A list of all raw metadata sets, each formatted as a JSON string.

<img width="1814" height="1122" alt="image" src="https://github.com/user-attachments/assets/26ca04f1-3409-428a-9a3f-e4bb8fd9d215" />
