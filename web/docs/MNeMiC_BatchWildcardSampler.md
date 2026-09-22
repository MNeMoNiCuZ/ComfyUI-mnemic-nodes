# 🔀 Batch Wildcard Upscale Sampler

Generates several images in one node, resolving the wildcards fresh for each
one, so a single queue gives you a different prompt per image. Optionally runs
a second high-resolution pass per image.

This is **not** a true sampler batch: images are processed one at a time inside
the node, then combined into a batch-shaped latent for whatever comes next.

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

- **model** / **clip** — After the LoRA patches from the *last* image.
- **vae** — Passed through, so the upscale chain downstream has it.
- **positive** / **negative** — Conditioning from the last image's prompt.
- **latent** — All sampled latents combined into one batch.
- **prompt** — The resolved positive prompt for each image, as a list.

## How it works

Per image: resolve wildcards → apply any `<lora:...>` tags to fresh clones of
the model and clip → encode both prompts → sample → optionally upscale and
sample again. LoRA tags only apply from the positive prompt; tags in the
negative prompt are stripped so they never reach the text encoder.

If nothing is connected to the `latent` output, sampling is skipped and the node
only resolves prompts — a cheap way to preview what the wildcards will produce.

The resolved per-image prompts are published for **💾 Save Image With Metadata**,
so saved files get the prompt that actually made them rather than the template.

## Notes

This node patches the sampler at runtime to inject noise for the upscale pass.
It is the most involved node in the pack; if a workflow behaves oddly, try it
with `upscale` off first.
