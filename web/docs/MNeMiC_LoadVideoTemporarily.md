# 🎞️ Load Video Temporarily

Same idea as ComfyUI's Load Video, except uploads land in the `temp` folder instead of `input`. Useful for one-off videos you do not want accumulating in your input directory. Temp is cleared when ComfyUI restarts.

## Inputs

- **video**: File to load from `temp`. New node instances start blank rather than pre-selecting whichever temp video happens to exist.

## Outputs

- **video**: The loaded video, with its audio. Connect it to Save Video, Get Video Components or any other node that takes a video.

## Notes

The node re-runs when the file's modification time changes, so a replaced file is picked up without hashing the whole video. When a saved workflow is opened after a restart and its temp video is gone, the selection is cleared instead of reporting a missing file.
