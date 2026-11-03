# 📂 Load File From Path

Loads a file and the files that share its name, picked by seed, such as an
image and its caption. Each file output has an extension and a type, so one node can
give an image, its text, a mask, audio, a video or a path. All outputs use the
same seed, so they always come from the same file name.

## Inputs

- **include_subfolders**: Include files from all subfolders. Defaults to off.
- **seed**: Index of the file name to load, starting at 0 and wrapping at the
  count. Defaults to increment.
- **input_path**: Folder to load from. A single file loads that file and its
  matching files. Relative paths start at ComfyUI's input folder; empty is an
  error.
- **extension 1**, **extension 2**, ...: The extension of each output's file,
  e.g. `png`. List several, like `png, jpg, webp`, to use whichever one exists
  (first listed wins). The label shows the file count; see below.
- **type 1**, **type 2**, ...: What each output loads the file as. The output
  slot takes that type.
- **Add file output**: Add another file output, up to 16.
- **Remove last file output**: Remove the last file output and its
  connections. At least one stays.

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
- **total_count**: How many files the first output found. The seed wraps at
  this count.
- **output1**, **output2**, ...: One per file output, labelled with its type
  and extension, e.g. `image (png)`.

## How it works

The first output decides which files are loaded: the node lists every file
with its extension, sorted by path, and the seed picks one. Each other output
loads the file with the same folder and name and its own extension.

When one of those files is missing, the node logs a warning and that output
gets a stand-in, so nodes downstream keep running:

| Type | Missing file gives |
| --- | --- |
| image | A black image the size of a loaded image or mask, else 64x64. |
| mask | A black mask, sized the same way. |
| text, path | An empty string. |
| audio | Silence, one sample long. |
| video | Nothing. |

With no files for the first output at all, every output gets a stand-in and
the name is empty.

The label of each extension shows how many files it finds at the path, e.g.
`extension 1 (200)`. The label is marked 🟡 when the outputs' counts differ (some
files have no match) and 🔴 when an output finds no files, e.g.
`extension 2 (0) 🔴`. On the classic canvas the label text is also coloured. Hover it for every
count and how many files have a match for every output. The counts
update as you edit the path or extensions, and on every run. A connected path
shows no counts.

Changing an output's type disconnects that output, since its old links would
not accept the new type.

## Examples

A captioned dataset with `cat_01.png` + `cat_01.txt`, `cat_02.jpg` +
`cat_02.txt`:

| Output | Extension | Type |
| --- | --- | --- |
| output1 | `png, jpg` | image |
| output2 | `txt` | text |

Seed 1 gives the image `cat_02.jpg`, the text of `cat_02.txt`, and the name
`cat_02`.

Use `png` twice, as **image** and as **mask**, to get both from one file. Use
**path** for a file another node loads by path, such as a `.json` sidecar.

## Notes

- Put the file type every name has first, usually the image.
- Images are turned upright using their EXIF orientation.
- Files are read when the node runs; there is no image preview.
