# 📁 Get File Path

Picks a file from ComfyUI's `input` folder and splits its path into parts, so
other nodes can use the folder, the bare name or the extension separately.

## Inputs

- **image** — The file to use. The upload button accepts any file type, not
  just images — switch the file-type filter to "all files" in the browser
  dialog when picking a non-image.

## Outputs

- **full_file_path** — The complete path.
- **file_path_only** — The containing folder.
- **file_name_only** — The name without its extension.
- **file_extension_only** — The extension, including the dot.

## Notes

If the file cannot be found, all four outputs are empty and the reason is
printed to the console.
