# 🖼️ Download Image from URL

Fetches an image over HTTP and brings it into the workflow, optionally saving a
copy to disk.

## Inputs

- **image_url** — Direct link to the image. The URL must end in `.jpg`,
  `.jpeg`, `.png` or `.webp`.
- **save_file_name_override** *(optional)* — Filename for the saved copy.
  Leave empty to use the name from the URL.
- **save_path** *(optional)* — Folder to save into. Leave empty to skip saving
  and only pass the image downstream.

## Outputs

- **image** — The downloaded image.
- **width** / **height** — Its size in pixels.

## Notes

Saved copies are always written as PNG. Missing folders are created. A failed
download, an unsupported extension or a non-200 response returns empty outputs
and prints the reason to the console rather than stopping the queue.
