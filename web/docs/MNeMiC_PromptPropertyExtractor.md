# ⚙️ Prompt Property Extractor

Reads generation settings out of the prompt itself. Write `<cfg:7.5>` or
`<checkpoint:myModel>` in the text and this node pulls them out, loads what
needs loading, and exposes everything as outputs — so one text field can drive
a whole workflow.

Wildcards in the text are resolved first, so a wildcard file can supply the
settings too.

## Inputs

- **input_string** — Prompt text with property tags. Every widget below is a
  *default* that a tag can override.
- **load_clip_from_checkpoint** / **load_vae_from_checkpoint** — Whether a
  `<checkpoint:...>` tag also supplies CLIP / VAE. Ignored when there is no
  checkpoint tag.
- **cfg**, **steps**, **sampler_name**, **denoise**, **width**, **height**,
  **seed**, **start_step**, **end_step** — Defaults for the matching tags.
- **model** / **clip** / **vae** *(optional)* — Used when no tag overrides them.

## Supported tags

```
<checkpoint:name>  <model:name>  <ckpt:name>
<clip:name>
<vae:name>
<lora:name:weight>
<cfg:value>
<steps:value>      <step:value>
<sampler:name>     <sampler_name:name>
<denoise:value>
<width:value>      <height:value>
<resolution:WxH>   <res:WxH>          e.g. <res:1024x768>
<seed:value>
<start_step:value> <start:value>      <start_at_step:value>
<end_step:value>   <end:value>        <end_at_step:value>
<pos:value>        <positive:value>
<neg:value>        <negative:value>
```

Multiple `<pos>` and `<neg>` tags are combined with `", "`. Use `\>` to put a
literal `>` inside a tag value, e.g. `<neg:(cat:1.5)\, ugly>`.

## Priority

For each setting: the tag wins, then the connected input, then the widget
default. Checkpoint names, LoRA names and samplers are matched loosely, so
`<checkpoint:realvis>` finds `SDXL/RealVisXL_V5.0.safetensors`.

## Outputs

- **MODEL** / **CLIP** / **VAE** — After the checkpoint and LoRA tags are
  applied.
- **positive** / **negative** — Conditioning, encoded from the cleaned text.
- **latent** — An empty latent at the resolved width and height.
- **seed**, **steps**, **cfg**, **sampler**, **denoise**, **start_step**,
  **end_step**, **width**, **height** — The resolved values, for wiring into a
  sampler.
- **positive** *(string)* — The text with all recognised tags removed.
- **negative** *(string)* — The text collected from the negative tags.
- **other_tags** — Anything tag-shaped the parser did not recognise, so typos
  are visible instead of silently dropped.
- **resolved_string** — Wildcards resolved but all tags still present.

## Notes

A `scheduler` tag and output are deliberately absent: ComfyUI validates
scheduler names when this module loads, which is before custom schedulers from
other packs have registered themselves.

## Examples

```
a portrait of a woman <checkpoint:realvis> <res:832x1216> <cfg:4.5> <steps:30>
<lora:add-detail:0.6> <neg:blurry, watermark>
```
