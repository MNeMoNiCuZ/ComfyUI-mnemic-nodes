# 🔀 Batch Wildcard Upscale Sampler

The Batch Wildcard Sampler generates multiple images where **every image resolves its own independent set of wildcards and LoRA loading**. A normal sampler applies a single prompt to the whole batch; this node instead resolves the prompt separately for each index, so a single run produces a different prompt — and therefore a different image — for each item.

It is an all-in-one node: it resolves the wildcards, loads any LoRAs referenced in the prompt, encodes each prompt through CLIP, samples each image, and optionally runs an upscale second pass. It can also be used purely as a prompt previewer with no model attached, to check what your wildcards resolve to.

Additionally this node has an Upscale pass that can be enabled, using pixel-space upscaling with lanczos, or using an upscale model. Like `Hires-fix` from A1111/Forge.

Huge thanks and credits to ChronoKnight for the initial version of this node!

- https://github.com/KChronoKnight
- https://civitai.com/user/ChronoKnight

<img width="2175" height="639" alt="image" src="https://github.com/user-attachments/assets/316a9bc4-16a7-4887-8fc7-ca06c6b149ae" />

## About Batching

Despite the name, this node is **not currently** doing true sampler batching. It processes one image at a time internally: resolve wildcards, encode prompts, sample, optionally upscale, then move to the next item. The benefit is convenience and some speed-ups from keeping the whole sequence inside one node and returning one combined output at the end, but the actual image generation is still sequential rather than batched.

## Explanation

Internally, ComfyUI requires conditioning tensors to have a batch dimension of 1, which normally prevents giving each image in a batch its own prompt. This node works around that by looping internally:

1. Resolve the wildcards for batch index `i`.
2. Load any LoRAs referenced by `<lora:...>` tags in the resolved prompt onto a clone of the model and CLIP.
3. Encode the resolved positive and negative prompts through CLIP (with LoRA tags stripped from the text).
4. Sample a single image with a unique seed.
5. Optionally run an upscale second pass on the result.
6. Repeat for every index, then combine all results into one output batch.

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

### Interaction with Save Image With Metadata

Because the resolved prompts retain their `<lora:...>` tags, the [Save Image With Metadata](./image_save_with_metadata.md) node decides how to handle them based on its own `strip_lora_prompt` toggle:

- `strip_lora_prompt` **on** → the `<lora:...>` tags are removed from the saved prompt text (the LoRA hashes are still recorded separately).
- `strip_lora_prompt` **off** → the `<lora:...>` tags are kept in the saved prompt text.

---

## Per-Image Resolution & Seeding

Every batch index is resolved and sampled independently:

- **Wildcards** are resolved with `seed + index`, so each image draws a different result while staying fully reproducible.
- **Noise** for each image is also generated with `seed + index`.

Because both use the same base `seed`, re-running with the same `seed` and prompt always reproduces the identical batch. Change the `seed` to get a completely new set of variations.

---

## Inputs

### Required

- `text` — The positive prompt, with wildcard and `<lora:...>` support. Resolved independently for each image in the batch.
- `negative` — The negative prompt. Supports the exact same wildcard syntax as the positive prompt, and is also resolved independently per image.
- `seed` — Base seed for **both** wildcard resolution and noise generation. Each image uses `seed + index`.
- `batch_size` — Number of images to generate sequentially. This is not a true sampler batch; each image resolves its own wildcards and prompt, then runs one after another inside the node.
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
- `console_log` — Print detailed wildcard processing steps to the console.

---

## Upscale

When `upscale` is enabled the node runs a second sampling pass on each image at a larger resolution. The process is:

1. The first-pass latent is decoded to pixel space using the connected VAE.
2. If an `upscale_model` is connected, AI super-resolution runs first (e.g. a 4x ESRGAN model). The output is then scaled down to the exact target size set by `upscale_rate`, so a 4x model with `upscale_rate = 2.0` gives a clean 2× final image.
3. If no `upscale_model` is connected, Lanczos interpolation is used instead.
4. The upscaled image is re-encoded to latent space and sampled again with the upscale denoise, steps, CFG, sampler, and scheduler settings.

The upscale pass requires a VAE to be connected. If `upscale` is on but no VAE is connected, a warning is printed and the pass is skipped.

---

## Outputs

- `model` — The model after LoRA patches from the last batch item have been applied. Useful for chaining into other nodes.
- `clip` — The CLIP after LoRA patches from the last batch item have been applied.
- `positive` — The positive conditioning encoded from the last batch item's resolved prompt.
- `negative` — The negative conditioning encoded from the last batch item's resolved prompt.
- `latent` — The combined batch of sampled latents (empty when sampling is skipped). Route this into a VAE Decode to get images.
- `prompt` — The resolved positive prompt for each image, returned as a list (one entry per batch item). Connect to a **Show Text** node to see each resolved prompt as a separate entry.

> The `model`, `clip`, `positive`, and `negative` outputs reflect the **last** batch item. They are useful for passing conditionings and a patched model downstream without needing separate encoder nodes.

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

Connect the `positive` and `negative` outputs to other nodes (e.g. a second KSampler) to reuse the encoded conditioning from the last batch item without needing separate CLIPTextEncode nodes.
