# 🖼️📊 Metadata Extractor (Single)

Reads the generation metadata out of one image: prompts, sampler settings, and
the raw block as it was stored.

## Inputs

- **seed** — Which file to take when `input_path` is a folder. Set its control
  to **increment** to walk through them.
- **input_path** *(optional)* — A single image file, or a folder of them.
  Relative paths resolve inside ComfyUI's `input` folder.
- **image_input** *(optional)* — An image already in the workflow. Takes
  priority over `input_path`, but carries no metadata of its own — connect a
  file path instead if you need the settings.
- **filter_params** *(advanced)* — Comma-separated keys to pull out, e.g.
  `steps, sampler, seed`.

## Outputs

- **image** — The image the metadata came from. A 64×64 black image when
  nothing could be loaded.
- **positive_prompt** / **negative_prompt** — As stored in the file.
- **parsed_params_json** — Every recognised setting, as indented JSON.
- **filtered_params_list** — Only the keys from `filter_params`, one value per
  line, in the order you asked for them.
- **raw_metadata_json** — The unparsed metadata block.

## Notes

Reads png, jpg, jpeg, tiff and tif. Files with no metadata return empty
strings and `{}` rather than failing. Keys absent from the file come back as
empty lines in `filtered_params_list`, so the line positions stay aligned with
your filter list.
