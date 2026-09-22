# 🖼️📊 Metadata Extractor (List)

The list version of 🖼️📊 Metadata Extractor (Single): reads metadata from a
whole folder and returns parallel lists, rotated so the seed picks the starting
point.

## Inputs

- **seed** — Where the list starts. Set its control to **increment** to rotate
  through the folder.
- **input_path** *(optional)* — A folder of images, or a single file.
  Relative paths resolve inside ComfyUI's `input` folder.
- **image_input** *(optional)* — A batch already in the workflow. Takes
  priority over `input_path`.
- **filter_params** *(advanced)* — Comma-separated keys to pull out, e.g.
  `steps, sampler, seed`.
- **max_file_count** *(advanced)* — Cap on how many items to return. `0`
  returns everything found.

## Outputs

All outputs are lists in the same order, one entry per image:

- **image** — The images, as one batch.
- **positive_prompt** / **negative_prompt**
- **parsed_params_json** — Recognised settings per image, as indented JSON.
- **filtered_params_grouped** — Only the keys from `filter_params`, one value
  per line, per image.
- **raw_metadata_json** — The unparsed metadata block per image.

## Notes

Files are sorted by name before rotating, so the order is stable. Images whose
dimensions differ from the first one are resized and centre-cropped to match,
because a batch has to be uniform — a console warning says when this happens.
Files that fail to load are skipped rather than aborting the run.
