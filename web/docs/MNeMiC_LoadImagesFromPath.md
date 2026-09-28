# 📂 Load Images From Path

Loads an image or steps through a folder, with a mask and separate path or filename outputs.

The image preview updates automatically when the path, seed, or subfolder toggle changes.
It shows the image for the current widget values without running the workflow.
The preview is hidden when those inputs are connected to other nodes.

## Inputs

- **include_subfolders**: Include images from all subfolders. Defaults to off.
- **seed**: Image index, starting at 0 and wrapping at the file count. Defaults to increment.
- **input_path**: Folder or image file. Relative paths start at ComfyUI's input folder; empty is an error.
- **output1**, **output2**, ...: Format of each text output. The first defaults to **path/file.ext**; hover over options in the open dropdown for descriptions and examples.
- **Add file/path output**: Add a text output and choose its format, up to 32 outputs.
- **Remove last file/path output**: Remove the last additional output and its connections.

For `C:\image.png`, with `C:\` as the input folder:

| Format | Output |
| --- | --- |
| path | `C:\` |
| path/ | `C:\` |
| file | `image` |
| file.ext | `image.png` |
| path/file | `C:\image` |
| path/file.ext | `C:\image.png` |
| relative_path | `.` |
| relative_path/ | `.\` |
| relative_path/file | `image` |
| relative_path/file.ext | `image.png` |

## Outputs

- **image**: Selected image.
- **mask**: Alpha channel, or black if absent.
- **current_index**: Image index used.
- **total_count**: Number of images found.
- **output1**, **output2**, ...: Separate strings below the counters, each with its own selected format.

## Examples

Choose **path/** for **output1** and **file.ext**
for **output2** to connect the folder and filename separately.

## Notes

- Supports PNG, JPG, JPEG, WEBP, BMP and GIF. Folders are read in filename order. With **include_subfolders** enabled, images from all subfolders are included in path order.
- No usable images returns empty outputs and a count of 0.
- Paths use your system's separators. Relative paths may contain `..`; relative folder output is `.` for the input folder itself.
- Labels use `/`; output paths use `\` on Windows and `/` elsewhere. Drive roots keep their required slash. File paths never end in a slash.
- On Windows, relative formats require the image and input folder to share a drive.
- Extensionless formats remove only the final image extension. Dots within the filename are preserved.
