# 💾 Save Text File With Path

Saves text under ComfyUI's output folder, with automatic extensions and a choice of existing-file handling.

## Inputs

- **file_text**: Text to save.
- **path**: Folder under `output`. Empty uses `output` itself.
- **filename**: Name with or without an extension.
- **extension**: Optional override, such as `txt` or `.md`. Empty uses the filename's extension, or `txt` if none.
- **if file exists**: Defaults to **overwrite**, without numbering.

| If file exists | Behavior |
| --- | --- |
| overwrite | Replace the existing file. |
| ignore | Keep the existing file and return its path. |
| increment filename | Save to the next available numbered name. |

Only **increment filename** shows:

- **separator**: Underscore, hyphen, space or none; defaults to underscore.
- **number format**: `1`, `01`, `001` or `0001`; defaults to `1`.

Advanced: **suffix** adds optional text before the extension.

## Outputs

- **output_full_path**: Full file path, including the extension.
- **output_name**: Filename without its extension.
- **output_path**: Containing folder.

## Examples

| Filename | Setting | Result |
| --- | --- | --- |
| `notes.md` | Empty extension | `notes.md` |
| `notes.md` | Extension `txt` | `notes.txt` |
| `notes.md` already exists | Increment filename | `notes_1.md` |
| `notes_009.md` already exists | Increment filename | `notes_010.md` |

## Notes

- Incrementing keeps the exact filename when it is available. Existing trailing numbers keep their separator and at least their current padding.
- Path, filename and suffix support `[time(%Y-%m-%d)]` and `[hostname]`.
- Missing folders are created. Paths must stay under ComfyUI's output folder.
- Invalid filename characters are removed; Unicode is preserved.
