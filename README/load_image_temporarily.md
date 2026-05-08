# Load Image Temporarily

Loads an image and stores it in ComfyUI /temp-folder instead of the /input folder.
This folder is cleared upon comfy restart, so no image is saved permanently.

<img width="1477" height="494" alt="image" src="https://github.com/user-attachments/assets/5c0aa05c-6c6d-48df-a6a9-12356cc4ea4f" />

## What It Does

- Loads an uploaded temp image as `IMAGE`.
- Produces an inverted alpha `MASK` (same pattern as ComfyUI `LoadImage`).
- Outputs `width` and `height`.
- Uses temp storage instead of `/input` persistence.

## Inputs

- `image`
  - Upload/select an image from ComfyUI temp images.

## Outputs

- `image`: decoded image tensor.
- `mask`: alpha mask (inverted).
- `width`: image width.
- `height`: image height.
