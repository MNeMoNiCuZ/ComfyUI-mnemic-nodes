# 🖼️ Load Image Advanced

Loads an image from the `input` folder and also gives you its path, its size,
and the positive prompt stored in its metadata.

## Inputs

- **image** — The file to load.

## Outputs

- **image** — The loaded image.
- **mask** — The alpha channel, or fully black if the file has none.
- **image_path** — Full path of the file.
- **positive_prompt** — Positive prompt read from the image metadata. Empty
  when the file has no readable prompt.
- **width** / **height** — Size in pixels.

## Notes

Prompt extraction understands ComfyUI and A1111-style metadata. For the full
metadata set (negative prompt, sampler, steps, seed) use
🖼️📊 Metadata Extractor (Single).
