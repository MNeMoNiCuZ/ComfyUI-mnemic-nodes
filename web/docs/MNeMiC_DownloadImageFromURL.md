# 🖼️ Download Image from URL

Fetches an image over HTTP and brings it into the workflow. Keeps a copy in
ComfyUI's temp folder, or in input/output when saving is enabled.

## Inputs

- **image_url** — Direct link to the image. The URL path must end in `.jpg`,
  `.jpeg`, `.png` or `.webp`. Only public `http`/`https` addresses are allowed;
  localhost and private network addresses are refused. System proxy settings
  are not used.
- **save** — Keep a copy in input or output. Off by default. When off, writes
  a uniquely named PNG directly in ComfyUI's temp folder; the save settings are
  hidden and ignored. The image is passed downstream in either mode. Temp is
  automatic and is not a dropdown option.

These settings appear when **save** is enabled:

- **name** — Filename prefix template. Defaults to
  `%date:yyyy-MM-dd - hh.mm.ss%`, matching Save Image With Metadata. Leave empty
  to use the name from the URL. Accepts date tokens below. This must be a single
  filename: path separators and special path syntax are rejected. The chosen
  format supplies the extension, replacing an existing image extension.
- **path** — Folder prefix template inside the save location. Defaults to
  `%date:yyyy-MM-dd%`, matching Save Image With Metadata. Empty saves
  directly in the selected input/output folder. Accepts date tokens below.
  Only additive subfolders such as `downloads/portraits` are allowed. Absolute
  paths, drive/UNC paths, `.` / `..` components, empty components, trailing dots
  or spaces, reserved Windows names and alternate data streams are rejected.
  Symlinks, junctions and other reparse points beneath the chosen root are
  rejected, even if they currently point inside the root.
- **save_location** — `input` (default) or `output`.
- **overwrite** — Replace an existing file with the same name. Off by default:
  the existing file is kept and the image is still passed downstream.
- **file_format** — `png`, `jpeg` or `webp`, matching Save Image With Metadata.

Advanced, when saving JPEG or WebP:

- **quality** — Compression quality, 1–100 (default 100). Ignored for PNG.

## Outputs

- **image** — The downloaded image.
- **width** / **height** — Its size in pixels.

## How it works

Saving always uses the selected input/output folder, even when **path** is empty.
Missing subfolders are created. The selected format controls both the encoding
and extension: PNG uses `.png`, JPEG `.jpg`, and WebP `.webp`.

Paths are checked before and after date expansion, and again after folders are
created. Traversal is rejected rather than normalized. Overwrite replaces the
file's directory entry so an existing hardlink cannot corrupt a file outside
the chosen folder. Temporary copies use exclusive random filenames and always
use PNG, independently of the hidden save settings.

Both **name** and **path** use the same date formatter as Save Image With
Metadata, with the same default filename and folder prefixes. For example,
saving a PNG at 14:05:06 on 2026-10-12 writes
`input/2026-10-12/2026-10-12 - 14.05.06.png` with the default save settings.
All three text inputs also have placeholders when cleared; placeholders are
hints and do not replace an empty value. Date templates use the local time:

```text
%date:yyyy-MM-dd - hh.mm.ss%   Custom date/time pattern (hh is 24-hour time)
%Y %m %d %H %M %S %f           Year, month, day, hour, minute, second, microsecond
%A %a %B %b %j %W %w %U %u     Weekday, month and week directives
%p %x %X %c                    AM/PM, date, time, date+time
%%                             A literal percent sign
```

Use either custom `%date:...%` patterns or ordinary strftime directives in a
field. `%x` defaults to `yyyy-MM-dd`; time tokens use dots instead of colons
where needed for filenames. This node does not resolve `%seed` or `%model`.

## Examples

Save directly in ComfyUI's input folder:

```text
save: true
save_location: input
path: (empty)
name: (empty)
file_format: png
```

Save a dated WebP copy in output:

```text
save: true
save_location: output
path: downloads/%date:yyyy-MM-dd%
name: image_%date:yyyy-MM-dd - hh.mm.ss%
file_format: webp
quality: 95
```

## Notes

A failed download, unsupported URL extension or non-200 response returns empty
outputs and prints the reason to the console. A rejected save path or address
stops the queue with an error.

Older saved workflows loaded in the frontend retain their filename, path and
save settings; saving is enabled if their old path was nonempty. Legacy API
prompts without a save flag default to saving off. New API prompts use `save`,
`name` and `path` instead of `save_file_name_override` and `save_path`.
