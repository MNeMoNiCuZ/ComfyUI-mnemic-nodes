# V3 Migration — What Was Applied, What Is Still Open

Part 1 is a record of what changed. Part 2 is what still needs a decision from
you, laid out so you can skim and tick.

---

# Part 1 — Applied

## 1. Node IDs renamed, with automatic workflow migration ✅

Node ids were the emoji display strings (`"📁 Get File Path"`). They are now
ASCII (`MNeMiC_GetFilePath`), with the emoji text moved to `display_name`, so
**nothing changed visually** — the node menu, node titles and search all read
exactly as before.

Old workflows are migrated automatically. `__init__.py` holds a
`LEGACY_NODE_IDS` map of every old id, and `on_load` registers a `NodeReplace`
for each one, built from the node's own schema. When a workflow containing an
old id is loaded or queued, ComfyUI rewrites the node to the new id and
restores every input and link.

Never delete an entry from `LEGACY_NODE_IDS` — it is the only thing keeping old
workflows loadable. How the replacement works, and the three ways it silently
goes wrong, is documented in `WRITING_V3_NODES.md` §11.

**One known limitation.** 🔗 String Concat / Append and 🧩 Ideogram 4 Prompt
Builder grow extra input slots from JavaScript (`string_2`, `string_3`, … and
the `region_N` pins). Those are not in the schema, so a replacement cannot
carry them and their links are dropped. `web/js/legacy_node_warning.js` raises
a warning toast naming the node and the number of connections at risk, but only
when a loaded workflow actually has something to lose.

Also updated to match: `web/js/string_concat.js` and
`web/js/ideogram4_prompt_builder.js` (they key off the node id), and the graph
scanning in `image_save_with_metadata.py` and `image_save_runtime_capture.py`,
which recognised nodes by their old id strings. Those now use a helper that
accepts the old id, the new id and the bare class name, so metadata extraction
works on old and new workflows alike.

## 2. `OUTPUT_NODE` corrected ✅

`OUTPUT_NODE` means "run on Queue even if nothing downstream needs the result".
Twelve nodes had it set without producing any output, so they fired on every
queue for no reason — including the paid Groq API calls.

| Node | Now |
|---|---|
| 💾 Save Text File With Path, 💾 Save Image With Metadata, 🖼️ Download Image from URL | still output nodes — they write files |
| ✨💬 Groq LLM, ✨📷 Groq VLM, ✨📝 Groq Transcribe, ⛔ Generate Negative Prompt | no longer output nodes: they cost money or model time, and now only run when something needs them |
| 📐 Resolution Selector, 🧹 String Cleaning, ✂️ Splitter, ✂️ Extractor, 📅 Format Date Time, 📁 Get File Path | no longer output nodes — pure functions |
| 📝 Wildcard Processor, 📝 Wildcard Processor Advanced, 🔠 Tiktoken Tokenizer | still output nodes, and now actually show something: the resolved prompt / the token count appear on the node |

**The one behaviour change to watch for:** if you had one of the middle-group
nodes sitting unconnected purely so it would fire on Queue, it no longer fires.

Dead code removed at the same time: three all-`False` `OUTPUT_IS_LIST` tuples,
two unused `DOCUMENTATION` attributes, and the per-file `NODE_CLASS_MAPPINGS`
blocks that ComfyUI never read.

## 3. Missing tooltips filled in ✅

Every input and every output in the pack now has a tooltip. Nothing existing
was reworded — rewrites are proposed in Part 2 §A instead.

Filled in: all outputs of 🎨 Colorful Starting Image, 📂 Load Images From Path,
🎲 Random Color / Bool / Int / Float / String / Seed, ✏️ all four Literals,
🔗 String Concat, 📅 Format Date Time, both 🖼️📊 Metadata Extractors and both
Ideogram nodes; the sampling inputs of 🔀 Batch Wildcard Upscale Sampler;
`images`, `file_format` and `quality` on 💾 Save Image With Metadata; the
`image` input on 🖼️ Load Image Temporarily; and every input and output of the
unregistered Groq Completion node.

## 4. Help pages for every node ✅

Every registered node now has a help page, opened from the orange `?` in the
node's title bar (`web/js/help_button.js`), or from the node Info panel (ⓘ in
the selection toolbox, or right-click → Node Info).

**Yes, it is standardized now** — it was not when most of these nodes were
written. Your installed frontend (1.45.21) resolves custom-node help as:

```
/extensions/ComfyUI-mnemic-nodes/docs/<node_id>/<locale>.md    (tried first)
/extensions/ComfyUI-mnemic-nodes/docs/<node_id>.md             (fallback)
```

so the files live in `web/docs/<node_id>.md`. This is exactly why §1 had to
happen first: a filename of `🖼️+📝 Load Text-Image Pair (Single).md` is not
something to rely on across Windows, HTTP encoding and git.

42 pages written, one per registered node, all following the same layout:
title, one-paragraph intro, Inputs, Outputs, How it works, Examples, Notes.
The long reference material now lives there — wildcard syntax, the property-tag
list, strftime directives, filename tokens, the Ideogram canvas shortcuts, the
resolution priority order, Groq API-key setup.

Part 2 §B proposes trimming the giant mouseover tooltips now that this content
has a proper home.

## 5. Advanced sections ✅

| Node | Moved behind **Show advanced inputs** |
|---|---|
| ✨💬 Groq LLM / ✨📷 Groq VLM | `max_tokens`, `top_p`, `seed`, `max_retries`, `stop`, `json_mode` |
| ✨📝 Groq Transcribe | `response_format`, `temperature`, `language`, `max_retries` |
| 📐 Resolution Selector | `multiply`, `swap_width_and_height`, `image_min_length`, `image_max_length`, `snap_to_nearest`, `snap_resolution`, `batch_size` |
| 🖼️📊 Metadata Extractor (Single) | `filter_params` |
| 🖼️📊 Metadata Extractor (List) | `filter_params`, `max_file_count` |
| 💾 Save Image With Metadata | `quality`, `embed_workflow`, `strip_lora_prompt` |
| 🔀 Batch Wildcard Upscale Sampler | (already done before this pass) |

Left fully visible as you asked: **🎨 Colorful Starting Image**,
**🧹 String Cleaning** and **🎲 Ideogram 4 Random Prompter**. On these nodes
the options *are* the point.

## 6. Placeholders — only the two you approved ✅

To be clear about what a placeholder is, since the proposal was vague: it is
**greyed-out background text inside an empty widget**. It is not a value. It is
not saved in the workflow, it is never sent to the node, and it disappears the
moment there is any real text in the field. Empty stays empty.

Added to exactly two inputs:

- `wildcard_string` on both Wildcard Processors —
  `A photo of a __sample_colors__ {dog|cat|monkey}.`
  (🔀 Batch Wildcard Upscale Sampler already had one.)
- `prefix` on 💾 Save Text File With Path — `[time(%Y-%m-%d - %H.%M.%S)] - `

On your note about that second one: the original proposal used a
`%date:...%`-style example, which was wrong — that syntax belongs to
💾 Save Image With Metadata, not this node. Save Text File only understands
`[time(<strftime>)]` and `[hostname]`. There is no `[datetime]` token, so the
placeholder shows the real thing that works.

Nothing else got a placeholder. The rest of the proposed list is dropped.

---

# Part 2 — Open decisions

## A. Tooltip rewrites

Nothing below has been changed. These are existing tooltips I think read badly,
with a suggested replacement. The pattern in most cases: they name the type
instead of explaining the behaviour, or they are subtly wrong.

### A1. Wrong or misleading — worth fixing regardless of style

| Node | Field | Current | Proposed |
|---|---|---|---|
| 🖼️ Download Image from URL | `save_path` | "Optional path to save the image. Defaults to the current directory." | "Folder to save a copy into. Leave empty to skip saving and only pass the image on." — empty does not save anywhere, so the current text is simply wrong |
| ⛔ Generate Negative Prompt | `num_beams` | "Number of beams for beam search. Higher values improve accuracy." | "Beam search width. Higher is slower and gives safer, less varied text." — it does not improve accuracy |
| 📐 Resolution Selector | `custom_width` / `custom_height` | "Custom width (Only used with Custom preset)" | "Width used when no preset, user preset or input image applies." — an input image or user preset also overrides it |
| 🖼️📊 Metadata Extractor (both) | `image_input` | "A list/batch of images. This has priority over input_path." | "An image already in the workflow. Takes priority over input_path, but carries no metadata — connect a path if you need the settings." |
| 💾 Save Image With Metadata | `strip_lora_prompt` | "Strip LoRAs from prompt." | "Remove `<lora:...>` tags from the prompt recorded in the file." |
| 🎲 Load Random Checkpoint | `model` / `clip` / `vae` / `path` outputs | "…(MODEL)", "…(CLIP)", "…(VAE)", "…(STRING)" | drop the type suffix — the socket already shows it |

### A2. Restates the type instead of saying anything

| Node | Field | Current | Proposed |
|---|---|---|---|
| ✏️ Literal Bool | `value` | "Boolean value (True or False)." | "The switch value. Wire it to several nodes to drive them all from one toggle." |
| ✏️ Literal Int | `value` | "Integer value." | "Any whole number. Useful when several nodes should share one value." |
| ✏️ Literal Float | `value` | "Floating-point value." | "Any decimal number. Useful when several nodes should share one value." |
| ✏️ Literal String | `value` | "Text string value. Supports multiple lines." | "Any text; newlines are kept. Useful for a prompt fragment reused in several places." |
| 🧹 String Cleaning | `input_string` | "Enter the text to be cleaned." | "The text to clean. Passes through untouched until an option below is enabled." |
| 🔠 Tiktoken Tokenizer | `input_string` | "Enter the text to be tokenized." | "The text to measure. Counts are OpenAI's, so treat them as a guide for image models." |
| 🏷️ LoRA Loader Prompt Tags | `CLIP` | "The CLIP model being used" | "The CLIP to patch with any LoRAs found in the text." |
| 📁 Get File Path | `image` | "Make sure to select any file type when uploading a non-image file." | "The file to split into parts. The upload dialog accepts any file type — switch its filter to all files for non-images." |

### A3. Output tooltips with redundant or missing information

| Node | Field | Current | Proposed |
|---|---|---|---|
| ✨ all four Groq nodes | `api_response` | "The API response. This is the text generated by the model" | "The text generated by the model." — drop the first sentence, add the period |
| 📁 Get File Path | `file_path_only` | "The path to the file" | "The containing folder, without the filename." — currently indistinguishable from `full_file_path` |
| 📁 Get File Path | `file_name_only` / `file_extension_only` | "The name of the file" / "The extension of the file" | "Filename without its extension." / "Extension, including the dot." |
| 🖼️ Download Image from URL | all three outputs | "The downloaded image" / "The width of the image" / "The height of the image" | add the periods; width/height → "Width of the downloaded image, in pixels." |
| 🔠 Tiktoken Tokenizer | the four `..._list` outputs | "…(output as list)" | "Same as the output above, but flagged as a list so downstream nodes iterate over it." |
| 🔠 Tiktoken Tokenizer | `split_token_ids`, `special_tokens_used`, `text_hash`, the three chunk outputs | no trailing periods | add them |
| 🖼️ Load Image Advanced | `mask` | "The alpha channel of the image, if it exists." | "The alpha channel, or fully black if the image has none." — says what you actually get |
| 📐 Resolution Selector | `latent` | "The final scaled latent." | "An empty latent at the final size, `batch_size` deep." |

### A4. Long and repetitive but not wrong

Six nodes share this seed tooltip verbatim:

> "Seed for random number generator. Use -1 for random seed (different each
> time), or set a specific value for reproducibility."

Proposed: **"`-1` rolls a new value every run. Any other number repeats the
same result."** Same information, one line instead of three.

Similar trims available on the range inputs: "Minimum value for the random
integer (inclusive)." → "Lowest number that can come out. Included in the
range."

- [ ] **A1** apply — recommended, these are factually wrong
- [ ] **A2** apply
- [ ] **A3** apply
- [ ] **A4** apply

## B. Trim the manual-length tooltips now that help pages exist

This is the thing you flagged in point 4: several tooltips are pages long,
which is miserable as a mouseover. All of that content is now in the node's
help page, so the tooltip can go back to being a one-liner.

| Node | Field | Tooltip today | Proposed tooltip |
|---|---|---|---|
| 📝 Wildcard Processor (+ Advanced) | `wildcard_string` | ~15 lines: every wildcard syntax form with examples | "The prompt template to resolve. Supports `__file__` wildcards, `{a\|b}` choices, weights, multi-picks and variables — see the node Info panel for the full syntax." |
| 🔀 Batch Wildcard Upscale Sampler | `text` | the same syntax block again, plus per-image notes | "Positive prompt. Resolved separately for every image; supports wildcards and `<lora:name:strength>` tags. Press ? for the syntax." |
| 🔀 Batch Wildcard Upscale Sampler | `negative` | 6 lines | "Negative prompt. Resolved per image, with the same syntax as the positive prompt." |
| 📅 Format Date Time | `date_format` | 21-line directive table | "Date/time format string using strftime directives. Press ? for the full list." |
| 💾 Save Image With Metadata | `filename_prefix`, `folder` | the same 24-line token table, twice | "Filename prefix. Supports date tokens, `%seed` and `%model` — see the node Info panel for the list." / "Subfolder under `output`. Same tokens as the filename prefix." |
| ✨📝 Groq Transcribe | `language` | one line plus 100+ ISO codes | "Language of the audio as an ISO 639-1 code, e.g. `en`, `fr`, `sv`. Press ? for the full list." |
| ⚙️ Prompt Property Extractor | `input_string` | 20 lines listing every supported tag | "Prompt text, optionally carrying `<tag:value>` settings that override the widgets below. Press ? for the tag list." |
| 🎲 Ideogram 4 Random Prompter | ~8 fields | 6-12 lines each, with worked examples | keep the first sentence of each; the examples are already on the help page |
| 🎨 Colorful Starting Image | `color_palette`, `positioning_bias`, `arrangement`, `background_color`, … | bulleted lists of every option | keep one line; the option lists are already on the help page |
| 🔀 Batch Wildcard Upscale Sampler | `upscale_rate`, `upscale_noise_inject_strength`, `strip_prompt_weights` | 6-10 lines each | keep the first sentence, move the reasoning to the help page |

Nothing is lost — every one of those blocks is already written into
`web/docs/`. This is the biggest readability win left in the pack.

- [ ] **B** trim the long tooltips and rely on the help pages

## C. `DynamicCombo` for 📐 Resolution Image Size Selector

You said this section made no sense. Here it is properly.

### The problem

The node has four different ways to get a resolution, and all four sets of
widgets sit on screen at the same time:

```
preset:        [Custom ▾]        ← one of ~50 model presets, or "Custom"
preset_user:   [None ▾]          ← one of your saved presets, or "None"
custom_width:  [512]             ← only used sometimes
custom_height: [512]             ← only used sometimes
(image socket)                   ← wins over everything if connected
```

Which one actually applies is decided by a priority order you cannot see:
image, then user preset, then preset, then the custom numbers. You have to know
it or read the description. And the unused widgets do not grey out, so
`custom_width` sits there showing `512` while the node quietly uses a preset's
832 — which reads like a bug the first few times.

### What `DynamicCombo` is

A V3 input type that renders **only the widgets belonging to the option you
picked**. One dropdown chooses the mode; the widgets for the other modes are
not drawn at all.

### What the node would look like

```
source: [preset ▾]          →  preset:      [SDXL: 832x1216 ▾]
source: [user preset ▾]     →  preset_user: [Favorites: 768x768 ▾]
source: [custom ▾]          →  width: [512]   height: [512]
source: [from image ▾]      →  (image socket only)
```

The hidden priority rule disappears, because there is nothing left to
prioritise: you pick the source and only its controls exist.

### The cost

The input set changes shape, so this cannot be a silent edit:

- `custom_width` / `custom_height` become `width` / `height` nested inside the
  `custom` option; `preset` and `preset_user` move inside their own options.
- Existing workflows would need a second `NodeReplace` with a real
  `input_mapping`, and it would have to *infer* a `source` value from the old
  widget values: if `preset_user` was not "None" → `user preset`, else if
  `preset` was not "Custom" → `preset`, else `custom`.
- `NodeReplace` can set a **fixed** value, but it cannot run that conditional
  logic. So every migrated node would come back set to one single mode, and any
  that used a different one would silently produce the wrong resolution.

That last point is the killer.

### Recommendation

**Do it, but as a new node rather than a conversion.** Ship it alongside as
e.g. 📐 Resolution Selector (Source), leave the current node untouched, and
deprecate the old one later only if the new one earns it. Clearer UI, zero risk
to saved workflows.

If you would rather keep one node, the honest alternative is to leave the
inputs alone and just make the rule visible: put `preset` first and change the
*display names* (not the ids) of the custom fields to something like
`custom_width (used if nothing above applies)`. Ugly, but free and safe.

The two other nodes originally floated for this treatment — ✂️ String Text
Extractor and ✂️ String Text Splitter — are not worth it. Three or four widgets
each and no hidden rules.

- [ ] **C1** add a new `DynamicCombo` resolution node, leave the old one alone — recommended
- [ ] **C2** convert the existing node, accepting a one-mode guess for old workflows
- [ ] **C3** leave it; just clarify the widget display names

## D. Two unreachable nodes — what is actually missing

You asked what I was proposing here. Properly, per node:

### `nodes/groq_api_completion.py` — ✨💬 Groq Completion API

**Reachable?** No. It is not imported anywhere, so it has never been loadable
in any released version of the pack.

**Is it replaced?** Yes, completely. ✨💬 Groq LLM API does the same job (chat
completions) and ✨📷 Groq VLM API covers the image half. The Completion node
is an earlier draft of both: its model list is two generations stale
(`llama-3.1-70b-versatile`, `mixtral-8x7b-32768`, `gemma-7b-it`,
`llava-v1.5-7b-4096-preview` — all retired by Groq), and its image path has a
real bug: it calls `encode_image()` with a PIL image where that function
expects a file path, so the llava branch would fail if it ever ran.

**Anything lost by deleting it?** Nothing.

**Recommendation: delete the file.** No workflow can reference it, so there is
nothing to migrate and nothing to deprecate.

### `nodes/groq_api_alm_translate.py` — ✨🌐 Groq ALM API - Translate

**Reachable?** No — its import in `__init__.py` is commented out, and has been
for a while. But unlike the Completion node this one is *finished*: the code is
current, its model list (`whisper-large-v3`) is still valid, and this migration
converted it along with everything else. It works; it is just switched off.

**Is it replaced?** No. ✨📝 Groq Transcribe writes down what was said, in the
language it was said in. Translate does speech → **English text** in one call.
Feed French audio to Transcribe and you get French text; Translate gives you
English. Nothing else in the pack does that.

**So the real question is why it was switched off.** There is no note in the
code or the git history, so I don't know. If it was because the endpoint is
English-only and that felt too narrow — that limitation is already stated in
the node's own name (`[EN only]`), and it is Groq's limitation, not yours.

**Recommendation: register it.** It is working code covering a capability
nothing else has, it is already migrated, and its `LEGACY_NODE_IDS` entry is
already written. Enabling it is three steps: uncomment the import, uncomment
its line in `get_node_list()`, write its help page. If you switched it off for
a reason you remember, say so and I will delete it and drop the legacy entry
with it.

### Experimental badges

Separately: three nodes patch ComfyUI's runtime or carry a large custom-JS
surface, and V3 can badge that so it is visible before you place the node.

| Node | Why |
|---|---|
| 🔀 Batch Wildcard Upscale Sampler | monkey-patches the sampler during the upscale pass |
| 💾 Save Image With Metadata | installs a hook into ComfyUI's executor at load time |
| 🧩 Ideogram 4 Prompt Builder | large custom canvas UI, actively changing |
| 🎲 Ideogram 4 Random Prompter | already says EXPERIMENTAL in its description |
| ⛔ Generate Negative Prompt | already says EXPERIMENTAL in its description |

`is_experimental=True` adds a small badge and nothing else — no behaviour
change, no effect on saved workflows. The last two already say it in prose; the
flag just makes it visible in the node menu.

- [ ] **D1** delete `groq_api_completion.py`
- [ ] **D2** register ✨🌐 Groq ALM Translate — recommended — or delete it
- [ ] **D3** set `is_experimental=True` on the five nodes above

## E. Note, no action needed: the `IS_CHANGED` time hacks

🎲 Random Seed and 📅 Format Date Time force a re-run on every queue by
returning `time.time()` as their fingerprint. That is correct and stays —
re-rolling every run is the whole point of both nodes. Recorded here only so it
is not mistaken for something the migration should have "cleaned up".

`not_idempotent=True` is **not** a substitute: it only adds the node id to the
cache key, it does not force re-execution. 🖼️ Load Image Temporarily already
hashes the file contents, which is the right approach for a file-backed node.
