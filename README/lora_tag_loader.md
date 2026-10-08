# 🏷️ LoRA Loader Prompt Tags

Loads LoRA models using tags in the prompt.

### Syntax and Weights

The basic syntax is `<lora:loraName:strength>`.

-   The default strength is `1.0` if not specified (e.g., `<lora:myLora>`).
-   A strength of `0` disables the LoRA for both model and CLIP unless a separate CLIP weight is specified.
-   If an invalid strength is provided (e.g., non-numeric text), it will also be treated as `1.0`.

#### CLIP Weight
You can provide a separate weight for the CLIP model.

-   **Syntax**: `<lora:loraName:model_weight:clip_weight>`
-   If the CLIP weight is omitted, it defaults to the model's weight.
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
