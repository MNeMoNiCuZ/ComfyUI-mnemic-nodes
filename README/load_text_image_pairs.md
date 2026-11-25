# 🖼️+📝 Load Text-Image Pairs

This document describes two nodes for loading pairs of images and text files.

-   **Load Text-Image Pairs (List):** Use this for loading and caching entire datasets.
-   **Load Text-Image Pair (Single):** Use this for quickly loading a single pair from a dataset without caching.

---

<a id="load-text-image-pairs-list"></a>

## 🖼️+📝 Load Text-Image Pairs (List)

This node loads an entire dataset of image and text pairs from a folder. It is designed for performance when you need to iterate through or use the full list of items.

**Key Feature: Caching**
The first time this node is run on a folder, it loads all images, processes them into a batched tensor, and stores the result in memory. Subsequent runs are nearly instantaneous as they use the cached data.

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

<img width="1646" height="982" alt="image" src="https://github.com/user-attachments/assets/5dfca806-2245-4c96-9e34-6216ec1609aa" />

### Inputs
-   `seed`: The starting index for selecting pairs. Set to `increment` to cycle through the dataset.
-   `input_path` selects a folder containing images and optional captions with matching basenames. Relative paths start in ComfyUI's input folder. An image without a caption gets an empty string.
-   Connect both `image_input` and `text_input` to use workflow data instead of a folder. A single caption applies to the whole batch.
-   `force_reload`: A checkbox to force the node to discard the cache and reload all data from the disk.
-   `limit_count`: (Optional) The maximum number of pairs to return in the list outputs. `0` returns all pairs.
-   `text_format_extension`: (Optional) The extension for text files (e.g., `txt`, `caption`). Default is `txt`.

### Outputs
-   `image_list` is an image batch starting at the seed-selected pair and wrapping around. Folder images are resized and center-cropped to match the first image's dimensions when needed.
-   `string_list`, `image_path_list` and `image_filename_list` contain the corresponding captions, full paths and filenames without extensions, in batch order. Direct inputs have empty path and filename entries.
-   `total_count`: The total number of pairs found in the dataset.

---

<a id="load-text-image-pair-single"></a>

## 🖼️+📝 Load Text-Image Pair (Single)

This node loads only one specific image-text pair from a folder. It is designed to be extremely fast and lightweight.

**Key Feature: No Caching**
This node does not cache any data. It reads the requested files directly from the disk on every run. Use this when you only need a single item from a dataset and don't want to spend time pre-loading the entire set.

### Inputs
-   `seed`: The index of the pair to load.
-   `input_path` selects a folder containing images and optional captions with matching basenames. Relative paths start in ComfyUI's input folder. An image without a caption gets an empty string.
-   Connect both `image_input` and `text_input` to pass the supplied image or batch and text through directly. In this mode the path and filename outputs are empty, and `total_count` is the batch size.
-   `text_format_extension`: (Optional) The extension for text files (e.g., `txt`, `caption`). Default is `txt`.

### Outputs
-   `image_single`: The single image selected by the `seed`.
-   `string_single`: The text paired with the selected image.
-   `image_path_single`: The full absolute path of the selected image.
-   `image_filename_single`: The filename (without extension) of the selected image.
-   `total_count`: The total number of pairs found in the dataset.
