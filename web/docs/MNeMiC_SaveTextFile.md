# 💾 Save Text File With Path

Writes text to a file under ComfyUI's `output` folder, with a templated folder
name, filename and auto-incrementing counter.

## Inputs

- **file_text** — The text to write.
- **path** — Subfolder under `output`. Supports the tokens below.
- **prefix** — Start of the filename. Supports the tokens below.
- **counter_separator** — What sits between the name parts and the counter.
- **counter_length** — Digits in the counter, e.g. `3` gives `001`. `0` turns
  the counter off entirely.
- **suffix** — Added after the counter.
- **output_extension** — Extension without the dot, e.g. `txt`.

## Outputs

- **output_full_path** — Full path of the file that was written.
- **output_name** — Filename without its extension.
- **output_path** — The resolved folder, without the filename.

## Tokens

Both `path` and `prefix` accept:

```
[time(<format>)]   Current date/time, using strftime directives
[hostname]         This machine's hostname
```

```
[time(%Y-%m-%d)]                ->  2025-08-14
[time(%Y-%m-%d - %H.%M.%S)]     ->  2025-08-14 - 17.42.09
```

## Filename layout

```
{prefix}{separator}{counter}{separator}{suffix}.{extension}
```

The counter looks at existing files that match the same pattern and takes the
next free number, so nothing is overwritten.

## Notes

Paths are resolved inside `output` and `..` is rejected, so the node cannot
write outside it. Characters Windows forbids in filenames are stripped from
`prefix` and `suffix` (Unicode is kept), and very long names are truncated to
stay inside the OS path limit. Missing folders are created.
