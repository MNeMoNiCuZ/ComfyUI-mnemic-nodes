# 🏷️ LoRA Loader Prompt Tags

Reads `<lora:name:strength>` tags out of a prompt, applies those LoRAs to the
model and CLIP, optionally limits model weights to selected sampling steps,
and hands back the prompt with the tags removed. One node
replaces a chain of LoRA Loaders, and which LoRAs load can come from the prompt
text itself — including from a wildcard.

Based on [comfyui_lora_tag_loader](https://github.com/badjeff/comfyui_lora_tag_loader)
by badjeff, with a different file-matching system.

## Inputs

- **MODEL** — The checkpoint to patch.
- **CLIP** — Optional text encoder to patch. Its LoRA strengths are constant during encoding.
- **STRING** — Prompt text containing the tags.

## Outputs

- **MODEL** — With every matched LoRA applied, including any model step schedules.
- **CLIP** — With constant LoRA strengths, or empty when no CLIP was connected.
- **STRING** — The prompt with all `<...>` tags stripped, ready for encoding.

## Tag syntax

```
<lora:name>              strength 1.0 for both model and CLIP
<lora:name:0.8>          strength 0.8 for both
<lora:name:0.8:0.5>      model 0.8, CLIP 0.5
<lora:name:start=14>     default strengths, model active from step 14 onward
<lora:name:0.8:end=20>   model active during steps 1–20
<lora:name:0.8:start=14:end=20>  model active during steps 14–20
<lora:name:0.8:0.5:start=1:end=4>  model 0.8 during steps 1–4, CLIP 0.5
<lora:name:0.8:range=2-4,8-10>  model active during steps 2,3,4,8,9,10
<lora:name:range=2-4,8,10-12>   ranges and individual steps, default strengths
```

The name does not have to be the full filename — it is matched against your
LoRA files, preferring subfolder-aware substring hits and falling back to fuzzy
word matching. A strength of `0` disables the LoRA for both model and CLIP
unless a separate CLIP strength is specified. Either strength can be zero:
`<lora:name:0.8:0>` applies only to the model, and `<lora:name:0:0.5>` applies
only to CLIP. Fully disabled tags are removed without loading the LoRA file.

### Sampling step limits

`start=` and `end=` are optional named options; either order works. Strengths
can be omitted. Steps are counted from **1**, with both bounds inclusive.
Omitting `start=` starts at step 1; omitting `end=` continues through the end.
Each LoRA can have its own range, and scheduled and constant tags can be mixed.
For an 8-step generation, `<lora:name:0.8:start=1:end=4>` enables the model
LoRA for the first four steps and disables it for the remaining four.

Limits must be positive integers. Unknown or repeated named options, invalid
step values, and an end before the start raise an error. A start beyond the
available steps never activates; an end beyond them continues through the end.

Use `range=` for one or more finite ranges separated by commas, such as
`range=2-4,8-10`. Every endpoint is inclusive, and single steps also work:
`range=2-4,8,10-12`. The model LoRA is off outside the listed ranges. Ranges
can be listed in any order; overlapping, duplicate, and adjacent ranges are
merged and never multiply the strength. Spaces around commas and hyphens are
allowed. Empty ranges, zero/negative steps, and reversed ranges raise an error.
When combined with `start=`/`end=`, `range=` takes priority and logs a warning.

### Combining scheduling options

Scheduling options work as follows **per tag**:

**Priority: `range=` overrides both `start=` and `end=`. When both forms are
supplied, generation continues using `range=` and logs a console warning.**

| Options | Behavior |
| --- | --- |
| None | Active throughout the sampling pass. |
| `start=6` | Active from step 6 through the end. |
| `end=10` | Active from step 1 through step 10. |
| `start=6:end=10` | Active during steps 6–10, inclusive. |
| `range=2-4,8-10` | Active on steps 2, 3, 4, 8, 9, 10. |
| `start=6:range=2-4,8-10` | Steps 2–4 and 8–10; warning that `start=` is ignored. |
| `end=10:range=2-4,8-10` | Steps 2–4 and 8–10; warning that `end=` is ignored. |
| `start=6:end=10:range=2-4,8-10` | Steps 2–4 and 8–10; warning that both limits are ignored. |

Without `range=`, `start=` and `end=` define one inclusive interval. With
`range=`, only its intervals are used; `start=`/`end=` neither clip nor add to
them, and their values are ignored without validation. Option order makes no
difference. The warning appears even when optional LoRA console logging is
disabled. Invalid `range=` values still raise an error.

Different tags can use different forms in the same prompt:

```text
<lora:style:0.8:start=6:end=10> <lora:detail:0.5:range=2-4,8-10>
```

Each tag applies its own strength and schedule independently. Multiple tags
for the same LoRA stack as separate applications; use one `range=` tag to
specify multiple intervals for that LoRA at one strength.

The ranges are resolved against the actual sigma (noise-level) schedule of
each sampling pass. Intermediate model evaluations use the range containing
their noise level; a sampler evaluating the next step's sigma early will also
use that next range early. This avoids counting CFG calls as extra steps.
Steps restart from 1 on each pass, including partial-denoise, continuation,
and upscale passes; they are relative to the steps that pass actually runs.

This schedules **denoising**, not video frames. CLIP LoRAs still affect prompt
encoding at their constant strength. Video samplers using ComfyUI's standard
CFGGuider and weight-hook path can use these schedules. Custom samplers that
bypass that path are not supported by this feature.

Scheduled models enable ComfyUI's per-operation weight casting so mixed FP16 /
BF16 checkpoints remain compatible with the hook-based sampling path. This
also applies when the Batch Wildcard Upscale Sampler loads scheduled tags for
its first and upscale passes.

## Notes

Tags that match no file are skipped with a console note rather than failing the
run. The most recently used LoRA is kept in memory, so repeated runs with the
same one do not re-read it from disk. Lumina2 / ZiT models get an extra key
mapping applied automatically.

Console logging, fuzzy search and the candidate-log cap are in
**Settings → ⚡MNeMiC Nodes → LoRA Loading**.
