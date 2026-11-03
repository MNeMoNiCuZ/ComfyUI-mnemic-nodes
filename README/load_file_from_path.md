# 📂 Load File From Path

Loads a file and the files that share its name, picked by seed, such as an image and its caption. Each file output has an extension and a type, so one node can give an image, its text, a mask, audio, a video or a path. All outputs use the same seed, so they always come from the same file name.

## Inputs

- **include_subfolders**: Include files from all subfolders. Defaults to off.
- **seed**: Index of the file name to load, starting at 0 and wrapping at the count. Defaults to increment.
- **input_path**: Folder to load from. A single file loads that file and its matching files. Relative paths start at ComfyUI's input folder; empty is an error.
- **extension 1**, **extension 2**, ...: The extension of each output's file, e.g. `png`. List several, like `png, jpg, webp`, to use whichever one exists (first listed wins). The label shows how many files the extension finds, e.g. `extension 1 (200)`, marked 🟡 when the outputs' counts differ and 🔴 when one finds none. Hover it for all counts.
- **type 1**, **type 2**, ...: What each output loads the file as. The output slot takes that type.
- **Add file output** / **Remove last file output**: Add up to 16 file outputs, or remove the last one and its connections.

| Type | Output | Loads |
| --- | --- | --- |
| image | IMAGE | The image. Animated files give their first frame. |
| mask | MASK | The image's alpha channel, or fully black if it has none. |
| text | STRING | The file's text, read as UTF-8. |
| audio | AUDIO | The audio, for any format ComfyUI can decode. |
| video | VIDEO | The video, for any format ComfyUI can decode. |
| path | STRING | The file's full path, for formats no other type loads. |

## Outputs

- **name**: The shared file name, without folder or extension.
- **current_index**: Index actually loaded: the seed wrapped around the count.
- **total_count**: How many files the first output found. The seed wraps at this count.
- **output1**, **output2**, ...: One per file output, labelled with its type and extension, e.g. `image (png)`.

## How it works

The first output decides which files are loaded: the seed picks one of its files, sorted by path, and each other output loads the file with the same folder and name and its own extension. A missing file gives a warning and a stand-in instead of an error: empty text or path, a black image or mask the size of the loaded image, one sample of silence, or nothing for video.

## Example

For a dataset with `cat_01.png` + `cat_01.txt` and `cat_02.jpg` + `cat_02.txt`, set output 1 to `png, jpg` as **image** and output 2 to `txt` as **text**. Seed 1 gives `cat_02.jpg`, the text of `cat_02.txt`, and the name `cat_02`.
