# 🧩 Ideogram 4 Prompt Builder

A visual bounding-box editor that assembles the structured JSON caption format required by **Ideogram 4**. Draw regions directly on the canvas, configure each region's type, description, and color palette, and the node outputs a ready-to-use caption JSON.

Adapted from [kijai's Ideogram4PromptBuilderKJ](https://github.com/kijai/ComfyUI-KJNodes), converted to the classic node API and extended with **dynamic per-region STRING input pins**.

<img width="1611" height="530" alt="image" src="https://github.com/user-attachments/assets/2da9abb0-60db-4d68-a6b2-bea3dc183623" />

---

## What makes this node unique

Every region you draw on the canvas gets its own dedicated **`region_N` input pin** on the node. When you connect a string to `region_1`, that string overrides the description of region 1 at run time — no manual copy-pasting required. This means you can wire wildcard processors, LLM nodes, or any other string source directly into individual regions to drive their descriptions dynamically.

- Add a region → a new `region_N` pin appears on the node immediately.
- Remove a region → the corresponding pin is removed and the remaining pins are renumbered.
- Leave a pin unconnected → the description typed in the panel is used as-is.

---

## Editor overview

The editor is a fully interactive canvas embedded in the node:

| Control | Action |
|---|---|
| Drag on empty canvas | Draw a new region |
| Click a region | Select it |
| Alt-click overlap | Cycle through stacked regions |
| Double-click a region | Open an inline text editor for its description |
| Right-click canvas | Open the regions layer list (select / reorder / duplicate / delete) |
| Del / Backspace | Delete the selected region |
| Ctrl/Cmd + C / V / D | Copy / paste / duplicate the selected region |
| + Region button | Add a default staggered region (and its string input pin) |
| Grab BG button | Use the last generated image as the canvas background |
| Live checkbox | Feed the live sampling preview as the background while generating |
| Brightness slider | Dim the background image or set the blank canvas grey level |
| ~N tok | Rough token estimate; green = healthy, orange = nearing cap, red = at/over 2048 (model error) |
| Copy button | Copy the assembled caption JSON to the clipboard |
| Paste button | Import a caption JSON from the clipboard (or a paste prompt) into the editor |

### Layers menu (right-click)

Lists all regions top-to-bottom (region 01 is the front-most layer). From the menu you can:

- Click a row to select that region.
- Drag rows to reorder them.
- Click the ⧉ button to duplicate a region into placement mode (the copy follows the cursor until you click to place it).
- Click the ✕ button to delete a region.

---

## Style and palette

A global **Style colors** row sits above the canvas for per-image color palette swatches. Per-region color palettes appear in the selected region's panel. Swatches can be:

- Clicked to open a color picker.
- Right-clicked to remove.
- Dragged to reorder.

Up to 16 colors for the style palette; up to 5 colors per region element.

---

## Inputs

### Required

| Input | Type | Description |
|---|---|---|
| `width` | INT | Canvas width. Sets the aspect ratio; use multiples of 16. |
| `height` | INT | Canvas height. Sets the aspect ratio; use multiples of 16. |

### Optional

| Input | Type | Description |
|---|---|---|
| `high_level_description` | STRING | Optional one-line overview of the whole image. Omitted from the JSON when blank. |
| `background` | STRING | Scene background description. |
| `style` | ENUM | `none` omits the style block; `photo` or `art_style` adds the matching key. |
| `photo` | STRING | Photo style descriptor (visible only when `style = photo`). |
| `art_style` | STRING | Art-style descriptor (visible only when `style = art_style`). |
| `aesthetics` | STRING | Style descriptor. |
| `lighting` | STRING | Style descriptor. |
| `medium` | STRING | Style descriptor. |
| `image` | IMAGE | Reference image shown as the dimmed canvas background and behind the preview. |
| `import_json` | STRING | A full caption JSON. When connected, loads into the editor on run. The output always reflects the editor, never the raw input. |
| `region_N` | STRING | **Dynamic.** One pin per region drawn on the canvas. A connected, non-empty string overrides that region's description at run time. |

The `style_palette_data`, `elements_data`, and `bg_brightness` inputs are managed internally by the node UI and are hidden from the widget list.

---

## Outputs

| Output | Type | Description |
|---|---|---|
| `prompt` | STRING | The assembled Ideogram 4 caption JSON, ready to pass to an API node. |
| `preview` | IMAGE | Rendered preview of the regions drawn over the reference image (or a blank canvas). |
| `bboxes` | BOUNDING_BOX | Pixel-space bounding boxes `{x, y, width, height}` for each placed region, in the format expected by SAM3 and crop nodes. |
| `width` | INT | Canvas width (pass-through). |
| `height` | INT | Canvas height (pass-through). |

The `bboxes` output uses per-frame nesting (`list[list[dict]]`) — the standard shape that SAM3 and other bounding-box consumers expect.

---

## Region panel

When a region is selected, the panel below the canvas shows:

- **type** toggle — `obj` (an object or scene element) or `text` (a text element to render verbatim).
- **text** field — visible only for `text` type; the string Ideogram 4 will render literally.
- **description** field — free-text description of the region. **Overridden at run time by the matching `region_N` input pin when it is connected.**
- A note reminding you which input pin will override this description.
- **colors** — per-region color palette swatches.

---

## How the JSON caption is assembled

The node mirrors the Ideogram 4 structured caption format exactly:

```json
{
    "high_level_description": "...",
    "style_description": {
        "aesthetics": "...",
        "lighting": "...",
        "photo": "...",
        "medium": "...",
        "color_palette": ["#RRGGBB", ...]
    },
    "compositional_deconstruction": {
        "background": "...",
        "elements": [
            {
                "type": "obj",
                "bbox": [ymin, xmin, ymax, xmax],
                "desc": "...",
                "color_palette": ["#RRGGBB", ...]
            },
            {
                "type": "text",
                "bbox": [ymin, xmin, ymax, xmax],
                "text": "render this",
                "desc": "...",
                "color_palette": ["#RRGGBB", ...]
            }
        ]
    }
}
```

- `bbox` coordinates are on a **0–1000 grid** as `[ymin, xmin, ymax, xmax]`.
- The `style_description` block is omitted entirely when `style = none`.
- `color_palette` is omitted from an element when no colors are set.
- Elements drawn with no bbox (imported from JSON without coordinates) are exported without a `bbox` key.
