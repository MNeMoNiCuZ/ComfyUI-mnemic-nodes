# 💾 Save Video (MNeMiC)

Saves a video to the output folder like ComfyUI's Save Video, with the same formats and codecs. The file name accepts date codes, and the final prompt text can be stored in the file, so metadata viewers show the prompt that was actually used even when it was made at run time by a wildcard processor or an LLM node.

## Inputs

- **video**: The video to save, for example from Create Video.
- **filename_prefix**: Path and name inside the output folder. A `/` makes subfolders. Default `%Y-%m-%d/%Y-%m-%d - %H.%M.%S`: one folder per day, one file per second. The default for new nodes is set in Settings › ⚡MNeMiC Nodes › Save Video.
- **format**: Container and codec, the same choices as the native Save Video. Auto uses MOV for ProRes, WebM for AV1 and MP4 otherwise.
- **positive_prompt** (optional): The final positive prompt text.
- **negative_prompt** (optional): The final negative prompt text.

## Outputs

- **video**: The input video, unchanged.

## How it works

The file name accepts:

- strftime codes: `%Y` year, `%m` month, `%d` day, `%H` hour, `%M` minute, `%S` second, `%%` a literal %, and the rest of Python's codes.
- `%date:yyyy-MM-dd hh.mm.ss%` as in other save nodes.
- `%Node name.widget%` values from other nodes, and `%width%`, `%height%`, `%year%` and the other native variables.

The prompt graph and workflow are embedded exactly like the native Save Video, as `prompt` and `workflow` container tags holding JSON.

When a prompt input is connected, the file also gets a `final_prompt` tag holding a JSON object with `positive` and `negative` strings. Each key is present only when its input is connected. No tags are written when ComfyUI runs with `--disable-metadata`.

## Examples

```
filename_prefix: %Y-%m-%d/%Y-%m-%d - %H.%M.%S
file:            output/2026-11-23/2026-11-23 - 14.05.31_00001_.mp4
final_prompt:    {"positive": "a red fox in snow", "negative": "blurry"}
```

Read it back with `ffprobe -show_format -of json <file>`: the tags are under `format.tags`.
