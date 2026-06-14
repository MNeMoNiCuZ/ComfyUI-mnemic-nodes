# 🎲 Ideogram 4 Random Prompter

An experimental companion to the **Ideogram 4 Prompt Builder**. Instead of drawing regions by hand, this node automatically generates a complete composition from scratch by scattering weighted-random regions across the canvas and filling each with descriptions built from real dictionary words.

<img width="2162" height="580" alt="image" src="https://github.com/user-attachments/assets/a1f90b99-1150-476a-9349-38640cfc63c8" />

<img width="2434" height="1358" alt="image" src="https://github.com/user-attachments/assets/462a032f-79d6-458e-b4eb-66eb2c27320c" />


Requires the `wonderwords` package:

```bash
pip install wonderwords
```

---

## What makes this node unique

Every descriptive word in the caption is pulled **live from the wonderwords dictionary** — there are no hardcoded or curated word lists. This means every run produces genuinely novel, varied compositions:

- **Random region count** — minimum to maximum regions, weighted across size tiers.
- **Random placement** — centers scattered, clustered, arranged in spirals/bursts/grids, or pushed to compass edges.
- **Random sizes** — background (70–100% canvas area), large (34–62%), medium (17–40%), small (5–17%).
- **Random descriptions** — each region gets a randomized content-word budget filled from the dictionary.
- **Random styling** — aesthetics, lighting, medium, color palette, and harmony are all randomized per run.
- **Scene framing** — descriptions can be bare words or woven together with articles and spatial connectors into one coherent sentence.
- **Freeform regions** — some regions can drop their hard bounding boxes to blend softly into the scene.
- **Text regions** — some elements can render as actual in-image text (drawn words) instead of objects.

The output matches the **Ideogram 4 Prompt Builder** exactly — same JSON format, same preview, same bounding-box style — so the two nodes can be swapped freely or used side by side.

---

## Canvas settings

| Setting  | Type | Description                                                                                                     |
| -------- | ---- | --------------------------------------------------------------------------------------------------------------- |
| `width`  | INT  | Canvas width in pixels. Ideogram 4 prefers multiples of 16. Affects aspect ratio and the pixel grid for bboxes. |
| `height` | INT  | Canvas height in pixels. Ideogram 4 prefers multiples of 16.                                                    |

---

## Core randomization: regions and size tiers

The node randomly chooses how many regions to generate, then weighs each one across four size tiers.

| Setting             | Type  | Default | Description                                                                                                                       |
| ------------------- | ----- | ------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `seed`              | INT   | 0       | Random seed. The same seed + same settings always produce identical output. Change the seed to roll a completely new composition. |
| `region_count_min`  | INT   | 10      | Minimum number of element regions (inclusive). Set equal to max for a fixed count.                                                |
| `region_count_max`  | INT   | 20      | Maximum number of element regions (inclusive).                                                                                    |
| `background_weight` | FLOAT | 0.4     | Likelihood that any region is a **background** tier (covers ≥70% of canvas area, acts as a base layer).                           |
| `large_weight`      | FLOAT | 0.6     | Likelihood that a region is **large** (34–62% of canvas per axis).                                                                |
| `medium_weight`     | FLOAT | 0.4     | Likelihood that a region is **medium** (17–40% of canvas per axis).                                                               |
| `small_weight`      | FLOAT | 0.2     | Likelihood that a region is **small** (5–17% of canvas per axis).                                                                 |

All four weights are summed and each region picks a tier proportionally. Set all to 0 to get equal weighting (25% each).

---

## Region descriptions: words and content budgets

Each region gets a **content-word budget** — a random integer between min and max, filled with real dictionary words pulled live.

| Setting                  | Type | Default | Description                                                                                                                                                          |
| ------------------------ | ---- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `region_word_min`        | INT  | 5       | Minimum content words per region. Connector/article words (in scene mode) are NOT counted.                                                                           |
| `region_word_max`        | INT  | 15      | Maximum content words per region.                                                                                                                                    |
| `word_length_bias`       | INT  | 0       | Preferred dictionary word length (characters). 0 = no preference; >0 = bias toward that length. Example: 4 favours short punchy words, 11 favours long ornate words. |
| `word_length_randomness` | INT  | 2       | Spread around `word_length_bias`. Words are drawn from `[bias - this, bias + this]`. Ignored when bias is 0. Example: bias 8, randomness 2 → words 6–10 chars.       |

---

## Scene framing: pure vs. scene mode

### OFF (pure mode)

Each region's description is a bare comma-separated list of dictionary words:

```
vivid tower, hollow stone.
```

Maximum randomness, but Ideogram tends to render this as a collage or asset sheet of separate items.

### ON (scene mode)

The same dictionary words are woven together with **articles** (a / an) and **spatial connectors** (beside, near, behind, above, below, etc.) into one continuous sentence:

```
a vivid tower beside a hollow stone against an amber cloud.
```

This tells Ideogram it is **one coherent scene**, so a photograph actually looks like a photograph instead of a grid. The connector and article words are structural and do NOT count toward `region_word_min/max`.

| Setting         | Type    | Default | Description                                               |
| --------------- | ------- | ------- | --------------------------------------------------------- |
| `scene_framing` | BOOLEAN | True    | False = pure (bare words); True = scene (woven sentence). |

---

## Placement and arrangement

Regions are positioned either by a **positioning bias** (scattered, center-weighted, edge-weighted, grid-aligned, or a compass direction) or by a **structured arrangement** (spiral, burst, grid).

| Setting            | Type | Default     | Description                                                                                                                                                                                                                                    |
| ------------------ | ---- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `positioning_bias` | ENUM | `scattered` | How regions tend to cluster: `scattered` (anywhere), `center_weighted`, `edge_weighted`, `grid_aligned`, `random_weighted`, or compass directions (`north`, `south`, `east`, `west`, and diagonals). Ignored when `arrangement` is not `none`. |
| `arrangement`      | ENUM | `none`      | Structured placement pattern for region centres: `none` (use positioning_bias), `spiral` (wind outward), `burst` (explode from center), `grid` (orderly tile). Overrides positioning_bias when not `none`.                                     |

---

## Special region modes

### Freeform regions

Some regions can drop their hard bounding box and blend softly into the scene instead of rendering as a pinned rectangle. This removes the "cut-out collage" look.

| Setting           | Type  | Default | Description                                                                                                                                                                                                                                                                     |
| ----------------- | ----- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `freeform_chance` | FLOAT | 0.0     | Per-region probability that a region becomes freeform (no hard bbox). Freeform regions are drawn dashed in the preview but excluded from the bounding-box output (they have no fixed location). 0.0 = every element keeps a hard box; 1.0 = nothing is boxed (fully painterly). |

### Text regions

Some regions can render as actual in-image text (a dictionary word drawn into the picture) instead of an object.

| Setting           | Type | Default | Description                                                                                                                                                                                            |
| ----------------- | ---- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `text_region_min` | INT  | 0       | Minimum number of regions rendered as in-image TEXT. The text count is a random integer between min and max (clamped to the total region count). This is an EXACT count, not a per-region probability. |
| `text_region_max` | INT  | 2       | Maximum number of regions rendered as in-image TEXT. Example: min 1, max 2 → always 1 or 2 text words in the image.                                                                                    |

---

## Styling: medium, palette, and harmony

Every run randomizes the image medium, color palette family, and color-harmony rule.

| Setting                  | Type  | Default      | Description                                                                                                                                                                                                                                                                                |
| ------------------------ | ----- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `medium`                 | ENUM  | `photograph` | Image medium (an Ideogram 4 schema value). `photograph` emits a `photo` style key (focal length / aperture); every other medium emits an `art_style` key. `random` picks one per run. Options: `photograph`, `illustration`, `3d_render`, `painting`, `graphic_design`.                    |
| `color_palette`          | ENUM  | `none`       | Colour palette family for the image-level palette. `none` = emit no palette; `random_color` = any RGB; themed options: `muted`, `grayscale`, `binary`, `neon`, `pastel`, `colorized` (grayscale tinted with one hue); `random` = pick one family per run.                                  |
| `color_harmony`          | ENUM  | `none`       | Colour-harmony rule applied to generated colours: `none` (unrelated), `complementary` (two opposite hues), `analogous` (neighbouring), `triadic` (three evenly spaced), `tetradic` (four evenly spaced), `random` (pick one per run). Ignored when `color_palette` is `none`.              |
| `element_palette_chance` | FLOAT | 0.0          | Per-region probability that a region carries its OWN small colour palette (a subset of the image-level palette) instead of inheriting the global one. 0.0 = all elements share the image palette; 1.0 = every element gets its own colour sub-set. Ignored when `color_palette` is `none`. |

---

## High-level description (image overview)

The caption includes a one-line `high_level_description` (an overview of the whole image). This can be auto-generated or fully overridden.

| Setting                | Type   | Default                     | Description                                                                                                                                                                              |
| ---------------------- | ------ | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `description_override` | STRING | ``                          | **Full replacement** for the high_level_description. When non-empty, this exact string is used verbatim and generation is skipped. Leave blank to auto-generate.                         |
| `description_prefix`   | STRING | `A close-up photography of` | PREFIX prepended to the auto-generated description. Ignored when `description_override` is set. Final value: `<prefix> <generated words>`.                                               |
| `description_length`   | INT    | 35                          | Target length (words) for the auto-generated description. The generator keeps adding dictionary word-groups until reaching ~this many words. Ignored when `description_override` is set. |

---

## Background description

The `compositional_deconstruction` block includes a `background` field that sets a base scene layer.

| Setting                         | Type   | Default                                    | Description                                                                                                                                          |
| ------------------------------- | ------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `description_background_prefix` | STRING | `an environment photography background of` | PREFIX prepended to the auto-generated background description. Leave blank for a fully random background. Final value: `<prefix> <generated words>`. |

---

## Inputs summary

### Required

- `seed`, `width`, `height`
- `region_count_min`, `region_count_max`
- `background_weight`, `large_weight`, `medium_weight`, `small_weight`
- `word_length_bias`, `word_length_randomness`
- `scene_framing`, `region_word_min`, `region_word_max`
- `freeform_chance`, `text_region_min`, `text_region_max`, `element_palette_chance`
- `medium`, `color_palette`, `color_harmony`, `positioning_bias`, `arrangement`

### Optional

- `description_length`, `description_override`, `description_prefix`, `description_background_prefix`

---

## Outputs

| Output    | Type         | Description                                                                                                                                                  |
| --------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `prompt`  | STRING       | The assembled Ideogram 4 caption JSON, ready to pass to an API node.                                                                                         |
| `preview` | IMAGE        | Rendered preview of all regions (solid rects for boxed regions, dashed rects for freeform).                                                                  |
| `bboxes`  | BOUNDING_BOX | Pixel-space bounding boxes `{x, y, width, height}` for each **boxed** region (freeform regions are excluded). In the format expected by SAM3 and crop nodes. |
| `width`   | INT          | Canvas width (pass-through).                                                                                                                                 |
| `height`  | INT          | Canvas height (pass-through).                                                                                                                                |

The `bboxes` output uses per-frame nesting (`list[list[dict]]`) — the standard shape that SAM3 and other bounding-box consumers expect.

---

## JSON caption structure

The node outputs the same Ideogram 4 caption JSON as the **Prompt Builder**:

```json
{
    "high_level_description": "A close-up photography of ...",
    "style_description": {
        "aesthetics": "vivid mysterious, ...",
        "lighting": "soft luminous, ...",
        "photo": "85mm, f/5.6",
        "medium": "photograph",
        "color_palette": ["#RRGGBB", ...]
    },
    "compositional_deconstruction": {
        "background": "an environment photography background of ...",
        "elements": [
            {
                "type": "obj",
                "bbox": [ymin, xmin, ymax, xmax],
                "desc": "a vivid tower beside ...",
                "color_palette": ["#RRGGBB", ...]
            },
            {
                "type": "text",
                "bbox": [ymin, xmin, ymax, xmax],
                "text": "TOWER",
                "desc": "..."
            }
        ]
    }
}
```

- `bbox` coordinates are on a **0–1000 grid** as `[ymin, xmin, ymax, xmax]`.
- `style_description` is omitted when `color_palette` is `none`.
- `color_palette` is omitted from an element when no colours are set.
- Freeform elements (with `nobbox=True` in generation) are omitted from the elements array.

---

## Spatial connectors (scene framing mode)

When `scene_framing` is ON, the node weaves descriptions together with these structural words (which do NOT count toward content-word budgets):

> beside, near, behind, before, above, below, amid, atop, against, beyond, framing, facing

These are randomly selected to join phrases into one coherent sentence.

---

## Example workflows

### High-quality realistic photograph

- `scene_framing = ON`
- `medium = photograph`
- `region_count_min = 3`, `region_count_max = 6` (sparse)
- `background_weight = 0.8`, `large_weight = 0.2`, `medium_weight = 0`, `small_weight = 0` (mostly large shapes)
- `freeform_chance = 0.3` (some soft blending)
- `text_region_min = 0`, `text_region_max = 0` (no text overlays)

### Busy abstract collage

- `scene_framing = OFF` (pure mode for maximum randomness)
- `region_count_min = 25`, `region_count_max = 40` (dense)
- `medium = graphic_design`
- `arrangement = grid` (orderly)
- `color_palette = neon`, `color_harmony = tetradic` (vivid 4-colour scheme)
- `text_region_min = 2`, `text_region_max = 4` (lots of text elements)

### Surreal painted scene

- `scene_framing = ON`
- `medium = painting`
- `arrangement = spiral` (energetic)
- `positioning_bias = center_weighted` (elements cluster toward the middle)
- `freeform_chance = 0.6` (lots of soft blending)
- `color_palette = pastel`, `color_harmony = analogous` (soft, harmonious)
