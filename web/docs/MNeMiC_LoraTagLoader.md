# 🏷️ LoRA Loader Prompt Tags

Reads `<lora:name:strength>` tags out of a prompt, applies those LoRAs to the
model and CLIP, and hands back the prompt with the tags removed. One node
replaces a chain of LoRA Loaders, and which LoRAs load can come from the prompt
text itself — including from a wildcard.

Based on [comfyui_lora_tag_loader](https://github.com/badjeff/comfyui_lora_tag_loader)
by badjeff, with a different file-matching system.

## Inputs

- **MODEL** — The checkpoint to patch.
- **CLIP** — The CLIP to patch.
- **STRING** — Prompt text containing the tags.

## Outputs

- **MODEL** / **CLIP** — With every matched LoRA applied.
- **STRING** — The prompt with all `<...>` tags stripped, ready for encoding.

## Tag syntax

```
<lora:name>              strength 1.0 for both model and CLIP
<lora:name:0.8>          strength 0.8 for both
<lora:name:0.8:0.5>      model 0.8, CLIP 0.5
```

The name does not have to be the full filename — it is matched against your
LoRA files, preferring subfolder-aware substring hits and falling back to fuzzy
word matching. A strength of `0` is read as 1.0 rather than "off".

## Notes

Tags that match no file are skipped with a console note rather than failing the
run. The most recently used LoRA is kept in memory, so repeated runs with the
same one do not re-read it from disk. Lumina2 / ZiT models get an extra key
mapping applied automatically.

Console logging, fuzzy search and the candidate-log cap are in
**Settings → ⚡MNeMiC Nodes → LoRA Loading**.
