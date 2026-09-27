# 📂 Load Images From Path

Loads an image or steps through a folder, with a mask and separate path or filename outputs.

## Inputs

- **seed**: Image index, starting at 0 and wrapping at the file count. Defaults to increment.
- **input_path**: Folder or image file. Relative paths start at ComfyUI's input folder; empty is an error.
- **output1**, **output2**, ...: Format of each text output. The first defaults to **full path with ext**; hover for the selected format's tooltip.
- **Add file/path output**: Add a text output and choose its format, up to 32 outputs.
- **Remove last file/path output**: Remove the last additional output and its connections.

For `C:/ComfyUI/input/portraits/photo.v2.png`, with `C:/ComfyUI/input` as the input folder:

| Format | Output |
| --- | --- |
| full path with ext | `C:/ComfyUI/input/portraits/photo.v2.png` |
| full path without ext | `C:/ComfyUI/input/portraits/photo.v2` |
| folder path without trailing / | `C:/ComfyUI/input/portraits` |
| folder path with trailing / | `C:/ComfyUI/input/portraits/` |
| filename with ext | `photo.v2.png` |
| filename without ext | `photo.v2` |
| relative path with ext | `portraits/photo.v2.png` |
| relative path without ext | `portraits/photo.v2` |
| relative folder without trailing / | `portraits` |
| relative folder with trailing / | `portraits/` |

## Outputs

- **image**: Selected image.
- **mask**: Alpha channel, or black if absent.
- **current_index**: Image index used.
- **total_count**: Number of images found.
- **output1**, **output2**, ...: Separate strings below the counters, each with its own selected format.

## Examples

Choose **folder path with trailing /** for **output1** and **filename with ext**
for **output2** to connect the folder and filename separately.

## Notes

- Supports PNG, JPG, JPEG, WEBP, BMP and GIF. Folders are read in filename order, without subfolders.
- No usable images returns empty outputs and a count of 0.
- Paths use your system's separators. Relative paths may contain `..`; relative folder output is `.` for the input folder itself.
- Labels and paths use `\` on Windows and `/` elsewhere. Drive roots keep their required slash. File paths never end in a slash.
- On Windows, relative formats require the image and input folder to share a drive.
