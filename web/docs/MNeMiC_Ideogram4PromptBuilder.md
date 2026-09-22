# 🧩 Ideogram 4 Prompt Builder w. String Inputs

A visual editor for Ideogram 4's structured JSON caption format. Draw regions
on a canvas, describe each one, and the node assembles the caption JSON.

Adapted from KJNodes' `Ideogram4PromptBuilderKJ` by kijai, with per-region
string inputs added.

## Canvas controls

- **Drag on empty canvas** — draw a new region
- **+ Region** — add a region without drawing
- **Click a region** — select it and show its fields
- **Drag inside / on an edge or corner** — move / resize
- **Delete** or **Backspace** — delete the selected region
- **Ctrl+C / Ctrl+V** — copy / paste a region
- **Ctrl+D** — duplicate
- **Escape** — cancel the current draw or edit

## Inputs

- **width** / **height** — Canvas aspect and the pixel grid the boxes are
  measured against. Ideogram 4 wants multiples of 16.
- **high_level_description** *(optional)* — One line describing the whole
  image. Omitted from the JSON when blank.
- **background** *(optional)* — The scene background description.
- **style** *(optional)* — `none` omits the style block; `photo` and
  `art_style` choose which style key is written.
- **photo** / **art_style** *(optional)* — The descriptor for the chosen style.
- **aesthetics** / **lighting** / **medium** *(optional)* — Extra style
  descriptors. Blank ones are omitted.
- **image** *(optional)* — A reference image shown behind the editor canvas.
- **import_json** *(optional)* — A full caption JSON. When connected it loads
  into the editor on the next run; the output always reflects the editor, never
  the raw input.
- **style_palette_data** / **elements_data** — Serialized editor state, managed
  by the node's UI. Do not edit these by hand.
- **region_0**, **region_1**, … — One string input per region, added
  automatically. A connected, non-empty string overrides that region's
  description, which is how you drive a region from a wildcard or an LLM node.

## Outputs

- **prompt** — The caption as JSON text.
- **preview** — A rendered preview of the regions, their text and their
  palettes.
- **bboxes** — Region boxes in pixels as `{x, y, width, height}`, nested one
  list per frame. Freeform regions are excluded.
- **width** / **height** — Passed through.

## Notes

In the JSON, `bbox` is normalised to a 0-1000 grid as
`[ymin, xmin, ymax, xmax]`; `width` / `height` only set the aspect ratio.
Regions marked freeform carry no box, which lets Ideogram blend them into the
scene instead of pinning them to a rectangle — they show as dashed in the
preview.
