# 🎨 Colorful Starting Image

Generates a random abstract image of coloured shapes. Made to be fed into an
img2img pass at high denoise, where it seeds composition and colour instead of
the flat grey a blank latent gives you.

Everything is exposed on the node on purpose — it is a visual playground, so
there is nothing hidden behind Advanced.

## Inputs

Canvas:

- **width** / **height** — Output size in pixels.
- **background_color** — A colour name, a hex code like `#FF0000`, or one of
  `random`, `noise`, `noise_large`, `noise_color`, `noise_color_large`.

Shapes:

- **components** — How many shapes to draw.
- **component_scale** — Largest shape size as a fraction of the canvas width.
  At 1024px and 0.5, big shapes land around 512px.
- **shape_string** — Comma-separated shapes to draw from: `rectangle, ellipse,
  circle, line, spline, dot, stripes, triangle, polygon, arc,
  concentric_circles`.
- **size_distribution** — `uniform`, `prefer_small` or `prefer_large`.
- **allow_rotation** — Let rectangles and lines rotate.
- **shape_opacity** — Alpha of the shapes, 0.1-1.0.

Colour:

- **color_palette** — `random_color`, `muted`, `grayscale`, `binary`, `neon`,
  `pastel`, or `colorized` (grayscale tinted with one shared hue).
- **color_harmony** — `complementary`, `analogous`, `triadic` or `tetradic`
  relationships between the picked colours. No effect on the `binary` palette.
- **fill_mode** — `none` for flat fills, `gradient` for a two-colour blend per
  shape, `blocks` for vertical strips.

Layout:

- **positioning_bias** — Where shapes cluster: `scattered`, `center_weighted`,
  `edge_weighted`, `grid_aligned`, `random_weighted`, or a compass direction.
  Ignored when `arrangement` is not `none`.
- **arrangement** — `spiral`, `burst` or `grid` structured placement.

Post-processing:

- **noise_level** / **noise_scale** / **noise_color** — Gaussian noise in the
  shape fills. Scale 1 is per-pixel; higher values give larger blotches.
- **warp_type** / **warp_intensity** — `wave`, `noise_field` or `swirl`
  distortion of the finished image.
- **blur_radius** — Final Gaussian blur, in pixels.

- **seed** — Same seed and settings always produce the same image.

## Outputs

- **image** — The generated image.
- **mask** — White where shapes were drawn, black where the background shows
  through.

## Notes

Every combo input also offers `random`, which re-rolls that one setting per
run. Related: 🎲 Random Color for a single colour instead of an image.
