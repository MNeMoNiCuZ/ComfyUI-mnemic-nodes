# 🎲 Ideogram 4 Random Prompter

**Experimental.** Generates a complete random Ideogram 4 caption: a scattered
set of regions, each described with words pulled live from the `wonderwords`
dictionary, plus random style, lighting, medium, palette and arrangement.

Nothing here is curated — every content word is a dictionary word. It is a
generator to explore with, not a prompt assistant. Everything stays visible on
the node for that reason; nothing is hidden behind Advanced.

Requires the `wonderwords` package.

## Inputs

Canvas:

- **seed** — Same seed and settings give the exact same caption, preview and
  boxes.
- **width** / **height** — Canvas size in pixels; Ideogram 4 prefers multiples
  of 16.

How many regions:

- **region_count_min** / **region_count_max** — The count is rolled between
  them, inclusive. Set both the same for a fixed count.
- **background_weight** / **large_weight** / **medium_weight** /
  **small_weight** — Relative likelihood of each size tier. Background blocks
  cover 70%+ of the canvas; large is ~34-62% per axis, medium ~17-40%, small
  ~5-17%. All four are summed and each region picks a tier proportionally; all
  zero falls back to equal weighting.

Wording:

- **word_length_bias** — Preferred word length in characters. `0` means no
  preference.
- **word_length_randomness** — Spread around that length. Ignored when bias is
  0.
- **scene_framing** — `pure` gives each region a bare word list, which Ideogram
  tends to render as a collage of separate items. `scene` weaves the same words
  into one sentence with articles and spatial connectors, which reads as a
  single coherent scene — this is what makes `photograph` actually look like a
  photograph. Connector words do not count toward the word budget.
- **region_word_min** / **region_word_max** — Content words per region.

Regions:

- **freeform_chance** — Chance a region drops its bounding box and blends
  softly into the scene instead of sitting in a hard rectangle. Freeform
  regions are excluded from the bbox output.
- **text_region_min** / **text_region_max** — How many regions are rendered as
  in-image text instead of objects. An exact count, clamped to the total region
  count.
- **element_palette_chance** — Chance a region carries its own colour sub-set
  instead of the image palette. No effect when `color_palette` is `none`.

Style:

- **medium** — `photograph` writes a `photo` style key with focal length and
  aperture; anything else writes an `art_style` key.
- **color_palette** — Palette family, mirroring 🎨 Colorful Starting Image.
  `none` emits no palette at all and lets Ideogram choose.
- **color_harmony** — Relationship between the palette colours. Ignored when
  the palette is `none`.
- **positioning_bias** — Where regions cluster. Ignored unless `arrangement` is
  `none`.
- **arrangement** — `spiral`, `burst` or `grid` structured placement; overrides
  `positioning_bias`.

Description:

- **description_length** — Target word count for the auto-generated high-level
  description.
- **description_override** — Use this text verbatim as the high-level
  description; the prefix and length settings are then ignored.
- **description_prefix** — Prepended to the generated high-level description.
- **description_background_prefix** — Prepended to the generated background
  description.

## Outputs

Same shape as 🧩 Ideogram 4 Prompt Builder:

- **prompt** — The caption as JSON text.
- **preview** — Rendered preview of the regions.
- **bboxes** — Region boxes in pixels, freeform regions excluded.
- **width** / **height** — Passed through.

## Tip

For something that looks like a real photo rather than an asset sheet:
`scene_framing` on, `medium` = `photograph`, a low region count, and high
background/large weights.
