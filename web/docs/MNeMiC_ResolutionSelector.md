# 📐 Resolution Image Size Selector

Picks an output resolution from a preset, your own saved preset, custom
numbers, or an incoming image — then optionally multiplies, clamps, snaps and
swaps it. Hands back the numbers plus a matching empty latent.

## Inputs

- **preset** — Model-specific resolution presets, grouped by model. `Custom`
  uses the width/height widgets.
- **preset_user** — Your own presets. `None` means "ignore this".
- **custom_width** / **custom_height** — Used when `preset` is `Custom` and no
  higher-priority source applies.
- **image (optional)** — Connect an image to take its dimensions.

Advanced:

- **multiply** — Scales the final result. Negative values flip width and
  height.
- **swap_width_and_height** — Swaps the two.
- **image_min_length** / **image_max_length** — When an image is connected,
  clamp its shortest / longest side. `0` disables the clamp.
- **snap_to_nearest** + **snap_resolution** — Round both dimensions to a
  multiple of `snap_resolution`. `0` disables snapping.
- **batch_size** — How many latents to make in the batch.

## Outputs

- **width** / **height** — The final numbers, in pixels.
- **latent** — An empty latent of that size, `batch_size` deep.

## Priority

Highest wins:

1. **image (optional)** — if connected
2. **preset_user** — if not `None`
3. **preset** — if not `Custom`
4. **custom_width** / **custom_height**

The multiply, clamp, snap and swap steps then run on whatever that produced.
Dimensions are never allowed below 64 pixels.

## Your own presets

User presets live in `nodes/resolution_selector/user_resolution.json` and are
created with a `Favorites` group the first time the node loads. Edit that file
to add your own; entries are grouped by the top-level key and shown as
`Group: name`. The model presets are in `preset_resolution.json` next to it.

```json
{
    "Favorites": [
        {"name": "[Square] 768x768 1:1", "width": 768, "height": 768},
        {"name": "[Portrait] 832x1216 13:19", "width": 832, "height": 1216}
    ]
}
```

Reload ComfyUI after editing — the lists are read when the node is registered.
