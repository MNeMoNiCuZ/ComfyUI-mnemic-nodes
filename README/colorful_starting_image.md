# 🎨 Colorful Starting Image

A powerful and highly customizable ComfyUI node for generating complex, abstract, and visually interesting images from scratch. It serves as an excellent starting point for creative workflows, providing a rich visual foundation that can be used as an initial image, a texture, or a source for further manipulation.

![image](https://github.com/user-attachments/assets/d40e27d7-e17d-4750-b88b-9cf39b654823)

## ✨ Features

- **Highly Customizable**: A vast array of controls to move from simple geometric patterns to chaotic, organic, and atmospheric compositions.
- **Flexible Shape System**: Define a custom mix of shapes to draw, including rectangles, ellipses, lines, splines, dots, stripes, triangles, polygons, and more.
- **Advanced Color Control**: Go beyond random colors with palettes, color harmonies, multi-color fills, and opacity.
- **Granular Randomization**: Precisely control the placement and size of shapes with positioning biases and size distributions.
- **Organic Effects**: Add a new layer of visual interest with features like rotation, color bleed, and shape warping.
- **Workflow Integration**: A dedicated `MASK` output for seamless integration with other nodes.

## ⚙️ Inputs

### Core Generation
- **`width` / `height`**: The dimensions of the output image in pixels.
- **`layers`**: The total number of shapes to draw. More layers create a more complex image.
- **`density`**: Controls the maximum size of shapes relative to the image dimensions.
- **`shape_string`**: A comma-separated list of shapes to draw (e.g., `rectangle, dot, dot`). The node randomly picks from this list for each layer, so repeating a shape increases its probability.

### Colorization
- **`color_palette`**: The base color generation method (`random`, `muted`, `grayscale`, `high_contrast`).
- **`color_harmony`**: Applies a color theory rule (`complementary`, `analogous`, `triadic`) for more aesthetically pleasing results.
- **`multi_color_mode`**: Fills shapes with multiple colors instead of a solid fill (`gradient`, `random_vertices`).
- **`shape_opacity`**: The transparency of the drawn shapes. Lower values create blending effects.
- **`background_color`**: The background color of the canvas (e.g., `black`, `#FF0000`).

### Randomization & Composition
- **`positioning_bias`**: Controls where shapes are more likely to appear on the canvas.
- **`size_distribution`**: Biases the random size generation towards smaller or larger shapes.
- **`allow_rotation`**: If true, allows shapes like rectangles and lines to be drawn at random angles.
- **`controlled_chaos`**: Arranges shapes in a structured pattern (e.g., `spiral`, `burst`) instead of pure randomness.
- **`seed`**: The seed for the random number generator. The same seed with the same settings will always produce the same image.

### Effects & Post-Processing
- **`stroke_width`**: If greater than 0, shapes will be drawn as outlines of this width instead of being filled.
- **`noise_level`**: Fills shapes with a noisy, grainy texture instead of a solid color.
- **`color_bleed`**: Simulates a watercolor-like effect where colors from shapes bleed into their surroundings.
- **`warp_type`**: The type of distortion to apply to the final image (e.g., `wave`, `swirl`).
- **`warp_intensity`**: The strength of the distortion effect.
- **`blur_radius`**: Applies a final Gaussian blur to the entire image.

## ել Outputs
- **`image`**: The final generated colorful image.
- **`latent`**: A latent representation of the final image, ready to be used in a diffusion model.
- **`mask`**: A black-and-white mask where all drawn shapes are white and the background is black.