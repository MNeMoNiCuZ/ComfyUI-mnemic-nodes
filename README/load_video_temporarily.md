# Load Video Temporarily

Loads a video and stores it in ComfyUI /temp-folder instead of the /input folder. This folder is cleared upon comfy restart, so no video is saved permanently.

## What It Does

- Loads an uploaded temp video as `VIDEO`, with its audio.
- Works with Save Video, Get Video Components and other video nodes.
- Uses temp storage instead of `/input` persistence.

## Inputs

- `video`
  - Upload/select a video from ComfyUI temp files.

## Outputs

- `video`: the loaded video.
