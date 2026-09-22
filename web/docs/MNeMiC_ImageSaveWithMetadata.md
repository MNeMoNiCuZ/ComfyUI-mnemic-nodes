# 💾 Save Image With Metadata

Saves images with Civitai-compatible metadata written into the file, so an
upload there shows the model, LoRAs, sampler, steps, seed and prompts.

Only **images** needs connecting: everything else is read out of the workflow
graph automatically.

## Inputs

- **images** — The images to save. A batch becomes separate numbered files.
- **filename_prefix** — Start of the filename. Tokens below.
- **folder** — Subfolder under ComfyUI's `output`. Tokens below.
- **file_format** — `png`, `jpeg` or `webp`.
- **positive_override** *(optional)* — Use this instead of the auto-detected
  positive prompt. Accepts one string for every image, or a list of prompts
  applied one per image (looping if the counts differ).

Advanced:

- **quality** — Compression quality for jpeg and webp, 1-100. Ignored for PNG.
- **embed_workflow** — Write the workflow into the file so it can be dragged
  back into ComfyUI. Turn off for smaller files or when sharing.
- **strip_lora_prompt** — Remove `<lora:...>` tags from the recorded prompt.

## Tokens

Both `filename_prefix` and `folder` accept:

```
%date:yyyy-MM-dd - hh.mm.ss%   Date/time, Civitai-style pattern
%Y %m %d %H %M %S %f           strftime directives
%A %a %B %b %j %W %w %U %u     weekday / month / week directives
%p %x %X %c                    AM-PM, date, time, date+time
%%                             a literal percent sign
%seed                          the resolved generation seed
%model                         the resolved model basename
```

## How it works

The node walks the prompt graph to find the checkpoint, LoRAs, sampler,
scheduler, steps, cfg, seed and size, then follows text links backwards to
recover the real prompt — through String Concat, Wildcard Processor, LoRA Tag
Loader and Prompt Property Extractor nodes, so what gets recorded is the
resolved text, not the template. Per-image prompts published by
🔀 Batch Wildcard Upscale Sampler are picked up automatically when that node is
in the graph.

## Notes

Detection depends on reading the graph, so unusual sampler setups can come out
with gaps. If the metadata is wrong, `positive_override` is the escape hatch.
This node installs a runtime hook into ComfyUI's executor at load time in order
to see the live prompt.
