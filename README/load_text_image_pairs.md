# 🖼️+📝 Load Text-Image Pairs

This document describes two nodes for loading pairs of images and text files.

-   **Load Text-Image Pairs (List):** Use this for loading and caching entire datasets.
-   **Load Text-Image Pair (Single):** Use this for quickly loading a single pair from a dataset without caching.

---

## 🖼️+📝 Load Text-Image Pairs (List)

This node loads an entire dataset of image and text pairs from a folder. It is designed for performance when you need to iterate through or use the full list of items.

**Key Feature: Caching**
The first time this node is run on a folder, it loads all images, processes them into a batched tensor, and stores the result in memory. Subsequent runs are nearly instantaneous as they use the cached data.

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

<img width="1646" height="982" alt="image" src="https://github.com/user-attachments/assets/5dfca806-2245-4c96-9e34-6216ec1609aa" />

### Inputs
-   `seed`: The starting index for selecting pairs. Set to `increment` to cycle through the dataset.
-   `folder_path`: Path to a folder containing image and text files with matching names.
-   `force_reload`: A checkbox to force the node to discard the cache and reload all data from the disk.
-   `limit_count`: (Optional) The maximum number of pairs to return in the list outputs. `0` returns all pairs.
-   `text_format_extension`: (Optional) The extension for text files (e.g., `txt`, `caption`). Default is `txt`.

### Outputs
-   `image_single`: The single image selected by the `seed`.
-   `string_single`: The text paired with the selected image.
-   `image_path_single`: The full absolute path of the selected image.
-   `image_filename_single`: The filename (without extension) of the selected image.
-   `image_list`: A list of all images in the dataset.
-   `string_list`: A list of all text strings in the dataset.
-   `image_path_list`: A list of full absolute paths for all images.
-   `image_filename_list`: A list of filenames for all images.
-   `total_count`: The total number of pairs found in the dataset.

---

## 🖼️+📝 Load Text-Image Pair (Single)

This node loads only one specific image-text pair from a folder. It is designed to be extremely fast and lightweight.

**Key Feature: No Caching**
This node does not cache any data. It reads the requested files directly from the disk on every run. Use this when you only need a single item from a dataset and don't want to spend time pre-loading the entire set.

### Inputs
-   `seed`: The index of the pair to load.
-   `folder_path`: Path to a folder containing image and text files with matching names.
-   `image_input`: (Optional) A single image or a batch of images. Overrides `folder_path`.
-   `text_input`: (Optional) A single string or a list of strings. Overrides `folder_path`.
-   `text_format_extension`: (Optional) The extension for text files (e.g., `txt`, `caption`). Default is `txt`.

### Outputs
-   `image_single`: The single image selected by the `seed`.
-   `string_single`: The text paired with the selected image.
-   `image_path_single`: The full absolute path of the selected image.
-   `image_filename_single`: The filename (without extension) of the selected image.
-   `total_count`: The total number of pairs found in the dataset.