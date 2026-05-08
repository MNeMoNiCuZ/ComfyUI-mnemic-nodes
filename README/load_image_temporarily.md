# Load Image Temporarily

`Load Image Temporarily` loads images from ComfyUI's temp upload area and decodes them using core `LoadImage`-style behavior.

<img width="1477" height="494" alt="image" src="https://github.com/user-attachments/assets/5c0aa05c-6c6d-48df-a6a9-12356cc4ea4f" />

## What It Does

- Loads an uploaded temp image as `IMAGE`.
- Produces an inverted alpha `MASK` (same pattern as ComfyUI `LoadImage`).
- Outputs `width` and `height`.
- Uses temp storage instead of `/input` persistence.

## Inputs

- `image`
  - Upload/select an image from ComfyUI temp images.
  - New node instances are clear by default (empty selection), so no previous temp image is preloaded.

## Outputs

- `image`: decoded image tensor.
- `mask`: alpha mask (inverted).
- `width`: image width.
- `height`: image height.

## Notes

- Multi-frame images are supported; frames with mismatched size are skipped.
- If no alpha/transparency is present, a default empty mask is returned.
