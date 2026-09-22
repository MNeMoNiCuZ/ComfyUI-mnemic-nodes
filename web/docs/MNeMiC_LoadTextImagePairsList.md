# 🖼️+📝 Load Text-Image Pairs (List)

The list version of 🖼️+📝 Load Text-Image Pair (Single): returns the whole
dataset as parallel lists, rotated so the seed picks the starting point.

## Inputs

- **seed** — Where the lists start. Set its control to **increment** to rotate.
- **folder_path** — Folder holding the images and caption files.
- **force_reload** — Re-read from disk instead of using the cache. Turn it on
  after changing files on disk, then off again.
- **image_input** / **text_input** *(optional)* — Data already in the workflow.
  When both are connected they take priority over the folder.
- **limit_count** *(optional)* — Cap on how many pairs to return. `0` returns
  all of them.
- **text_format_extension** *(optional)* — Caption file extension without the
  dot. Default `txt`.

## Outputs

All in the same order, one entry per pair:

- **image_list** — The images, as one batch.
- **string_list** — The captions.
- **image_path_list** — Full paths.
- **image_filename_list** — Filenames without extensions.
- **total_count** — How many pairs the dataset holds.

## Notes

The folder is read once and cached per path; `force_reload` clears it. Images
whose dimensions differ from the first are resized and centre-cropped so the
batch is uniform. A single text input paired with several images is applied to
all of them; a list of texts is truncated to match the shorter of the two.
