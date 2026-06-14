# Prompting Guide

Ideogram 4 is trained exclusively on **structured JSON captions** (represented as string type). While the
model can accept plain-text prompts, providing a JSON object that follows the
caption schema gives significantly better results, especially for
controllability, spatial layout, and style fidelity.

## Plain-text vs. JSON prompts

You can pass in plain-text prompts directly to the model and it will work. The
sampling parameters come from a named preset in `ideogram4.PRESETS` (the same
ones `run_inference.py` exposes via `--sampler-preset`), unpacked into the
`pipe()` call:

```python
from ideogram4 import PRESETS

preset = PRESETS["V4_QUALITY_48"]
images = pipe(
  "a golden retriever on a skateboard",
  height=1024,
  width=1024,
  num_steps=preset.num_steps,
  guidance_schedule=preset.guidance_schedule,
  mu=preset.mu,
  std=preset.std,
)
```


But for higher quality image generations and more control, pass a JSON string as the prompt:

```python
import json
from ideogram4 import PRESETS

caption = {
  "high_level_description": "A golden retriever riding a skateboard down a sunny sidewalk.",
  "style_description": {
    "aesthetics": "warm, playful, vibrant",
    "lighting": "bright afternoon sunlight, long soft shadows",
    "photo": "shallow depth of field, eye-level, 85mm lens",
    "medium": "photograph",
    "color_palette": ["#F5C542", "#87CEEB", "#4A4A4A", "#FFFFFF", "#2E8B57"]
  },
  "compositional_deconstruction": {
    "background": "A sun-drenched suburban sidewalk lined with green hedges and a white picket fence. Dappled light filters through overhead trees.",
    "elements": [
      {"type": "obj", "bbox": [200, 300, 800, 900], "desc": "A golden retriever with a fluffy coat, standing on a red skateboard with all four paws. Its tongue is out and ears are flapping in the wind."},
      {"type": "obj", "bbox": [250, 750, 750, 950], "desc": "A worn red skateboard with black wheels rolling along the concrete sidewalk."}
    ]
  }
}

preset = PRESETS["V4_QUALITY_48"]
images = pipe(
  json.dumps(caption, separators=(",", ":"), ensure_ascii=False),
  height=1024,
  width=1024,
  num_steps=preset.num_steps,
  guidance_schedule=preset.guidance_schedule,
  mu=preset.mu,
  std=preset.std,
)
```

## Magic prompt

Writing these captions by hand is optional. *Magic prompt* uses an LLM to expand
a plain-text prompt into a full structured caption for you, so you get the
quality of a JSON prompt from a casual one. It is enabled by default in
`run_inference.py`; you can also call it directly:

```python
import os
from ideogram4 import ClaudeOpusMagicPromptV1, PRESETS

magic = ClaudeOpusMagicPromptV1(api_key=os.environ["MAGIC_PROMPT_API_KEY"])
caption = magic.expand("a golden retriever on a skateboard", aspect_ratio="1:1")
preset = PRESETS["V4_QUALITY_48"]
images = pipe(
  caption,
  height=1024,
  width=1024,
  num_steps=preset.num_steps,
  guidance_schedule=preset.guidance_schedule,
  mu=preset.mu,
  std=preset.std,
)
```

The package ships three configurations, registered by name in
`ideogram4.MAGIC_PROMPTS` (the keys `run_inference.py` accepts via
`--magic-prompt-model`):

| Config class | Registry key | Backend |
| :--- | :--- | :--- |
| `Ideogram4MagicPromptV1` | `ideogram-4-v1` | Ideogram's hosted magic-prompt API (free; reads `IDEOGRAM_API_KEY`) |
| `ClaudeOpusMagicPromptV1` | `claude-opus-v1` | [OpenRouter](https://openrouter.ai) (reads `MAGIC_PROMPT_API_KEY`) |
| `ClaudeSonnetMagicPromptV1` | `claude-sonnet-v1` | [OpenRouter](https://openrouter.ai) (reads `MAGIC_PROMPT_API_KEY`) |

`ideogram-4-v1` is the default and is **free**. It runs the expansion
server-side, so there is no local model or system prompt involved — it just needs
an Ideogram API key (get one at
[developer.ideogram.ai](https://developer.ideogram.ai)). The `claude-*`
configurations instead send one of our open-source system prompt to an OpenRouter model;
select one with `--magic-prompt-model` and export `MAGIC_PROMPT_API_KEY`:

```bash
python run_inference.py \
  --prompt "an isometric illustration of a tiny city floating in the clouds" \
  --output out.png \
  --quantization "nf4" \
  --magic-prompt-model claude-opus-v1 \
  --magic-prompt-key "$MAGIC_PROMPT_API_KEY"
```

See the README's [CLI](../README.md#cli) section for the rest of the flags.

Our magic-prompt system prompts are **open source** (they ship in
`src/ideogram4/magic_prompt_system_prompts/`), so you're also welcome to
construct the caption with any system prompt and LLM of your choosing.

**A few caveats:**

- At Ideogram we've tested this magic prompt with **Claude Opus**. You're welcome
  to implement your own `MagicPrompt` configurations and/or drive a different LLM
  with our system prompt, but those paths aren't tested by us and quality may
  vary.
- The magic prompt shipped here is **not** the same magic prompt used in
  production at [Ideogram.ai](https://ideogram.ai) — results will differ from the
  hosted product (including the `ideogram-4-v1` API).

## JSON caption schema

> **Note:** Following this schema is **not required** — the model accepts any
> string as a prompt. The schema below describes the exact structure the model
> was trained on, and matching it minimizes train/eval mismatch so the model
> generates closer to its full quality. Treat the "required" / "must" language
> in the rest of this section as the format the [`CaptionVerifier`](../src/ideogram4/caption_verifier.py)
> checks against, not as a hard pipeline constraint. Deviating from the schema
> is allowed; it just means you're sampling outside the training distribution.

The full caption schema has three top-level fields:

1. `high_level_description` — optional string, but strongly recommended.
2. `style_description` — optional object.
3. `compositional_deconstruction` — **required** object.

`compositional_deconstruction` must always be present. Within it, both
`background` and `elements` are required.

### `high_level_description`

A one- or two-sentence summary of the entire image. Strongly recommended in every prompt.

```json
"high_level_description": "A medium-shot photograph of a barista pouring latte art in a cozy cafe."
```

### `style_description`

Controls the visual style, lighting, medium, and color palette.

`style_description` must contain **exactly one** of:

- `photo` — for photographic captions (paired with `medium: "photograph"`).
- `art_style` — for non-photographic captions (illustration, painting, 3D render, etc.).

`aesthetics`, `lighting`, and `medium` are also required when `style_description` is present. `color_palette` is optional.

**Key order is strict** and depends on which of `photo` / `art_style` is used:

| Caption type | Required key order |
| :----------- | :----------------- |
| Photo (uses `photo`) | `aesthetics`, `lighting`, `photo`, `medium`, `color_palette` |
| Non-photo (uses `art_style`) | `aesthetics`, `lighting`, `medium`, `art_style`, `color_palette` |

`color_palette` is the only field in this list that may be omitted; if it is included it must remain in the final position.

Field descriptions:

| Field | Type | Description |
| :---- | :--- | :---------- |
| `aesthetics` | string | Aesthetic keywords (e.g. "moody, cinematic, desaturated") |
| `lighting` | string | Lighting description (e.g. "golden hour, rim light, dramatic shadows") |
| `photo` | string | Camera/lens details for photographic outputs (e.g. "35mm, f/1.4, bokeh"). Use this OR `art_style`, not both. |
| `medium` | string | Medium type: `"photograph"`, `"illustration"`, `"3d_render"`, `"painting"`, `"graphic_design"`, etc. |
| `art_style` | string | Art style description for non-photo captions (e.g. "flat vector illustration, bold outlines"). Use this OR `photo`, not both. |
| `color_palette` | list[str] | Hex color codes that steer the image's dominant colors. Up to 16 entries. |

### `compositional_deconstruction`

Provides fine-grained spatial control over the image layout using bounding
boxes and per-element descriptions. Both fields below are required.

| Field | Type | Description |
| :---- | :--- | :---------- |
| `background` | string | Description of the background/environment (required) |
| `elements` | list[dict] | List of elements with optional bounding boxes (required) |

`background` must come before `elements`.

Each element in `elements` must follow a fixed **key order** depending on its
type. `bbox` and `color_palette` are optional within an element; if present they
must appear in the positions shown below.

| Type | Required key order |
| :--- | :----------------- |
| `"obj"` | `type`, `bbox`, `desc`, `color_palette` |
| `"text"` | `type`, `bbox`, `text`, `desc`, `color_palette` |

Field descriptions:

| Field | Type | Description |
| :---- | :--- | :---------- |
| `type` | string | `"obj"` for objects/subjects, `"text"` for in-image text |
| `bbox` | list[int] | `[y_min, x_min, y_max, x_max]` in normalized `0–1000` coordinates (origin at top-left). Optional. |
| `desc` | string | Detailed description of the element |
| `text` | string | (only for `type: "text"`) The literal text to render |
| `color_palette` | list[str] | Optional per-element palette. Up to 5 hex entries. |

**Key ordering matters.** The model was trained on JSON with a consistent key
order, so maintaining it improves generation quality. The pipeline runs
[`CaptionVerifier`](../src/ideogram4/caption_verifier.py) on every prompt and emits
warnings for unknown keys, missing required keys, or out-of-order keys.

**Hex color format.** Colors in `color_palette` must be uppercase
`#RRGGBB` strings (e.g. `#1B1B2F`, not `#1b1b2f` or `#fff`).

**Encoding.** When serializing with Python's `json` module, pass
`separators=(",", ":")` and `ensure_ascii=False`.
`CaptionVerifier` warns when it detects `\uXXXX` escapes with no literal
non-ASCII characters in the raw text.

## Color palette conditioning

One of Ideogram 4's distinctive features is **color palette control**. By
providing a `color_palette` array of hex colors in `style_description`, you
can steer the dominant colors of the generated image.

```json
"style_description": {
  "aesthetics": "moody, cinematic",
  "lighting": "low-key, deep shadows",
  "photo": "35mm, f/1.4",
  "medium": "photograph",
  "color_palette": ["#1B1B2F", "#162447", "#1F4068", "#E43F5A", "#F5F5F5"]
}
```

Tips for effective color palette use:

- **Up to 16 colors** in `style_description.color_palette` for the overall
  image palette, and **up to 5 colors** per element in
  `compositional_deconstruction.elements[*].color_palette`.
- **Include background colors** — if you want a dark background, include the
  dark hex in the palette.
- **Contrast pairs** — include both your highlight and shadow colors for more
  controlled lighting.
- **Uppercase hex only** — `#RRGGBB` form, no shorthand.

### Example: warm sunset palette

```json
{
  "high_level_description": "A lone sailboat on calm water at sunset.",
  "style_description": {
    "aesthetics": "serene, warm, golden hour",
    "lighting": "golden hour backlighting, warm atmospheric haze",
    "photo": "wide angle, f/8, long exposure",
    "medium": "photograph",
    "color_palette": ["#FF6B35", "#F7C59F", "#004E89", "#1A659E", "#2B2D42"]
  },
  "compositional_deconstruction": {
    "background": "A calm ocean stretching to a low horizon, sky washed in orange and pink with thin wisps of cloud.",
    "elements": [
      {"type": "obj", "desc": "A single sailboat with a white triangular sail, silhouetted against the setting sun."}
    ]
  }
}
```


### Example: corporate design palette

```json
{
  "high_level_description": "A clean, modern business card layout for a tech company.",
  "style_description": {
    "aesthetics": "minimal, professional, geometric",
    "lighting": "even, diffuse studio lighting",
    "medium": "graphic_design",
    "art_style": "flat vector design, generous whitespace, sans-serif typography",
    "color_palette": ["#FFFFFF", "#F0F0F0", "#333333", "#0066FF", "#00CC88"]
  },
  "compositional_deconstruction": {
    "background": "A solid off-white card surface with subtle paper texture.",
    "elements": [
      {"type": "text", "text": "ACME TECH", "desc": "Bold dark grey sans-serif company name across the upper third of the card."},
      {"type": "text", "text": "hello@acme.tech", "desc": "Small blue sans-serif contact email near the bottom of the card."}
    ]
  }
}
```



## Full example

```json
{
  "high_level_description": "A medium-shot photograph of Formula 1 driver Max Verstappen wearing his Red Bull Racing racing suit and cap, smiling as he holds his racing helmet and talks to a man in a white shirt and black vest at a race track.",
  "style_description": {
    "aesthetics": "saturated primary colors, rule of thirds, joyful and triumphant",
    "lighting": "overcast daylight, diffused, soft subtle shadows",
    "photo": "shallow depth of field, sharp focus, eye-level, telephoto",
    "medium": "photograph"
  },
  "compositional_deconstruction": {
    "background": "The background is an out-of-focus racing paddock or track environment. Several blurred figures are visible, including one in an orange shirt. A purple and white structure with a red 'F1' logo stands on the left. The scene is outdoors with daylight, though the sky is not visible.",
    "elements": [
      {"type": "obj", "bbox": [55, 642, 1000, 937], "desc": "An older man standing in profile, facing left toward Max Verstappen. He has grey hair and fair skin. He is wearing a white long-sleeved button-down shirt with a navy blue quilted vest over it. He has a slight smile."},
      {"type": "obj", "bbox": [34, 137, 1000, 617], "desc": "Max Verstappen, a fair-skinned male Formula 1 driver, positioned in the center. He is facing forward with a joyful expression and a slight smile. He wears a navy blue Red Bull Racing team uniform with numerous sponsor logos and a matching baseball cap with the number '1'. He is holding a white and red racing helmet in his hands. He has a silver watch on his left wrist."},
      {"type": "obj", "bbox": [422, 212, 792, 452], "desc": "Max Verstappen's racing helmet, held in front of his chest. It features a white, red, and yellow design with the Red Bull logo and the 'Player 0.0' branding. The visor is clear and open."},
      {"type": "text", "bbox": [657, 0, 755, 142], "text": "F1", "desc": "Large, stylized red logo on a black and purple background in the lower left."},
      {"type": "text", "bbox": [768, 0, 818, 147], "text": "Formula 1\nWorld Championship™", "desc": "Small white sans-serif text below the F1 logo on the left side."},
      {"type": "text", "bbox": [78, 447, 117, 510], "text": "ORACLE\nRed Bull\nRacing", "desc": "Very small white and orange logo on the front of the navy blue cap."},
      {"type": "text", "bbox": [78, 417, 120, 440], "text": "1", "desc": "Bold red numeral '1' on the front left side of the navy blue cap."},
      {"type": "text", "bbox": [332, 442, 363, 483], "text": "Red Bull", "desc": "Small yellow and red text logo on the collar of the uniform."},
      {"type": "text", "bbox": [373, 490, 423, 532], "text": "RAUCH", "desc": "Small yellow and blue logo on the right chest of the uniform."},
      {"type": "text", "bbox": [422, 473, 500, 532], "text": "BYBIT\nHONDA", "desc": "Medium-sized white sans-serif text on the right chest of the uniform."},
      {"type": "text", "bbox": [410, 203, 442, 257], "text": "RAUCH", "desc": "Small yellow logo on the left upper arm of the uniform."},
      {"type": "text", "bbox": [530, 448, 627, 510], "text": "Red Bull", "desc": "Medium red text logo on the right side of the torso, part of the Red Bull graphic."},
      {"type": "text", "bbox": [680, 417, 768, 523], "text": "Red Bull", "desc": "Large red text logo across the lower torso of the uniform."},
      {"type": "text", "bbox": [797, 475, 815, 518], "text": "MAX", "desc": "Small white text next to a Dutch flag on the belt area of the uniform."},
      {"type": "text", "bbox": [558, 317, 715, 355], "text": "Player 0.0", "desc": "Black sans-serif text on a white band on the racing helmet."},
      {"type": "text", "bbox": [560, 800, 582, 835], "text": "IA.COM", "desc": "Small blue sans-serif text on the right sleeve of the white shirt."},
      {"type": "text", "bbox": [968, 8, 997, 332], "text": "© Anadolu Agency via Getty Images", "desc": "Small white watermark text in the bottom left corner."}
    ]
  }
}
```

## Safety filter

NSFW prompts are blocked. Instead of an image, the model returns a gray screen
with the text "Image blocked by safety filter". False positive rates for safety
is higher for non-json like prompts. We are aware that this is an issue an we may
make a future checkpoint update to improve it.

# Congratulations!

You are now a certified Ideogram 4 prompter!

With structured JSON captions, you have fine-grained control over composition,
color palettes, typography, and spatial layout — capabilities that go far
beyond what plain-text prompts can express!
We'd love to see what you create :-)
Share your results, experiments, and creative discoveries with the community,
especially the unexpected ones. Tag us on social media or open a discussion on
the repo. Happy generating!
