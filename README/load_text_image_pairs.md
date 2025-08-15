## 🖼️+📝 Load Text-Image Pairs

Loads image and text pairs from a folder, or from separate inputs, and groups them together in a list.

This could be used to load and view datasets, or if you have a matching caption or description file to an image, or text generated in a workflow. Essentially you use this to pair up the data, and then you can step through it one by one, or all at once.

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

<img width="1646" height="982" alt="image" src="https://github.com/user-attachments/assets/5dfca806-2245-4c96-9e34-6216ec1609aa" />

### Inputs
-   `seed`: The starting index for selecting pairs. Set to `increment` to cycle through the dataset.
-   `folder_path`: Path to a folder containing image and text files with matching names.
-   `image_input`: (Optional) A single image or a batch of images. Overrides `folder_path`.
-   `text_input`: (Optional) A single string or a list of strings. Overrides `folder_path`.
-   `max_pair_count`: (Optional) The maximum number of pairs to return. `0` returns all pairs.
-   `text_format_extension`: (Optional) The extension for text files (e.g., `txt`, `caption`). Default is `txt`.

### Outputs
-   `image_single_output`: The single image selected by the `seed`.
-   `string_single_output`: The text paired with the selected image.
-   `image_list_output`: A list of all images in the dataset.
-   `string_list_output`: A list of all text strings in the dataset.
-   `full_path_single`: The absolute file path of the selected image.
-   `filename_single`: The filename (without extension) of the selected image.
-   `full_path_list`: A list of absolute file paths for all images.
-   `filename_list`: A list of filenames for all images.

You can also use the optional image + text manual inputs instead of paths. They have a higher priority if they are used.
<img width="2245" height="960" alt="image" src="https://github.com/user-attachments/assets/c285c150-dad2-4ca4-b475-c64cfb02ed24" />
