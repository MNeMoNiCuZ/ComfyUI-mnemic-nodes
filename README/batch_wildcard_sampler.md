# 🔀 Batch Wildcard Upscale Sampler

The Batch Wildcard Sampler generates multiple images where **every image resolves its own independent set of wildcards and LoRA loading**. A normal sampler applies a single prompt to the whole batch; this node instead resolves the prompt separately for each index, so a single run produces a different prompt — and therefore a different image — for each item.

It is an all-in-one node: it resolves the wildcards, loads any LoRAs referenced in the prompt, encodes each prompt, samples the images together as one batch, and optionally runs a batched upscale second pass. It can also be used purely as a prompt previewer with no model attached, to check what your wildcards resolve to.

Additionally this node has an Upscale pass that can be enabled, using pixel-space upscaling with lanczos, or using an upscale model. Like `Hires-fix` from A1111/Forge.

Huge thanks and credits to ChronoKnight for the initial version of this node!

- https://github.com/KChronoKnight
- https://civitai.com/user/ChronoKnight

<img width="2175" height="639" alt="image" src="https://github.com/user-attachments/assets/316a9bc4-16a7-4887-8fc7-ca06c6b149ae" />

## About Batching

This node does true sampler batching: the whole batch is denoised in one sampler call, with a different prompt for each image. VRAM use grows with `batch_size`, just like a normal KSampler batch.

**Anima and SDXL batching are confirmed working.** Each image can use its own set of LoRAs, model strengths, and CLIP strengths within the same batch. Shared LoRAs and per-image LoRAs can be combined, such as a common acceleration LoRA with a different style or style strength for each image.

Prompt encoding and Anima's model-side text preprocessing run per prompt. Denoising runs on the complete batch. The optional upscale pass also denoises the complete batch together.

## Explanation

ComfyUI gives conditioning entry *n* to latent *n* when the conditioning's batch size matches the latent batch. This node builds such a conditioning:

1. Resolve wildcards and LoRA tags for every image.
2. Encode each image's positive and negative prompts with its own CLIP patches.
3. Stack the conditionings and seed each image's initial noise independently.
4. Sample the entire batch once, applying per-image model LoRA strengths.
5. Optionally upscale and sample the entire batch again.

Different LoRAs and model weights can be used for each image **inside the same sampler call**. The identical leading LoRA tags are loaded normally. Remaining LoRAs are applied as additive layer outputs with a separate strength for each image; a missing LoRA has strength zero. Each image's positive and negative prompts are encoded using its own CLIP LoRA weights before sampling.

Per-image adapters support ordinary LoRA, LoHa, LoKr, and linear/convolution weight or bias diffs, including sampling-step ranges. Differing DoRA, OFT, normalization patches, shape-changing patches, and video time/blend tags raise an error. Put such tags first, identically in every prompt, to use the regular shared loader. Existing bypass-patched models cannot receive another set of per-image adapters; use the base model as input. LoRA tags load from the positive prompt only.

The returned model must be reused with the original latent batch size and image order. The returned CLIP contains only the shared leading tags; per-image CLIP changes are already baked into the conditioning outputs. Adapter computation and memory grow with the number of different LoRAs as well as batch size. No automatic sequential fallback is used.

The batching approach follows [CRT's File Batch Prompt Scheduler](https://github.com/PGCRT/CRT-Nodes/blob/main/py/File_Batch_Prompt_Scheduler.py) and [KSampler Batch](https://github.com/PGCRT/CRT-Nodes/blob/main/py/Ksampler_Batch.py): concatenate per-image conditioning and noise before one sampler call. Per-image model LoRAs extend that approach using ComfyUI's adapter bypass operations.

### Example

With `batch_size` = 4 and the prompt:

```
A photo of a {red|green|blue|gold} __animal__
```

a single run might produce four different images from these four resolved prompts:

- `A photo of a red fox`
- `A photo of a gold owl`
- `A photo of a blue cat`
- `A photo of a green heron`

---

## Wildcard Support

Wildcard resolution is handled by the exact same engine as the [Wildcard Processor](./wildcard_processor.md), so both the positive and negative prompt fields support the full syntax:

- **File Wildcards** — `__filename__` inserts a random line from `filename.txt` in one of the wildcard directories.
- **Glob Wildcards** — `__*color*__` (pool lines from all matching files) or `__folder/*__` (pick a random file in a folder).
- **Inline Choices** — `{red|green|blue}` chooses one option.
- **Weighted Choices** — `{5::black|green|red}` makes `black` 5× as likely.
- **Multiple Selections** — `{2$$a|b|c|d}` (fixed count) and `{1-3$$a|b|c|d}` (ranged count), with an optional inline custom separator: `{1-3$$, $$a|b|c|d}`.
- **Variables** — `${animal=!__animals__} ... ${animal}` to reuse a resolved value.
- **Nesting** — all of the above can be combined.

See the [Wildcard Processor documentation](./wildcard_processor.md) for full details, examples, and the list of supported wildcard directories.

---

## LoRA Loading

LoRAs can be loaded directly from the prompt using `<lora:name:strength>` tags — the same mechanism as the [LoRA Loader Prompt Tags](./lora_tag_loader.md) node — so no separate loader node is required. Because each image resolves its own prompt, **each image can load a different set of LoRAs** (for example by putting a LoRA tag inside a wildcard file or inline choice).

- **Syntax**: `<lora:name:strength>`
- **Description**: Loads and applies the best-matching LoRA file for `name` to that image's model and CLIP. The matching is fuzzy (the same scoring used elsewhere in the pack), so the name does not need to be exact.
- **Strength**: Optional, defaults to `1.0`. A second value sets a separate CLIP strength, e.g. `<lora:mylora:0.8:0.6>`.
- **Example**: `A portrait of a knight <lora:detail-enhancer:0.75>`

The LoRA tags are **kept** in the resolved prompt (so they can be recorded in metadata) and are automatically **stripped before the text is sent to CLIP**, so the tags themselves never pollute the conditioning.

### Different strengths per image

Use an inline choice for the strength:

```text
A colorful illustration <lora:AdventureTimeStyleAnima:{0.5|1|2|4}>
```

Each image independently selects a strength. Choices are random, so values may repeat across the batch.

### Different LoRAs per image

Put complete tags inside an inline choice, or store them in wildcard files:

```text
A portrait {<lora:style_a:0.8>|<lora:style_b:1.2>}
```

Each choice can also contain several tags to select a complete set of LoRAs. Use LoRAs compatible with the connected base model.

### Shared and per-image LoRAs together

```text
<lora:anima-turbo-lora-v0.2.safetensors:0.85>
A colorful illustration <lora:AdventureTimeStyleAnima:{0.5|1|2|4}>
```

Every image uses the turbo LoRA at `0.85` and independently selects its style strength. Identical leading tags are applied to the shared model; differing tags retain their own strengths for each image. A LoRA with no text-encoder weights affects only the diffusion model, even when the tag specifies a CLIP strength.

### Interaction with Save Image With Metadata

Because the resolved prompts retain their `<lora:...>` tags, the [Save Image With Metadata](./image_save_with_metadata.md) node decides how to handle them based on its own `strip_lora_prompt` toggle:

- `strip_lora_prompt` **on** → the `<lora:...>` tags are removed from the saved prompt text (the LoRA hashes are still recorded separately).
- `strip_lora_prompt` **off** → the `<lora:...>` tags are kept in the saved prompt text.

---

## Per-Image Resolution & Seeding

Every batch index is resolved and seeded independently:

- **Wildcards** are resolved with `seed + index`, so each image draws a different result while staying fully reproducible.
- **Noise** for each image is also generated with `seed + index`, so each image starts from the same noise it would get if sampled alone. Ancestral and SDE samplers add their own noise during sampling, so their results can differ slightly from sampling each image alone.

Because both use the same base `seed`, re-running with the same `seed` and prompt always reproduces the identical batch. Change the `seed` to get a completely new set of variations.

---

## Inputs

### Required

- `text` — The positive prompt, with wildcard and `<lora:...>` support. Resolved independently for each image in the batch.
- `negative` — The negative prompt. Supports the exact same wildcard syntax as the positive prompt, and is also resolved independently per image.
- `seed` — Base seed for **both** wildcard resolution and noise generation. Each image uses `seed + index`.
- `batch_size` — Number of images to generate. Every image resolves its own wildcards and prompt, and the whole batch is sampled at once.
- `width` / `height` — Output dimensions for the first pass.
- `steps` — Number of sampling steps.
- `cfg` — Classifier-free guidance scale.
- `sampler_name` — The sampler to use (same list as KSampler).
- `scheduler` — The scheduler to use (same list as KSampler).
- `denoise` — Denoising strength for the first pass.
- `upscale` — Enable the upscale second pass. See the [Upscale](#upscale) section below.

### Optional Inputs

- `model` — Only needed to sample images. Leave disconnected to use the node as a prompt previewer.
- `clip` — Only needed to sample images.
- `vae` — Required for the upscale pass. The node decodes the first-pass latent to pixel space, upscales it, then re-encodes. Without a VAE the upscale pass is skipped.
- `upscale_model` — Connect a **Load Upscale Model** node (e.g. an ESRGAN/4x model) to use AI super-resolution during the upscale instead of plain Lanczos. The model runs at its native scale, then the result is downscaled to the exact target size implied by `upscale_rate`.

### Advanced Inputs

These inputs are hidden behind the node's **Advanced** toggle and are collapsed by default.

**Upscale settings** (only active when `upscale` is on):

- `upscale_rate` — Upscale factor. For example, `2.0` doubles width and height. Larger values can be typed in manually.
- `upscale_denoise` — Denoising strength for the upscale pass. Lower values keep the first-pass composition; higher values add more detail but can drift from the original.
- `upscale_steps` — Number of sampling steps for the upscale pass.
- `upscale_cfg` — CFG for the upscale pass. Set to `0` to reuse the first-pass CFG.
- `upscale_sampler_name` — Sampler for the upscale pass. Select `(same as first pass)` to reuse the first-pass sampler.
- `upscale_scheduler` — Scheduler for the upscale pass. Select `(same as first pass)` to reuse the first-pass scheduler.

**Prompt encoding:**

- `strip_prompt_weights` — Strip per-token weight syntax (e.g. `(word:1.3)`) from prompts before encoding, leaving only the plain text. Enable this when using LLM-based text encoders such as T5 (used in FLUX, SD3, and other newer models). Those encoders process prompts as natural language and do not support ComfyUI/A1111-style prompt weighting — feeding them weighted syntax causes the encoder to treat the parentheses and colons as literal characters, which can degrade prompt adherence.

**Utilities:**

- `recache_wildcards` — Force a reload of all wildcard files from disk. Useful after adding or editing wildcard files. Can be turned off again after running once.

Console logging is controlled in ComfyUI's settings under **⚡MNeMiC Nodes → Wildcard Processing → Console Logging** and **⚡MNeMiC Nodes → LoRA Loading → Console Logging**. This node uses the same wildcard and LoRA matching engines as the Wildcard Processor and LoRA Loader Prompt Tags nodes.

---

## Upscale

When `upscale` is enabled the node runs a second sampling pass on the complete batch at a larger resolution, preserving each image's prompts and LoRA settings. The process is:

1. The first-pass latent is decoded to pixel space using the connected VAE.
2. If an `upscale_model` is connected, AI super-resolution runs first (e.g. a 4x ESRGAN model). The output is then scaled down to the exact target size set by `upscale_rate`, so a 4x model with `upscale_rate = 2.0` gives a clean 2× final image.
3. If no `upscale_model` is connected, Lanczos interpolation is used instead.
4. The upscaled image is re-encoded to latent space and sampled again with the upscale denoise, steps, CFG, sampler, and scheduler settings.

The upscale pass requires a VAE to be connected. If `upscale` is on but no VAE is connected, a warning is printed and the pass is skipped.

---

## Outputs

- `model` — The shared model with per-image LoRA adapters. Reuse with the same latent batch size and order.
- `clip` — CLIP with shared leading LoRA tags. Per-image CLIP changes are baked into the conditioning outputs.
- `positive` — The batched positive conditioning, one entry per image in batch order.
- `negative` — The batched negative conditioning, one entry per image in batch order.
- `latent` — The combined batch of sampled latents (empty when sampling is skipped). Route this into a VAE Decode to get images.
- `prompt` — The resolved positive prompt for each image, returned as a list (one entry per batch item). Connect to a **Show Text** node to see each resolved prompt as a separate entry.

> The `positive` and `negative` outputs line up with the `latent` batch, so a downstream KSampler fed the latent still gives every image its own prompt. Use the returned `model` to retain per-image LoRAs; keep the latent batch size and order unchanged.

---

## Prompt-Preview Mode (No Sampling)

The node only samples when it actually needs to. Sampling is **skipped** — and only the resolved prompts are returned — when either:

- `model` or `clip` is **not connected**, or
- the `latent` output is **not connected** to anything.

This makes it easy to use the node purely to test what your wildcards resolve to: leave the model/clip off (or leave the latent output unused) and read the `prompt` output. When sampling is skipped, the `latent` output is an empty placeholder.

> Note: ComfyUI caches node results by input values. After connecting/disconnecting the `latent` output you may need to change an input (or re-queue) for the node to re-evaluate whether it should sample.

---

## Save Image With Metadata Integration

Because this node samples internally (there is no separate KSampler or CLIPTextEncode node in the graph), the [Save Image With Metadata](./image_save_with_metadata.md) node cannot discover the prompts the way it normally does. There are two ways to get correct, per-image metadata:

### Automatic (recommended)

When a Batch Wildcard Sampler is present in the workflow, the saver **automatically picks up** the per-image prompts this node published and writes **each saved image its own correct positive prompt, negative prompt, and seed** (`seed + index`). No wiring and no override are required — just connect your images to the saver as usual.

This only engages when a Batch Wildcard Sampler is actually in the current graph, so it never affects unrelated workflows.

### Manual via the list output

Alternatively, wire this node's `prompt` list output into the saver's `positive_override` input. The saver applies **one prompt per image**, looping through the list if its length differs from the number of images. A single string in `positive_override` still applies to every image as before.

---

## How to Use

**To generate a varied batch:**

1. Add the **Batch Wildcard Sampler** node.
2. Write your positive (and optional negative) prompt using any wildcard syntax.
3. Set `batch_size` to the number of varied images you want.
4. Connect `model`, `clip`, and `vae`.
5. Route the `latent` output into a **VAE Decode**, then into a preview or **Save Image With Metadata** node (metadata is picked up automatically).

**To use the upscale pass:**

1. Enable `upscale`.
2. Make sure a `vae` is connected — the upscale pass requires it.
3. Optionally connect an `upscale_model` (e.g. a 4x ESRGAN) for AI super-resolution instead of Lanczos.
4. Expand the **Advanced** section to tune `upscale_rate`, `upscale_denoise`, `upscale_steps`, `upscale_cfg`, sampler, and scheduler.

**To only test prompts:**

1. Add the node and write your prompt.
2. Leave `model`/`clip` disconnected (or leave the `latent` output unused).
3. Connect `prompt` to a **Show Text** node and queue. No sampling happens.

**To use downstream conditionings:**

Connect the `model`, `positive`, `negative`, and `latent` outputs to a downstream sampler to preserve per-image conditioning and LoRA settings. Keep the batch size and image order unchanged. Anima also requires the returned model for its per-prompt text preprocessing.

## Compatibility and Limits

Anima preserves each image's T5 IDs, token weights, and original Qwen embeddings until its model-side text preprocessing runs. The processed conditionings are then stacked for batched denoising. Downstream samplers must use this node's returned model alongside its conditioning outputs. Constant per-image LoRA patches are routed to the correct image during preprocessing; step-scheduled patches apply during denoising only.

Prompt embeddings with different lengths are padded (or repeated for compatible CLIP lengths). Padding can change results on models that ignore attention masks. Initial noise uses each image's seed; ancestral/SDE sampling uses the batch's first seed for later noise, so results need not match separate runs. Auxiliary Llama/byT5 conditionings are also stacked. Unsupported differing metadata raises an error rather than reusing another image's conditioning.

Anima and SDXL are confirmed working. Other architectures depend on their conditioning formats and layer layouts. Per-image adapter routing assumes layers retain the image batch dimension or flatten contiguous tokens per image; custom models that reorder or split rows need dedicated support. Per-image LoRAs require ComfyUI's weight-adapter bypass APIs.
