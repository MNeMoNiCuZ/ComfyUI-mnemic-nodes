# 🏷️ LoRA Loader Prompt Tags

Loads LoRA models using tags in the prompt.

### Syntax and Weights

The basic syntax is `<lora:loraName:strength>`.

-   The default strength is `1.0` if not specified (e.g., `<lora:myLora>`).
-   A strength of `0` disables the LoRA for both model and CLIP unless a separate CLIP weight or a `blend=` ramp is specified.
-   If an invalid strength is provided (e.g., non-numeric text), it will also be treated as `1.0`.

#### CLIP Weight
You can provide a separate weight for the CLIP model.

-   **Syntax**: `<lora:loraName:model_weight:clip_weight>`
-   If the CLIP weight is omitted, it defaults to the model's weight, except `time=` tags, which default to **0**.
-   Either weight can be `0`: `<lora:myLora:0.8:0>` applies only to the model; `<lora:myLora:0:0.5>` applies only to CLIP.

#### Sampling Step Limits

Add optional `start=` and/or `end=` options without changing the strength slots:

```text
<lora:myLora:start=14>                Default strengths; model from step 14 onward
<lora:myLora:0.8:end=20>              Model during steps 1–20
<lora:myLora:0.8:start=14:end=20>      Model during steps 14–20
<lora:myLora:0.8:0.5:start=1:end=4>    Model 0.8 during steps 1–4; CLIP 0.5
<lora:myLora:0.8:range=2-4,8-10>      Model during steps 2,3,4,8,9,10
<lora:myLora:range=2-4,8,10-12>       Ranges and individual steps, default strengths
```

Steps start at **1** and both limits are inclusive. Omitted limits mean the
start or end of the sampling pass. Each LoRA has its own optional range.
Invalid, repeated, or unknown named options raise an error; limits must be
positive integers with `end >= start`.

`range=` accepts comma-separated inclusive ranges or single steps. The model
LoRA is off outside them. Ranges may be unordered; overlaps, duplicates, and
adjacent ranges are merged without multiplying the strength. Spaces around
commas and hyphens are allowed. Empty or reversed ranges and steps below 1
raise an error. When combined with `start=`/`end=`, `range=` takes priority
and a warning is logged.

#### Combining Scheduling Options

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

Different tags may use different forms in the same prompt:

```text
<lora:style:0.8:start=6:end=10> <lora:detail:0.5:range=2-4,8-10>
```

Each tag has its own strength and schedule. Multiple tags for the same LoRA
stack as separate applications; use one `range=` tag for multiple intervals
at one strength.

Limits schedule model weights using each pass's actual noise schedule, not
video frames or individual model calls. Intermediate evaluations follow their
noise level, so samplers that evaluate a later sigma early can switch early.
Step numbering restarts for each sampling pass, including continuation and
upscale passes. CLIP strength remains constant during prompt encoding.
Requires ComfyUI's standard CFGGuider/weight-hook sampling path; video-specific
samplers that bypass it are unsupported.

#### Video Time Windows (Opt-In)

Use `time=` for seconds on the **generated video's timeline**, independently
of the denoising steps:

```text
<lora:myLora:0.8:time=0-2>                 First 2 seconds of video
<lora:myLora:0.8:time=0-2,4-6>             Multiple video time windows
<lora:myLora:0.8:time=0.5-2.5:fps=24>      Decimal seconds; explicit timeline fps
<lora:myLora:0.8:range=2-4,8-10:time=0-2>  First 2 seconds, only on selected steps
```

Time intervals include the start and exclude the end; `time=0-2` is off at
and after 2 seconds, subject to latent time resolution. Step intervals remain
inclusive. When a tag has both a time window and a step schedule, both must
match. `range=` still overrides `start=`/`end=` and logs a warning.

Supported native models: **MiniMax H3** and **LTXV/LTXAV**, including LTX
**2.3/2.5** using those classes. Connect the loader's MODEL output to the active
video model input/guider. Requires ComfyUI's standard CFGGuider prediction and
weight-hook sampling path. Image models and custom samplers bypassing that
path are unsupported.

Scheduled and fallback timed LoRAs use a model-local compatibility adapter for
ComfyUI mixed-precision operations. It reads actual parameters instead of
serialized scale metadata and caches/restores quantized weights with their
scales. Both packed quantized weights and floating-point weights in these
operations use their weight setter without requesting an in-place update.
Ordinary tags continue to use ComfyUI's standard LoRA loader.

If CPU weight pinning is refused while loading or offloading the hook-enabled
quantized model, it logs a warning and uses unpinned CPU offload for subsequent
weights on that patcher. GPU sampling remains enabled; CPU/GPU transfers may
be slower. This fallback avoids retrying every weight during a model switch,
such as from video generation to H3 audio refinement. Other model branches
retain ComfyUI's own pinning behavior.

**No `time=` means no temporal wrapper, masks, extra predictions, or temporal
cache.** Constant and step-only LoRAs use their existing paths.

H3 LoRAs containing standard low-rank adapters only for the blocks' MLP
`fc1`/`fc2` weights use token contributions: the LoRA is added at selected
target-video tokens, excluding direct additions to reference, text, and audio
tokens. This path uses one prediction per model evaluation and temporarily
disables ComfyUI's allocation compiler for that sampling pass. An audio-only
refinement pass with fully frozen video skips these token contributions.

LTX and other H3 adapter layouts use prediction blending instead. Each distinct
active LoRA combination is evaluated and selected along the video time axis.
One fixed-strength timed LoRA typically needs two predictions per model
evaluation; overlapping timed LoRAs may need more. Weight caching for this path
may increase VRAM/RAM use. Audio uses the base prediction without timed LoRAs,
while retaining ordinary/step LoRAs. On the H3 token path, audio has no direct
timed LoRA addition, but multimodal attention can still carry indirect effects.

Timed tags default CLIP strength to **0** to avoid a global prompt effect.
An explicit CLIP weight is honored globally and cannot be time-masked:
`<lora:myLora:0.8:0.5:time=0-2>` applies CLIP strength 0.5 to the whole prompt.
Ordinary tags retain their existing CLIP default (the model strength).

`fps=` is optional. The timeline uses conditioning `frame_rate`/`fps`, falling back to **24 fps
for H3** or **25 fps for LTX**. `fps=` overrides the time-mask calculation only;
it does not change model conditioning or output encoding. Match it to your
actual output rate. Timed tags must agree on an explicit override. `fps=`
requires `time=`.

Time boundaries round to video latent slices using their frame-interval
midpoints. LTX uses a one-frame first slice then eight frames per slice; H3
uses repeating **1,4,4,4,4** frame slices. Short windows may select no slice.
Temporal attention and VAE decoding can carry influence across boundaries, so
a time window does not provide complete frame isolation. Model-side conditioning
preprocessing runs without timed weight hooks; timing affects token contributions
or denoising predictions, depending on the adapter path.

**Video scheduling controls the LoRA contribution, not an exact visual edit.**
Video generation tries to "explain" the change as part of a coherent scene,
blending a lot across time rather than treating each frame independently.
Temporal attention shares information between frames, and decoding blends
neighboring latent slices. A sharp schedule boundary can therefore become a
gradual transition, spread beyond the window, or preserve a consistent style
throughout the shot.

For example, a dark/light or exposure LoRA at extreme weights may be interpreted
as **someone turning the lights on or off**, a light source moving, or a lighting
change in the scene. It does not necessarily look like an exposure slider being
applied to the finished frames. LoRA weights are not calibrated exposure stops,
and a linear weight ramp does not guarantee a linear brightness change.

Reference images, prompts, and few-step/distilled sampling also influence the
visible result. LoRA trigger words are valid to keep in the prompt; they remain
in the text conditioning for the whole video. The time setting gates the LoRA
contribution, not those words. Nonzero execution logs confirm that code ran,
not that the requested visible timing was achieved.
To diagnose a weak result, compare the LoRA without `time=` using the same seed
and workflow, then try that LoRA alone with one time window. This distinguishes
a weak ordinary LoRA effect from a problem introduced by temporal blending.

Each sampling pass restarts its timeline at zero and its steps at one. Time
windows beyond the clip select nothing. Windows require finite seconds with
`0 <= start < end`; malformed, empty, reversed, or repeated options and
conflicting fps overrides raise an error.

#### Blend Between Two Weights

Add `blend=start_weight-end_weight` to interpolate linearly over one `time=`
window:

```text
<lora:myLora:time=0-10:blend=0.5-2>
<lora:myLora:time=0-10:blend=2-0.5>
<lora:MMH3-ExposureSlider-V1:time=0-10:blend=-8-8>
<lora:myLora:time=0-10:blend=0-2:fps=24:range=2-4>
```

For the first example, the intended weight is 0.5 at 0 seconds, 1.25 at 5
seconds, and approaches 2 just before 10 seconds. It is **off outside the
window**, including at 10 seconds. Sampling uses latent-slice midpoints, so the
first and last selected slices usually have weights slightly inside the endpoints.
If the clip ends before 10 seconds, the ramp stops at the corresponding
intermediate weight; it is not stretched to the clip length.

The two numbers are **absolute model weights**. `blend=` overrides a positional
model strength and logs a warning if one is supplied; it does not multiply it.
CLIP still defaults to 0 and an explicit CLIP strength stays global. Each tag
with `blend=` must have exactly one time interval; use separate tags for more
ramps. Negative, decreasing, equal, and zero endpoints are supported, including
`blend=8--8` for positive-to-negative and `blend=0-0` to disable the model LoRA.
`blend=` requires `time=`. A step schedule gates the ramp without changing its
video-time progress; `range=` keeps its existing priority over `start=`/`end=`.

To keep the final weight after the ramp, add a fixed-weight tag for the remaining
duration, for example:

```text
<lora:myLora:time=0-10:blend=0.5-2>
<lora:myLora:2:time=10-20>
```

The H3 MLP token path applies the interpolated weight directly at each selected
video slice. LTX and the H3 fallback interpolate **predictions made at the two
endpoint weights**. That approximation is not the same as evaluating the model
at every intermediate weight. It needs the endpoint predictions plus a base
prediction when audio or out-of-window video requires one, rather than a model
pass for every slice. Overlapping ramps require endpoint combinations and can
be substantially slower. The visible transition still follows the scene behavior
described above; this feature needs verification in your ComfyUI workflow.

### LoRA Matching and Prioritization

When you use a tag like `<lora:myLora>`, the node searches for the best matching LoRA file. If the name is not exact, it uses a scoring system to find the most likely candidate. Here is the order of priority:

1.  **Exact Match:** An exact filename match (e.g., `myLora.safetensors`) is always preferred.
2.  **Numbered Versions:** It intelligently handles numbered versions (e.g., `myLora-1`, `myLora-2`). If you ask for `myLora-2`, it will prioritize that file. If it can't find it, it will look for other numbered versions or the base `myLora` file.
3.  **Prefix Match:** It will look for files that start with your requested name (e.g., `myLoraAndMore.safetensors`).
4.  **Contains Match:** It will look for files that contain your requested name anywhere in the filename.
5.  **Path Priority:** Files located closer to the root of your LoRA folders are given a slight priority boost over files in deep subdirectories.


![image](https://github.com/user-attachments/assets/595fdb36-1442-4c0a-abf4-b1779674c515)

Route the model and clip through the node.

Use the output [STRING] to have the prompt without the `<lora::>`-tags.
