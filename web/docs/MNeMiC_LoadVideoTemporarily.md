# 🎞️ Load Video Temporarily

Same idea as ComfyUI's Load Video, except uploads land in the `temp` folder instead of `input`. Useful for one-off videos you do not want accumulating in your input directory. Temp is cleared when ComfyUI restarts.

## Inputs

- **framerate**: Leave at 0 to use the source frame rate. A positive value drops or repeats frames while keeping the audio at its original speed.

- **video**: File to load from `temp`. New node instances start blank rather than pre-selecting whichever temp video happens to exist.

## Outputs

- **video**: The loaded video, with its audio. Connect it to Save Video, Get Video Components or any other node that takes a video.
- **images**: The video frames as an image batch, in playback order at the selected frame rate.
- **audio**: The original audio track when present.

## Notes

The node re-runs when the file's modification time changes, so a replaced file is picked up without hashing the whole video. When a saved workflow is opened after a restart and its temp video is gone, the selection is cleared instead of reporting a missing file.
