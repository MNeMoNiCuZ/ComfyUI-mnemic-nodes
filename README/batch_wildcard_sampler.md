# 🔀 Batch Wildcard Sampler

The Batch Wildcard Sampler generates a batch of images where **every image resolves its own independent set of wildcards**. A normal sampler applies a single prompt to the whole batch; this node instead resolves the prompt separately for each batch index, so a single run produces a different prompt — and therefore a different image — for each item in the batch.

It is an all-in-one node: it resolves the wildcards, loads any LoRAs referenced in the prompt, encodes each prompt through CLIP, and samples each image, returning one combined latent batch. It can also be used purely as a prompt previewer, with no model attached, to check what your wildcards resolve to.

Huge thanks and credits to ChronoKnight for the initial version of this node!
- https://github.com/KChronoKnight
- https://civitai.com/user/ChronoKnight

## Explanation

Internally, ComfyUI requires conditioning tensors to have a batch dimension of 1, which normally prevents giving each image in a batch its own prompt. This node works around that by looping internally:

1. Resolve the wildcards for batch index `i`.
2. Load any LoRAs referenced by `<lora:...>` tags in the resolved prompt onto a clone of the model and CLIP.
3. Encode the resolved positive and negative prompts through CLIP (with LoRA tags stripped from the text).
4. Sample a single image with a unique seed.
5. Repeat for every index, then combine all results into one output batch.

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
- **Multiple Selections** — `{2$$a|b|c|d}` (fixed count) and `{1-3$$a|b|c|d}` (ranged count).
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

- `text` — The positive prompt, with wildcard and `<lora:...>` support. Resolved independently for each image in the batch.
- `negative` — The negative prompt. Supports the exact same wildcard syntax as the positive prompt, and is also resolved independently per image.
- `seed` — Base seed for **both** wildcard resolution and noise generation. Each image uses `seed + index`.
- `batch_size` — Number of images to generate. Each image resolves its own wildcards and gets its own prompt.
- `width` / `height` — Output dimensions.
- `steps` — Number of sampling steps.
- `cfg` — Classifier-free guidance scale.
- `sampler_name` — The sampler to use (same list as KSampler).
- `scheduler` — The scheduler to use (same list as KSampler).
- `denoise` — Denoising strength.
- `recache_wildcards` — Force a reload of all wildcard files from disk. Can be turned off again after running once.
- `console_log` — Print detailed wildcard processing steps to the console.

### Optional Inputs

- `model` — Only needed to sample images.
- `clip` — Only needed to sample images.
- `vae` — Reserved for sampling workflows.

---

## Prompt-Preview Mode (No Sampling)

The node only samples when it actually needs to. Sampling is **skipped** — and only the resolved prompts are returned — when either:

- `model` or `clip` is **not connected**, or
- the `latent` output is **not connected** to anything.

This makes it easy to use the node purely to test what your wildcards resolve to: leave the model/clip off (or leave the latent output unused) and read the `resolved_prompts` output. When sampling is skipped, the `latent` output is an empty placeholder.

> Note: ComfyUI caches node results by input values. After connecting/disconnecting the `latent` output you may need to change an input (or re-queue) for the node to re-evaluate whether it should sample.

---

## Outputs

- `latent` — The combined batch of sampled latents (empty when sampling is skipped). Route this into a VAE Decode to get images.
- `resolved_prompts` — The resolved positive prompt for each image, returned as a list (one entry per batch item). It behaves like the list outputs on the **Metadata Extractor (List)** and **String Text Splitter** nodes — connect it to a **Show Text** node to see each prompt as a separate entry.

---

## Save Image With Metadata Integration

Because this node samples internally (there is no separate KSampler or CLIPTextEncode node in the graph), the [Save Image With Metadata](./image_save_with_metadata.md) node cannot discover the prompts the way it normally does. There are two ways to get correct, per-image metadata:

### Automatic (recommended)

When a Batch Wildcard Sampler is present in the workflow, the saver **automatically picks up** the per-image prompts this node published and writes **each saved image its own correct positive prompt, negative prompt, and seed** (`seed + index`). No wiring and no override are required — just connect your images to the saver as usual.

This only engages when a Batch Wildcard Sampler is actually in the current graph, so it never affects unrelated workflows.

### Manual via the list output

Alternatively, wire this node's `resolved_prompts` list output into the saver's `positive_override` input. The saver applies **one prompt per image**, looping through the list if its length differs from the number of images. A single string in `positive_override` still applies to every image as before.

---

## How to Use

**To generate a varied batch:**

1. Add the **Batch Wildcard Sampler** node.
2. Write your positive (and optional negative) prompt using any wildcard syntax.
3. Set `batch_size` to the number of varied images you want.
4. Connect `model` and `clip`.
5. Route the `latent` output into a **VAE Decode**, then into a preview or **Save Image With Metadata** node (metadata is picked up automatically).

**To only test prompts:**

1. Add the node and write your prompt.
2. Leave `model`/`clip` disconnected (or leave the `latent` output unused).
3. Connect `resolved_prompts` to a **Show Text** node and queue. No sampling happens.
