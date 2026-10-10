# 🔀 Batch Wildcard Upscale Sampler

Generates several images in one node, resolving the wildcards fresh for each
one, so a single queue gives you a different prompt per image. Optionally runs
a second high-resolution pass per image.

This is a true sampler batch: every image gets its own encoded prompt, and the
whole batch is sampled in one go. VRAM use grows with `batch_size`.

## Inputs

- **text** — Positive prompt. Full wildcard syntax (see 📝 Wildcard Processor)
  plus `<lora:name:strength>` tags.
- **negative** — Negative prompt. Same wildcard syntax; resolved per image too.
- **seed** — Base seed. Image *n* uses `seed + n`, for both wildcard resolution
  and sampling noise.
- **batch_size** — How many images to generate.
- **width** / **height** — Size of each image, in pixels.
- **steps**, **cfg**, **sampler_name**, **scheduler**, **denoise** — First-pass
  sampling settings.
- **upscale** — Turn on the second pass. Its settings are under **Show advanced
  inputs**.
- **model** / **clip** *(optional)* — Needed to sample. Leave them off to just
  resolve and preview prompts.
- **vae** *(optional)* — Required for the upscale pass, which decodes to pixels,
  upscales, and re-encodes.
- **upscale_model** *(optional)* — An ESRGAN-style model for the upscale step
  instead of plain Lanczos.

Advanced (upscale pass):

- **upscale_rate** — How much bigger the second pass runs. With an upscale
  model connected, the model runs first and the result is then resized to
  exactly this factor, so a 4x model at rate 2.0 still gives a clean 2x.
- **upscale_denoise** — Low keeps the first-pass composition, high adds detail
  but drifts.
- **upscale_steps**, **upscale_cfg** — Second-pass sampling. `upscale_cfg` of 0
  reuses the first-pass cfg.
- **upscale_sampler_name**, **upscale_scheduler** — `(same as first pass)`
  reuses the first-pass choice.
- **upscale_noise_inject_strength** — Adds Gaussian noise to the upscaled latent
  before refining. The amount follows the upscale scheduler's sigma curve, so
  karras injects more at a low setting than a linear schedule does. Helps break
  up VAE re-encode artifacts.
- **strip_prompt_weights** — Removes `(word:1.3)` emphasis syntax before
  encoding. Turn this on for T5-based encoders (FLUX, SD3 and similar), which
  read the parentheses and colons as literal characters.
- **recache_wildcards** — Re-scan the wildcard folders from disk.

## Outputs

- **model** — Model with shared and per-image LoRAs. Reuse with the same latent batch size and order.
- **clip** — CLIP with shared leading LoRA tags. Per-image CLIP changes are baked into the conditionings.
- **vae** — Passed through, so the upscale chain downstream has it.
- **positive** / **negative** — Batched conditioning with one entry per image,
  in the same order as the latent batch.
- **latent** — All sampled latents combined into one batch.
- **prompt** — The resolved positive prompt for each image, as a list.

## How it works

Resolve wildcards for every image → encode each image's prompts → stack them
into one conditioning batch → sample the whole batch → optionally upscale the
batch and sample it again. Image *n* starts from the same noise it would get if
sampled alone with `seed + n`. Ancestral and SDE samplers add their own noise
during sampling, so their results can differ slightly from sampling each image
alone.

Prompts that encode to different lengths are padded to the longest one in the
batch.

Different LoRAs and model weights can be used for each image **inside the same sampler call**. The identical leading LoRA tags are loaded normally. Remaining LoRAs are applied as additive layer outputs with a separate strength for each image; a missing LoRA has strength zero. Each image's positive and negative prompts are encoded using its own CLIP LoRA weights before sampling.

Per-image adapters support ordinary LoRA, LoHa, LoKr, and linear/convolution weight or bias diffs, including sampling-step ranges. Differing DoRA, OFT, normalization patches, shape-changing patches, and video time/blend tags raise an error. Put such tags first, identically in every prompt, to use the regular shared loader. Existing bypass-patched models cannot receive another set of per-image adapters; use the base model as input. LoRA tags load from the positive prompt only.

The returned model must be reused with the original latent batch size and image order. The returned CLIP contains only the shared leading tags; per-image CLIP changes are already baked into the conditioning outputs. Adapter computation and memory grow with the number of different LoRAs as well as batch size. No automatic sequential fallback is used.

If nothing is connected to the `latent` output, sampling is skipped and the node
only resolves prompts — a cheap way to preview what the wildcards will produce.

The resolved per-image prompts are published for **💾 Save Image With Metadata**,
so saved files get the prompt that actually made them rather than the template.

## Notes

**Settings → ⚡MNeMiC Nodes → Wildcard Processing → Show hover tooltips**
controls hover tooltips for this node (including both prompt inputs) and both
Wildcard Processor variants. It defaults to off. Click **?** to read the help
page regardless of this setting.

The optional upscale noise callback adds noise at each denoising step.
It is the most involved node in the pack; if a workflow behaves oddly, try it
with `upscale` off first.

### Batching limitations

Anima keeps each image's T5 token IDs and token weights with its original Qwen embeddings. Its model-side text adapter processes each prompt after the model loads, then the resulting conditionings are stacked for one batched denoising pass. Use this node's returned **model** together with its **positive** and **negative** outputs downstream; that model carries the Anima preprocessing support. Per-image LoRA strengths also apply during text preprocessing when those LoRAs patch the text adapter. Step-scheduled patches apply during denoising, not this earlier preprocessing.

Prompt embeddings with different lengths are padded (or repeated for compatible CLIP lengths). Padding can change results on models that ignore attention masks. Initial noise uses each image's seed; ancestral/SDE sampling uses the batch's first seed for later noise, so results need not match separate runs. Auxiliary Llama/byT5 conditionings are also stacked. Unsupported differing metadata raises an error rather than reusing another image's conditioning.

Per-image adapter routing assumes layers retain the image batch dimension or flatten contiguous tokens per image. Custom models that reorder or split rows need dedicated support. This implementation requires ComfyUI's current weight-adapter bypass APIs. Runtime compatibility and image quality still need verification in ComfyUI.
