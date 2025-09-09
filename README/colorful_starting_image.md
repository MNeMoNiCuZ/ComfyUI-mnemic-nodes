# 🎨 Colorful Starting Image

A powerful and highly customizable ComfyUI node for generating complex, abstract, and visually interesting images from scratch. It serves as an excellent starting point for creative workflows, providing a rich visual foundation that can be used as an initial image, a texture, or a source for further manipulation.

![image](https://github.com/user-attachments/assets/d40e27d7-e17d-4750-b88b-9cf39b654823)

## ✨ Features

- **Highly Customizable**: Over 15 parameters for control from simple geometric patterns to complex, organic compositions.
- **Flexible Shape System**: Define a custom mix of shapes including rectangles, ellipses, circles, lines, splines, dots, stripes, triangles, polygons, arcs, gradient rectangles, and concentric circles.
- **Advanced Color Control**: Multiple palettes, color harmonies, multi-color modes, opacity, and noise effects.
- **Granular Randomization**: Precise control over shape placement, sizing, rotation, and arrangement patterns.
- **Noise & Distortion**: Add grainy textures and warp effects for organic complexity.
- **Workflow Integration**: Dual outputs (image + mask) for ComfyUI workflows.

## ⚙️ Inputs

### Core Generation
- **`width` / `height`**: The dimensions of the output image in pixels.
- **`components`**: The total number of shapes to draw. More components create a more complex image.
- **`component_scale`**: Controls the maximum size of shapes relative to the image dimensions (0.01-1.0).
- **`shape_string`**: A comma-separated list of shapes (e.g., `rectangle, ellipse, line`). Available: rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, gradient_rectangle, concentric_circles.

### Colorization
- **`color_palette`**: Base color method: `random` (picks from others), `random_color` (any RGB), `muted`, `grayscale`, `binary`, `neon`, `pastel`, `colorized` (single random hue across all shapes).
- **`color_harmony`**: Color theory rules: `random` (picks from others), `none`, `complementary`, `analogous`, `triadic`, `tetradic`.
- **`fill_mode`**: Multi-color fills: `random` (picks from others), `none`, `gradient`, `vertices`.
- **`shape_opacity`**: Alpha value (0.0-1.0) for drawn shapes.
- **`background_color`**: Canvas background - color names, hex codes, or `random`.

### Randomization & Composition
- **`positioning_bias`**: Placement bias: `random` (from others), `scattered`, `center_weighted`, `edge_weighted`, `grid_aligned`, `random_weighted`, directional (north, south, east, west, corners).
- **`arrangement`**: Structured patterns: `random` (from others), `none`, `spiral`, `burst`, `grid`.
- **`size_distribution`**: Size bias: `random` (from others), `uniform`, `prefer_small`, `prefer_large`.
- **`allow_rotation`**: Enable random rotation for rectangles, lines, etc.
- **`seed`**: Random seed (supports 64-bit values for reproducibility).

### Effects & Post-Processing
- **`noise_level`**: Grain intensity (0.0-5.0 multiplier).
- **`noise_scale`**: Grain patch size (1.0-100.0).
- **`noise_color`**: Grain type: `random`, `colored`, `monochrome`.
- **`warp_type`**: Distortion type: `random` (from others), `none`, `wave`, `noise_field`, `swirl`.
- **`warp_intensity`**: Distortion strength (0.0-1.0).
- **`blur_radius`**: Final Gaussian blur (0.0-1.0).

## 📤 Outputs
- **`image`**: The generated color image (RGB tensor).
- **`mask`**: Black-and-white mask where drawn shapes are white, background is black (mask tensor).