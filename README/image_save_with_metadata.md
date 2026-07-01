# 💾 Save Image With Metadata

Save images with Civitai-compatible metadata auto-detected from your workflow.

<img width="1190" height="447" alt="image" src="https://github.com/user-attachments/assets/097ed56c-3ef9-495b-b9af-e39a2ca18125" />

This node is integrated into this pack as an adapted copy of ChronoKnight's original node.
Original source:
- https://github.com/KChronoKnight/Chrono-Save-for-Civitai

## Inputs
- `images`: Image batch to save.
- `filename_prefix`: Supports `strftime`, `%date:yyyy-MM-dd - hh.mm.ss%`, plus `%seed` and `%model`.
- `folder`: Output subfolder under ComfyUI output dir, supports `strftime` and `%date:...%`.
- `file_format`: `png`, `jpeg`, or `webp`.
- `quality`: JPEG/WebP quality.
- `embed_workflow`: Embed workflow metadata into saved image.
- `strip_lora_prompt`: Removes `<lora:...>` and embedding tags from prompt text in metadata output.
- `positive_override` (optional): Override positive prompt text.

## Behavior
- Captures prompt/negative prompt and LoRAs from executed runtime graph paths (sampler upstream), with graph parsing fallback.
- Writes A1111-style `parameters` metadata.
- `Models used` captures base model + LoRA
