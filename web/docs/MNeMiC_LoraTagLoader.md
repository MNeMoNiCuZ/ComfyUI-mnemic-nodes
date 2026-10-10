# 🏷️ LoRA Loader Prompt Tags

Reads `<lora:name:strength>` tags out of a prompt, applies those LoRAs to the
model and CLIP, optionally selects sampling steps, video time windows, or strength ramps,
and hands back the prompt with the tags removed. One node
replaces a chain of LoRA Loaders, and which LoRAs load can come from the prompt
text itself — including from a wildcard.

Based on [comfyui_lora_tag_loader](https://github.com/badjeff/comfyui_lora_tag_loader)
by badjeff, with a different file-matching system.

## Inputs

- **MODEL** — The checkpoint to patch.
- **CLIP** — Optional text encoder to patch. Its LoRA strengths are constant during encoding; `time=` tags default to CLIP strength 0.
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
<lora:name:0.8:time=0-2>       video LoRA prediction during the first 2 seconds
<lora:name:0.8:time=0-2,4-6>   two video time windows, in seconds
<lora:name:0.8:time=0-2:fps=24>  explicitly use a 24 fps video timeline
<lora:name:time=0-10:blend=0.5-2>  ramp the model weight from 0.5 to 2 over 10 seconds
```

The name does not have to be the full filename — it is matched against your
LoRA files, preferring subfolder-aware substring hits and falling back to fuzzy
word matching. A strength of `0` disables the LoRA for both model and CLIP
unless a separate CLIP strength or `blend=` ramp is specified. Either strength can be zero:
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

`start=`, `end=`, and `range=` schedule **denoising**, not video frames. To
select seconds of the generated video, use `time=` (below). CLIP LoRAs affect
prompt encoding at their constant strength. Video samplers using ComfyUI's standard
CFGGuider and weight-hook path can use these schedules. Custom samplers that
bypass that path are not supported by this feature.

Scheduled models enable ComfyUI's per-operation weight casting so mixed FP16 /
BF16 checkpoints remain compatible with the hook-based sampling path. This
also applies when the Batch Wildcard Upscale Sampler loads scheduled tags for
its first and upscale passes.

### Video time windows (opt-in)

`time=0-2` selects the first two seconds of the **video timeline**, at every
denoising step. `time=0-2,4-6` selects multiple windows; decimals such as
`time=0.5-2.5` are allowed. Times start at zero and use **start-inclusive,
end-exclusive** intervals: `time=0-2` is off at and after 2 seconds, subject
to latent time resolution. This differs from the inclusive integer step ranges.

Supported models are native **MiniMax H3** and **LTXV/LTXAV**, including the
LTX 2.3/2.5 paths using those model classes. Route the loader's MODEL output
into the active video model socket or guider. The sampler must use ComfyUI's
standard CFGGuider prediction and weight-hook path; a sampler that bypasses
those hooks cannot apply this feature. Time windows on image models are unsupported.

Scheduled and fallback timed LoRAs include a model-local compatibility adapter
for ComfyUI mixed-precision operations. Serialized scale metadata is kept separate
from resident parameters; quantized weights are cached/restored with their scales.
Packed and floating-point weights in these operations use the weight setter
without requesting an in-place update.
Ordinary tags continue to use ComfyUI's standard LoRA loader.

If CPU weight pinning is refused while loading or offloading this hook-enabled
quantized model, a warning announces a fallback to unpinned CPU offload for
subsequent weights on that patcher. GPU sampling remains enabled; CPU/GPU
transfers may be slower. This avoids per-weight retries during switches such
as video generation to H3 audio refinement. Other model branches retain
ComfyUI's own pinning behavior.

Only `time=` tags install temporal processing. Ordinary tags and step-only tags
retain their existing sampling path: no temporal masks, extra model predictions,
or temporal cache allocation.

Standard H3 LoRAs targeting only the blocks' MLP `fc1`/`fc2` weights use token
contributions. They add the LoRA only at selected target-video tokens, excluding
direct additions to reference, text, and audio tokens. This uses one prediction
per model evaluation, temporarily disables ComfyUI's allocation compiler for
the pass, and skips contributions in audio-only refinement with fully frozen video.

LTX and other H3 adapter layouts use prediction blending. Each distinct active
LoRA combination is evaluated and selected for its assigned video slices.
One fixed-strength timed LoRA usually needs two predictions per model evaluation;
overlapping windows may require more. Native weight caching avoids rebuilding
weights at each branch switch but can increase VRAM/RAM use.

**On the prediction-blending path, audio uses the base prediction**, meaning the
model with ordinary and step-scheduled LoRAs but without the `time=` LoRAs.
The H3 token path makes no direct timed LoRA additions to audio, although
multimodal attention can carry indirect effects. Timed tags default their
CLIP strength to **0**, unlike ordinary tags, whose CLIP strength defaults to
the model strength. This prevents a timed LoRA from being baked into the whole
prompt. An explicit fourth strength slot still applies to CLIP globally:
`<lora:name:0.8:0.5:time=0-2>` uses CLIP strength 0.5 for the whole prompt;
that CLIP effect cannot be limited by the time window.

`fps=` is optional. The video frame rate comes from conditioning (`frame_rate` / `fps`) when
available. Otherwise it uses native defaults: **H3 24 fps**, **LTX 25 fps**.
Use `fps=` on a timed tag to override the timeline rate, especially if your
workflow's output rate differs from the conditioning rate. All timed tags on
the model must agree on the override. `fps=` does not change the model's
conditioning or the output encoder's frame rate; set those to match yourself.

Time masks follow the video VAE's latent slices: LTX's first slice represents
one frame and subsequent slices represent eight frames; H3 repeats a
**1,4,4,4,4** frame layout. Each whole slice is selected using the midpoint of
its represented frame interval. Boundaries therefore round to latent slices
and are approximate; a very short window may contain no slice midpoint.
Temporal attention and VAE decoding can carry visual influence across the
boundary, so a time window cannot guarantee complete frame isolation.
Model-side conditioning preprocessing runs without timed weight hooks; timing
affects token contributions or denoising predictions, depending on the adapter path.

**Video generation tries to "explain" the change as part of a coherent scene.**
It blends a lot across time: temporal attention shares information between
frames, and decoding blends neighboring latent slices. A hard time window can
become a gradual transition, influence neighboring frames, or leave a consistent
style throughout the shot. Scheduling controls the LoRA contribution rather
than an exact edit of the finished frames.

A **dark/light or exposure LoRA at extreme values may look like someone turning
the lights on or off**, a moving light source, or a lighting change within the
scene. Weights are not calibrated exposure stops; even a linear weight ramp
does not guarantee a linear brightness change.

Reference images, prompts, and few-step/distilled sampling also affect the result.
LoRA trigger words are valid to keep: they remain in the text conditioning for
the whole video. `time=` gates the LoRA contribution, not those words. Execution
logs can confirm a nonzero contribution without proving the visible timing works.
For a weak result, compare the LoRA without `time=`
at the same seed and workflow, then try it alone with one time window to check
whether temporal blending is weakening an otherwise effective LoRA.

`time=` and a step schedule can be used together: **both must match**. For
example, `<lora:name:0.8:range=2-4,8-10:time=0-2>` applies its video prediction
to the first two seconds only during the selected denoising steps. Existing
`range=` priority over `start=`/`end=` still applies with its warning.
The timeline starts at zero for each sampling pass; step numbering also
restarts per pass. Ordinary LoRAs remain applied in every temporal branch.

Windows beyond the clip select no slices. Invalid, empty, reversed, or
non-finite time windows raise an error; valid windows require
`0 <= start < end`. Repeated time/fps options and conflicting frame-rate
overrides raise an error. `fps=` requires `time=`.

### Blend between two weights

Use `blend=start_weight-end_weight` with one `time=` interval:

```text
<lora:name:time=0-10:blend=0.5-2>
<lora:name:time=0-10:blend=2-0.5>
<lora:MMH3-ExposureSlider-V1:time=0-10:blend=-8-8>
<lora:name:time=0-10:blend=0-2:fps=24:range=2-4>
```

The first example starts at 0.5, has intended weight 1.25 at 5 seconds, and
approaches 2 just before 10 seconds. It is **off outside the window**, including
at 10 seconds. Actual weights use latent-slice midpoints; the first/last slice
will usually be slightly inside the endpoint weights. A shorter clip uses only
the corresponding part of the ramp; the ramp is not rescaled to its duration.

- The endpoints are **absolute model weights**. `blend=` overrides a positional
  model weight and logs a warning if one is supplied; it does not multiply it.
- CLIP defaults to 0. An explicit CLIP weight remains global.
- `blend=` requires `time=` and exactly one interval per tag. Use separate tags
  for separate ramps; overlapping tags stack independently.
- Negative, decreasing, equal, and zero endpoints work. `blend=8--8` goes from
  positive 8 to negative 8; `blend=0-0` disables the model LoRA.
- Step schedules gate the ramp without restarting its progress through video
  time. `range=` still overrides `start=`/`end=` with a warning.

To hold the final strength afterward, add a fixed tag for the remaining duration:

```text
<lora:name:time=0-10:blend=0.5-2>
<lora:name:2:time=10-20>
```

H3's MLP token path applies the changing weight directly at selected video slices.
LTX and the H3 fallback interpolate **predictions evaluated at the two endpoint
weights**, which is an approximation rather than model evaluation at every
intermediate weight. This uses endpoint predictions plus the base prediction
when audio or out-of-window video requires it. Overlapping ramps require endpoint
combinations and can be substantially slower. Ordinary tags have no ramp overhead.
The visible transition still depends on how the model interprets the scene;
the new ramp needs verification in your ComfyUI workflow.

## Notes

Tags that match no file are skipped with a console note rather than failing the
run. The most recently used LoRA is kept in memory, so repeated runs with the
same one do not re-read it from disk. Lumina2 / ZiT models get an extra key
mapping applied automatically.

Console logging, fuzzy search and the candidate-log cap are in
**Settings → ⚡MNeMiC Nodes → LoRA Loading**.
