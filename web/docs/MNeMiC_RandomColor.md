# 🎲 Random Color

Rolls an RGB colour and hands it back in both formats.

## Inputs

- **seed** *(optional)* — `-1` rolls freshly every run; any other value makes
  the colour repeatable.

## Outputs

- **hex_color** — The colour as `#RRGGBB`.
- **red** / **green** / **blue** — The same colour as three 0-255 numbers.

## Notes

Every channel is rolled independently across the full range, so results are
evenly spread rather than pleasant. For themed palettes (muted, neon, pastel,
harmonies) use 🎨 Colorful Starting Image.
