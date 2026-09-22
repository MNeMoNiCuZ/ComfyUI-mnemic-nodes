# 📂 Load Images From Path

Loads one image from a folder, chosen by index. The seed starts at 0 and its
control defaults to **increment**, so each run loads the next image.

## Inputs

- **seed** — Which image to load. It wraps, so any number is valid.
- **input_path** — A folder or a single image file. Relative paths are resolved
  inside ComfyUI's `input` folder.

## Outputs

- **image** — The selected image.
- **mask** — Alpha channel, or fully black if the file has none.
- **image_path** — Full path of the file that was loaded.
- **current_index** — The index actually used (seed wrapped to the file count).
- **total_count** — How many images were found.

## Notes

Files are sorted by name, so the order is stable. Recognised extensions are
png, jpg, jpeg, webp, bmp and gif. An empty path is an error; a path with no
usable images returns empty outputs and a `total_count` of 0.
