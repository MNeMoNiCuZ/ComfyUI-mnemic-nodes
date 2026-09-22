# 🖼️ Load Image Temporarily

Same idea as ComfyUI's Load Image, except uploads land in the `temp` folder
instead of `input`. Useful for one-off reference images you do not want
accumulating in your input directory — temp is cleared when ComfyUI restarts.

## Inputs

- **image** — File to load from `temp`. New node instances start blank rather
  than pre-selecting whichever temp file happens to exist.

## Outputs

- **image** — The loaded image. Multi-frame files come out as a batch.
- **mask** — Alpha channel, inverted to match ComfyUI's Load Image.
- **width** / **height** — Size in pixels.

## Notes

The node fingerprints the file's contents, so editing the file re-runs the
workflow but re-queueing an unchanged file does not. Frames whose size differs
from the first frame are skipped.
