# 🖼️+📝 Load Text-Image Pair (Single)

Loads one image together with its caption file — the layout used by most
training datasets, where `photo_01.png` sits next to `photo_01.txt`.

## Inputs

- **seed** — Which pair to load. Set its control to **increment** to walk the
  dataset.
- **folder_path** — Folder holding the images and text files. Used only when
  the two direct inputs below are not connected.
- **image_input** *(optional)* — An image already in the workflow.
- **text_input** *(optional)* — Text already in the workflow. When both direct
  inputs are connected they take priority and the folder is ignored.
- **text_format_extension** *(optional)* — Extension of the caption files,
  without the dot. Default `txt`.

## Outputs

- **image_single** — The selected image.
- **string_single** — Its caption text.
- **image_path_single** — Full path of the image.
- **image_filename_single** — Filename without the extension.
- **total_count** — How many pairs the folder holds.

## Notes

Pairing is by matching basename. An image with no caption file is not a pair
and is skipped. A missing folder returns empty outputs with a `total_count` of
0. When using the direct inputs, the path and filename outputs are empty
because there is no file behind them.
