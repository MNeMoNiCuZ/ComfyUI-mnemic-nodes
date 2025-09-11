import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

import random
import math
import colorsys
import cv2

class ColorfulStartingImage:
    COLOR_PALETTE_OPTIONS = ["random_color", "muted", "grayscale", "binary", "neon", "pastel", "colorized"]
    COLOR_HARMONY_OPTIONS = ["none", "complementary", "analogous", "triadic", "tetradic"]
    MULTI_COLOR_MODE_OPTIONS = ["none", "gradient", "blocks"]
    POSITIONING_BIAS_OPTIONS = [
        "scattered", "center_weighted", "edge_weighted", "grid_aligned", "random_weighted",
        "north", "south", "east", "west",
        "north_west", "north_east", "south_west", "south_east"
    ]
    ARRANGEMENT_OPTIONS = ["none", "spiral", "burst", "grid"]
    SIZE_DISTRIBUTION_OPTIONS = ["uniform", "prefer_small", "prefer_large"]
    WARP_TYPE_OPTIONS = ["none", "wave", "noise_field", "swirl"]

    @classmethod
    def INPUT_TYPES(s):
        """
        Return the INPUT_TYPES schema describing the node's configurable inputs for the UI.
        
        The returned dictionary contains a "required" mapping of input names to their type descriptors and metadata (defaults, ranges, tooltips, and option lists). This schema controls available parameters for image generation such as image dimensions, number of components, shape choices, color palette/harmony, fill mode, positioning/arrangement, size distribution, rotation, noise and warp settings, blur, and RNG seed. Many fields accept "random" to let the node pick a value at runtime; color and arrangement option lists are derived from the class-level constants on `s`.
        """
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The width of the generated image in pixels."}),
                "height": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The height of the generated image in pixels."}),
                "components": ("INT", {"default": 20, "min": 1, "tooltip": "The total number of components (shapes) to draw on the image. More components create a more complex image."}),
                "component_scale": ("FLOAT", {"default": 0.5, "min": 0.01, "step": 0.01, "tooltip": "Controls the maximum potential size of shapes. A shape's max width is `image_width * component_scale`.\nExample: With a 1024px wide image and 0.5 scale, the largest shapes will be around 512px wide."} ),
                "shape_string": ("STRING", {"default": "rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, concentric_circles", "multiline": True, "tooltip": "A comma-separated list of shapes to draw from.\n\nAvailable shapes:\n- rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, concentric_circles"}),
                "color_palette": (["random"] + s.COLOR_PALETTE_OPTIONS, {"tooltip": "The color palette for the shapes.\n\nOptions:\n- random: Picks one of the other palette options at random.\n- random_color: Any RGB color.\n- muted: Less saturated, softer colors.\n- grayscale: Shades of gray.\n- binary: Pure black and white.\n- neon: Bright, highly saturated colors.\n- pastel: Soft, low-saturation colors.\n- colorized: Grayscale tinted with a single random hue across all shapes."} ),
                "color_harmony": (["random"] + s.COLOR_HARMONY_OPTIONS, {"tooltip": "Apply a color harmony rule to the generated colors.\n\nOptions:\n- none: No harmony.\n- complementary: Two colors from opposite sides.\n- analogous: Three colors next to each other.\n- triadic: Three colors evenly spaced.\n- tetradic: Four colors in square harmony.\n\nNote: Color harmony has no effect when the 'binary' color palette is selected."} ),
                "fill_mode": (["random"] + s.MULTI_COLOR_MODE_OPTIONS, {"tooltip": "Fill shapes with multiple colors.\n\nOptions:\n- none: Shapes are filled with a single color.\n- gradient: Blends two colors in a vertical gradient across each shape.\n- blocks: Divides each shape into vertical strips of solid, related colors."} ),
                "shape_opacity": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.05, "tooltip": "The alpha value (0.0 to 1.0) for the drawn shapes. 1.0 is fully opaque."} ),
                "background_color": ("STRING", {"default": "black", "tooltip": "The background color of the image. `random` is a valid value.\nCan be a color name (e.g., 'black', 'white', 'random')\nor a hex code (e.g., '#FF0000').\n\nFor a list of supported color names, see: https://www.w3.org/TR/css-color-3/#svg-color"}),
                "positioning_bias": (["random"] + s.POSITIONING_BIAS_OPTIONS, {"tooltip": "Controls where shapes are likely to appear.\n\nOptions:\n- scattered: Anywhere on the canvas.\n- center_weighted: Clustered in the center.\n- edge_weighted: Clustered along the edges.\n- grid_aligned: Aligned to a grid.\n- random_weighted: Clustered around two random points.\n- north/south/east/west: Clustered on that edge.\n- nw/ne/sw/se: Clustered in that corner."} ),
                "arrangement": (["random"] + s.ARRANGEMENT_OPTIONS, {"tooltip": "Arrange shapes in a structured, less random pattern.\n\nOptions:\n- none: Random placement.\n- spiral: Shapes are arranged in a spiral.\n- burst: Shapes burst outwards from the center.\n- grid: Shapes are aligned to a grid."} ),
                "size_distribution": (["random"] + s.SIZE_DISTRIBUTION_OPTIONS, {"tooltip": "Controls the distribution of shape sizes.\n\nOptions:\n- uniform: All sizes are equally likely.\n- prefer_small: Favors smaller shapes.\n- prefer_large: Favors larger shapes."} ),
                "allow_rotation": ("BOOLEAN", {"default": True, "tooltip": "Allow random rotation of shapes like rectangles and lines."} ),
                "noise_level": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 5.0, "step": 0.05, "tooltip": "Controls the amount of Gaussian noise added to shape fills. It acts as a multiplier for the noise intensity, where 0 is no noise and 1 is maximum intensity."} ),
                "noise_scale": ("FLOAT", {"default": 1.0, "min": 1.0, "max": 100.0, "step": 1.0, "tooltip": "Scale of the noise pattern. A scale of 1 creates fine, per-pixel noise. Higher values create larger, more coherent noise patterns."} ),
                "noise_color": (["random", "colored", "monochrome"], {"tooltip": "Whether the noise should be colored or monochrome."} ),
                "warp_type": (["random"] + s.WARP_TYPE_OPTIONS, {"tooltip": "Type of distortion to apply to the final image.\n\nOptions:\n- none: No distortion.\n- wave: Sine wave distortion.\n- noise_field: Random, noisy distortion.\n- swirl: Swirls the image around the center."} ),
                "warp_intensity": ("FLOAT", {"default": 0.5, "min": 0.0, "step": 0.1, "tooltip": "Multiplier for the warp effect. For wave/turbulence, it scales pixel displacement. For swirl, it scales the rotation angle."} ),
                "blur_radius": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1, "tooltip": "The radius in pixels for the final Gaussian blur filter."} ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed for the random number generator. Using the same seed and parameters will produce the same image."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "generate_image"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Creates a highly customizable, colorful image with random patterns and shapes, useful as a starting point for image generation."

    def get_harmonized_colors(self, harmony):
        """
        Return a small list of RGB colors (tuples of floats in 0–1) that follow the specified color harmony.
        
        If `harmony` is one of "complementary", "analogous", "triadic", or "tetradic", the function generates a random base hue and returns colors computed from that hue using HSV→RGB conversion; saturation and value for each color are randomized in the 0.5–1.0 range. For any other `harmony` value an empty list is returned.
        
        Parameters:
            harmony (str): One of "complementary", "analogous", "triadic", "tetradic" (case-sensitive). Determines the harmonic rule used to derive additional hues.
        
        Returns:
            list[tuple[float, float, float]]: List of RGB color tuples with components in the 0–1 range, or an empty list if the harmony is not recognized.
        """
        base_hue = np.random.rand()
        if harmony == "complementary": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.5) % 1]]
        if harmony == "analogous": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.083) % 1, (base_hue - 0.083) % 1]]
        if harmony == "triadic": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.333) % 1, (base_hue - 0.333) % 1]]
        if harmony == "tetradic": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.25) % 1, (base_hue + 0.5) % 1, (base_hue + 0.75) % 1]]
        return []

    def get_color(self, palette, harmony_colors, colorized_hue=None):
        """
        Return an (R, G, B) color tuple (ints 0–255) chosen according to the requested palette and optional harmony colors.
        
        Detailed behavior:
        - If `harmony_colors` is provided, some palettes prefer selecting from that list (values in `harmony_colors` are expected as (r,g,b) floats in [0,1]):
          - For "grayscale" with harmony: uses a harmony hue but chooses a lightness corresponding to a random gray value.
          - For "binary" with harmony: uses a harmony hue and returns a strongly black- or white-tinted color.
          - Otherwise when `harmony_colors` is present, a random harmony color is returned (converted to 0–255 ints).
        - Palette-specific rules when `harmony_colors` is not used:
          - "muted": random RGB each channel in [50,200].
          - "grayscale": uniform gray value in [0,254].
          - "binary": randomly returns pure black or pure white.
          - "neon": high-saturation HSV with value 0.8.
          - "pastel": low-saturation HSV with value 1.0.
          - "colorized": produces a color with the provided `colorized_hue` (float 0–1) or a random hue if None; saturation is sampled in [0.5,1.0].
        - Fallback: completely random RGB when palette is unknown.
        
        Parameters:
            palette (str): Named palette key (e.g., "muted", "grayscale", "binary", "neon", "pastel", "colorized").
            harmony_colors (iterable or None): Optional list/iterable of harmonious colors as (r,g,b) floats in [0,1]; when provided, may influence the returned color.
            colorized_hue (float or None): Hue in [0,1] to use for "colorized" palette; if None a random hue is chosen.
        
        Returns:
            tuple: (R, G, B) with integer channel values in 0–255.
        """
        if palette == "grayscale" and harmony_colors:
            gray_val = np.random.randint(0, 255)
            harmonious_color = random.choice(harmony_colors)
            h, _, _ = colorsys.rgb_to_hls(harmonious_color[0], harmonious_color[1], harmonious_color[2])
            s = np.random.uniform(0.5, 1.0)
            l = gray_val / 255
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return (int(r*255), int(g*255), int(b*255))
        if palette == "binary" and harmony_colors:
            harmonious_color = random.choice(harmony_colors)
            h, _, _ = colorsys.rgb_to_hls(harmonious_color[0], harmonious_color[1], harmonious_color[2])
            s = np.random.uniform(0.5, 1.0)
            l = 0 if np.random.rand() > 0.5 else 1  # black or white tinted
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return (int(r*255), int(g*255), int(b*255))
        if harmony_colors: color = random.choice(harmony_colors); return (int(color[0]*255), int(color[1]*255), int(color[2]*255))
        if palette == "muted": return (np.random.randint(50, 200), np.random.randint(50, 200), np.random.randint(50, 200))
        if palette == "grayscale": val = np.random.randint(0, 255); return (val, val, val)
        if palette == "binary": return (0,0,0) if np.random.rand() > 0.5 else (255,255,255)
        if palette == "neon":
            hue = np.random.rand()
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 0.8)
            return (int(r*255), int(g*255), int(b*255))
        if palette == "pastel":
            hue = np.random.rand()
            r, g, b = colorsys.hsv_to_rgb(hue, 0.2, 1.0)
            return (int(r*255), int(g*255), int(b*255))
        if palette == "colorized":
            gray_val = np.random.randint(0, 255)
            s = np.random.uniform(0.5, 1.0)
            r, g, b = colorsys.hls_to_rgb(colorized_hue if colorized_hue is not None else np.random.rand(), gray_val / 255, s)
            return (int(r*255), int(g*255), int(b*255))
        return (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))

    def get_biased_position(self, width, height, bias, arrangement, arrangement_params):
        """
        Return an (x, y) pixel position for placing a shape, biased by the requested arrangement or spatial bias.
        
        If an arrangement other than "none" is specified this computes a position according to that layout:
        - "spiral": requires arrangement_params['angle'] (radians) and ['radius'].
        - "burst": requires arrangement_params['angle'] and ['max_radius']; radius is sampled uniformly [0, max_radius].
        - "grid": requires arrangement_params['grid_w'], ['grid_h'] and ['index']; chooses a random offset inside the indexed grid cell.
        
        If arrangement is "none" the position is chosen according to the bias:
        - "center_weighted": normal distribution around image center.
        - "edge_weighted": biased toward a random image edge.
        - "grid_aligned": snapped to one of an 8x8 grid cell origins.
        - "random_weighted": samples around a randomly chosen anchor inside the image (avoids exact center).
        - Compass and corner biases ("north", "south", "east", "west", "north_west", "north_east", "south_west", "south_east"): sample near the corresponding edge/corner.
        - any other value: uniform random position.
        
        Parameters:
            width (int): image width in pixels.
            height (int): image height in pixels.
            bias (str): positioning bias name used when arrangement == "none".
            arrangement (str): layout mode ("none", "spiral", "burst", "grid", ...).
            arrangement_params (dict): parameters required by the chosen arrangement (see above).
        
        Returns:
            tuple[int, int]: (x, y) integer coordinates clamped to the image bounds.
        """
        x, y = 0, 0
        if arrangement != "none":
            if arrangement == "spiral":
                angle, radius = arrangement_params['angle'], arrangement_params['radius']
                x, y = (int(width / 2 + radius * math.cos(angle)), int(height / 2 + radius * math.sin(angle)))
            elif arrangement == "burst":
                angle, max_radius = arrangement_params['angle'], arrangement_params['max_radius']
                radius = np.random.uniform(0, max_radius)
                x, y = (int(width / 2 + radius * math.cos(angle)), int(height / 2 + radius * math.sin(angle)))
            elif arrangement == "grid":
                grid_w, grid_h, index = arrangement_params['grid_w'], arrangement_params['grid_h'], arrangement_params['index']
                cell_w, cell_h = width / grid_w, height / grid_h
                col = index % grid_w
                row = index // grid_w
                x = int(col * cell_w + np.random.uniform(0, cell_w))
                y = int(row * cell_h + np.random.uniform(0, cell_h))
        elif bias == "center_weighted": x, y = int(np.random.normal(width / 2, width / 6)), int(np.random.normal(height / 2, height / 6))
        elif bias == "edge_weighted":
            if np.random.rand() > 0.5:
                x = np.random.randint(0, int(width * 0.1)) if np.random.rand() > 0.5 else np.random.randint(int(width * 0.9), width)
                y = np.random.randint(0, height)
            else:
                x, y = np.random.randint(0, width), np.random.randint(0, int(height * 0.1)) if np.random.rand() > 0.5 else np.random.randint(int(height * 0.9), height)
        elif bias == "grid_aligned": grid_size = 8; x, y = (np.random.randint(0, grid_size) * (width // grid_size)), (np.random.randint(0, grid_size) * (height // grid_size))
        elif bias == "random_weighted":
            anchor_x = np.random.uniform(width * 0.1, width * 0.9)
            if width * 0.4 < anchor_x < width * 0.6: anchor_x += np.random.choice([-1, 1]) * width * 0.2
            anchor_y = np.random.uniform(height * 0.1, height * 0.9)
            if height * 0.4 < anchor_y < height * 0.6: anchor_y += np.random.choice([-1, 1]) * height * 0.2
            x, y = int(np.random.normal(anchor_x, width / 8)), int(np.random.normal(anchor_y, height / 8))
        elif bias == "north": x, y = np.random.randint(0, width), int(np.random.normal(height * 0.1, height / 10))
        elif bias == "south": x, y = np.random.randint(0, width), int(np.random.normal(height * 0.9, height / 10))
        elif bias == "west": x, y = int(np.random.normal(width * 0.1, width / 10)), np.random.randint(0, height)
        elif bias == "east": x, y = int(np.random.normal(width * 0.9, width / 10)), np.random.randint(0, height)
        elif bias == "north_west": x, y = int(np.random.normal(width * 0.1, width / 10)), int(np.random.normal(height * 0.1, height / 10))
        elif bias == "north_east": x, y = int(np.random.normal(width * 0.9, width / 10)), int(np.random.normal(height * 0.1, height / 10))
        elif bias == "south_west": x, y = int(np.random.normal(width * 0.1, width / 10)), int(np.random.normal(height * 0.9, height / 10))
        elif bias == "south_east": x, y = int(np.random.normal(width * 0.9, width / 10)), int(np.random.normal(height * 0.9, height / 10))
        else: x, y = np.random.randint(0, width), np.random.randint(0, height)
        return (max(0, min(width, x)), max(0, min(height, y)))

    def get_biased_size(self, max_size, distribution):
        """
        Return an integer shape size biased according to the requested distribution.
        
        Parameters:
            max_size (int): Maximum reference size for the shape.
            distribution (str): One of "uniform" (default behavior), "prefer_small", or "prefer_large".
                - "prefer_small": samples from a zero-mean normal (sigma = max_size/3), takes the absolute value,
                  converts to int and adds 1 (biases toward smaller values).
                - "prefer_large": samples from the same normal, subtracts its absolute value from max_size,
                  clamps to at least 1 (biases toward larger values).
                - otherwise: returns a uniform random integer in [1, max(2, int(max_size))).
        
        Returns:
            int: Computed size (always >= 1). The value distribution depends on the chosen `distribution`.
        """
        if distribution == "prefer_small": return int(abs(np.random.normal(0, max_size / 3))) + 1
        if distribution == "prefer_large":
            val = int(max_size - abs(np.random.normal(0, max_size / 3)))
            return max(1, val)
        return np.random.randint(1, max(2, int(max_size)))

    def draw_pulsating_line(self, draw, points, color, component_scale, width, height):
        """
        Draws a ribbon-like polyline with a sinusoidally "pulsating" thickness between a sequence of points.
        
        The function renders each segment between consecutive points as a filled polygon whose local thickness varies along the segment to produce a wavy, organic stroke. Designed to be resolution-aware: `component_scale`, `width`, and `height` control the overall maximum thickness.
        
        Parameters:
            draw: PIL.ImageDraw.Draw
                Drawing context to render the filled polygon(s) onto.
            points: Sequence[tuple[float, float]]
                Ordered list of (x, y) coordinates defining the polyline. At least two points are required.
            color: tuple or int
                Fill color used for the polygon. May be an RGB(A) tuple or a color value accepted by PIL.
            component_scale: float
                Relative scale used to compute maximum stroke thickness (proportional to the smaller of image width/height).
            width: int
                Canvas width in pixels (used to compute scale-dependent thickness).
            height: int
                Canvas height in pixels (used to compute scale-dependent thickness).
        
        Returns:
            None
        
        Notes:
            - No drawing occurs if `points` is empty or contains fewer than two points.
            - The routine builds a closed ribbon for each segment by offsetting points along the segment normal and filling the resulting polygon.
        """
        if not points or len(points) < 2: return

        max_thickness = max(2, int(min(width, height) * component_scale * 0.05))
        base_thickness = np.random.randint(1, max(2, max_thickness))
        
        num_segments = 20 # Segments per line for pulsation
        
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i+1]
            
            length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            if length == 0: continue

            dir_x, dir_y = (p2[0] - p1[0]) / length, (p2[1] - p1[1]) / length
            normal_x, normal_y = -dir_y, dir_x
            
            polygon_points = []
            for j in range(num_segments + 1):
                t = j / num_segments
                current_pos_x = p1[0] + t * (p2[0] - p1[0])
                current_pos_y = p1[1] + t * (p2[1] - p1[1])
                
                pulsation = (math.sin(t * 2 * math.pi * np.random.uniform(1, 3)) + 1) / 2 # Varies between 0 and 1
                current_thickness = base_thickness + (max_thickness - base_thickness) * pulsation
                
                offset = current_thickness / 2
                p_above = (current_pos_x + offset * normal_x, current_pos_y + offset * normal_y)
                p_below = (current_pos_x - offset * normal_x, current_pos_y - offset * normal_y)
                
                polygon_points.insert(j, p_above)
                polygon_points.insert(j+1, p_below)

            draw.polygon(polygon_points, fill=color)

    def _create_gradient_fill(self, width, height, color1, color2, opacity):
        """
        Create a vertical RGBA gradient image transitioning from color1 at the top to color2 at the bottom.
        
        Parameters:
            width (int): Output image width in pixels.
            height (int): Output image height in pixels.
            color1 (tuple or sequence of int): RGB color at the top (three 0–255 values).
            color2 (tuple or sequence of int): RGB color at the bottom (three 0–255 values).
            opacity (float): Alpha value applied uniformly to the whole image (0.0–1.0).
        
        Returns:
            PIL.Image.Image: An RGBA-mode image of size (width, height) with the vertical gradient and uniform alpha.
        """
        c1 = np.array(color1)
        c2 = np.array(color2)
        ramp = np.linspace(0, 1, height).reshape(height, 1, 1)
        gradient_rgb = c1 * (1 - ramp) + c2 * ramp
        gradient_rgb_w = np.broadcast_to(gradient_rgb, (height, width, 3))
        gradient_rgb_w = gradient_rgb_w.astype(np.uint8)
        alpha = np.full((height, width, 1), int(255 * opacity), dtype=np.uint8)
        gradient_rgba = np.concatenate((gradient_rgb_w, alpha), axis=2)
        return Image.fromarray(gradient_rgba, 'RGBA')

    def _create_blocks_fill(self, width, height, palette, harmony_colors, colorized_hue, opacity):
        """
        Create a vertical striped block fill as an RGBA PIL Image.
        
        Creates between 3 and 5 vertical strips across the specified width, assigning each strip a color chosen via self.get_color(...). The color's alpha channel is set according to opacity and the resulting image is returned as a PIL Image in 'RGBA' mode.
        
        Parameters:
            width (int): Width of the generated fill in pixels.
            height (int): Height of the generated fill in pixels.
            palette (str): Color palette identifier forwarded to self.get_color.
            harmony_colors (list): Optional list of harmony colors forwarded to self.get_color.
            colorized_hue (float | None): Optional hue used by colorized palettes; forwarded to self.get_color.
            opacity (float): Alpha multiplier in [0.0, 1.0] applied to each strip's color.
        
        Returns:
            PIL.Image.Image: An RGBA image of shape (height, width) containing the vertical block fill.
        
        Notes:
            - The number of strips (3–5) and their exact boundaries are chosen using NumPy's random functions, so output depends on the current NumPy RNG state.
            - Strips that would have zero width are skipped.
        """
        num_strips = np.random.randint(3, 6)
        blocks_rgba = np.zeros((height, width, 4), dtype=np.uint8)
        strip_boundaries = np.linspace(0, width, num_strips + 1, dtype=int)
        for i in range(num_strips):
            strip_x1 = strip_boundaries[i]
            strip_x2 = strip_boundaries[i+1]
            if strip_x1 >= strip_x2: continue
            block_color = self.get_color(palette, harmony_colors, colorized_hue)
            strip_color = block_color + (int(255 * opacity),)
            blocks_rgba[:, strip_x1:strip_x2] = strip_color
        return Image.fromarray(blocks_rgba, 'RGBA')

    def draw_shape(self, width, height, component_scale, shape, palette, image, mask, pos_bias, size_dist, rotation, harmony_colors, opacity, noise_level, noise_scale, noise_color, arrangement, arrangement_params, fill_mode, noise_rng, colorized_hue=None):
        """
        Render a single shape onto the provided image and its mask, returning the composited image and updated mask.
        
        This method creates separate RGBA and mask layers for one shape, computes a biased position and size, builds a per-shape mask (rectangle, triangle, polygon, ellipse/circle, dot, or line/arc/stripes variants), optionally fills the shape using a gradient or block pattern, applies noise, optionally rotates the shape layer, and composites the result on top of the supplied image and mask.
        
        Parameters that need clarification:
        - component_scale: fraction of the canvas used to compute the maximum shape size.
        - palette, harmony_colors, colorized_hue: control color selection; harmony_colors may bias palette choices and colorized_hue tints colorized palettes.
        - pos_bias, size_dist, arrangement, arrangement_params: control where and how the shape is placed and sized (bias strategies, distribution for sizes, and arrangement modes like spiral/burst/grid).
        - rotation (bool): enables random rotation (0–359°) for applicable shapes.
        - opacity: shape fill/stroke opacity in [0.0, 1.0].
        - noise_level, noise_scale, noise_color, noise_rng: control additive noise applied to the shape layer (noise_rng is the RNG used to generate noise; noise_color may be "random", "colored", or "monochrome").
        - fill_mode: "none", "gradient", or "blocks" — determines filling behavior for fillable shapes.
        
        Returns:
            tuple (PIL.Image.Image, PIL.Image.Image): (composited_image, combined_mask)
            - composited_image: the original image with the rendered shape composited on top (RGBA input is alpha-composited).
            - combined_mask: the original mask lightened with the new shape's mask (mode 'L').
        """
        shape_layer = Image.new('RGBA', image.size, (0,0,0,0))
        mask_layer = Image.new('L', mask.size, 0)
        shape_draw = ImageDraw.Draw(shape_layer)
        mask_draw = ImageDraw.Draw(mask_layer)

        x1_orig, y1_orig = self.get_biased_position(width, height, pos_bias, arrangement, arrangement_params)
        
        max_size_x = width * component_scale
        max_size_y = height * component_scale
        size_x = self.get_biased_size(max_size_x, size_dist) * np.random.choice([-1, 1])
        size_y = self.get_biased_size(max_size_y, size_dist) * np.random.choice([-1, 1])

        if shape == 'circle':
            size_x = size_y = min(abs(size_x), abs(size_y))

        x2_orig, y2_orig = x1_orig + size_x, y1_orig + size_y

        x1, x2 = min(x1_orig, x2_orig), max(x1_orig, x2_orig)
        y1, y2 = min(y1_orig, y2_orig), max(y1_orig, y2_orig)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        if x1 >= x2: x2 = x1 + 1
        if y1 >= y2: y2 = y1 + 1

        angle = np.random.randint(0, 360) if rotation else 0

        def apply_noise_to_layer(layer, mask):
            """
            Apply additive Gaussian noise to the RGB channels of a layer within a binary mask and return a new image.
            
            Applies per-pixel normal-distributed noise (mean 0, std = 255 * noise_level) generated from the enclosing scope's RNG and noise settings. Noise may be "colored" (independent RGB channels) or "monochrome" (single channel repeated across RGB) depending on the resolved noise_color; if noise_color is "random" the RNG chooses between those two. Noise is generated at a scaled resolution determined by noise_scale and resized to the layer size before application. Noise is added only where the mask equals 255; values are clipped to [0, 255]. The returned image preserves the original image mode (the function temporarily converts to RGBA if needed).
            
            Parameters:
                layer (PIL.Image): source image layer to which noise will be applied.
                mask (PIL.Image or array-like): binary mask where mask==255 indicates pixels that receive noise.
            
            Returns:
                PIL.Image: a new image with noise applied, in the same mode as the input layer.
            """
            if noise_level > 0:
                original_mode = layer.mode
                if original_mode != 'RGBA': layer = layer.convert('RGBA')
                
                layer_np = np.array(layer)
                mask_np = np.array(mask)
                
                noise_w, noise_h = layer.size
                noise_scale_w, noise_scale_h = max(1, int(noise_w / noise_scale)), max(1, int(noise_h / noise_scale))
                
                _noise_color = noise_color
                if _noise_color == "random": _noise_color = noise_rng.choice(["colored", "monochrome"])

                if _noise_color == "colored":
                    noise_shape = (noise_scale_h, noise_scale_w, 3)
                else: # monochrome
                    noise_shape = (noise_scale_h, noise_scale_w, 1)

                noise = noise_rng.normal(0, 255 * noise_level, noise_shape).astype(np.int16)
                if noise.shape[:2] != (noise_h, noise_w):
                    noise = cv2.resize(noise.astype(np.float32), (noise_w, noise_h), interpolation=cv2.INTER_LINEAR)
                    if len(noise.shape) == 2: noise = np.expand_dims(noise, axis=2)
                
                rgb = layer_np[:, :, :3].astype(np.int16)
                rgb[mask_np == 255] += noise[mask_np == 255].astype(np.int16)
                layer_np[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
                
                return Image.fromarray(layer_np, 'RGBA').convert(original_mode)
            return layer

        fillable_shapes = ["rectangle", "ellipse", "circle", "dot", "triangle", "polygon"]
        
        # --- MASK CREATION ---
        if shape in fillable_shapes:
            if shape == "rectangle":
                points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                mask_draw.polygon(points, fill=255)
            elif shape == "triangle":
                points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(3)]
                mask_draw.polygon(points, fill=255)
            elif shape == "polygon":
                num_sides = np.random.randint(5, 9)
                points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(num_sides)]
                mask_draw.polygon(points, fill=255)
            elif shape in ["ellipse", "circle"]:
                bbox = [x1, y1, x2, y2]
                if shape == "circle":
                    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                    size = min(x2 - x1, y2 - y1) / 2
                    bbox = [center_x - size, center_y - size, center_x + size, center_y + size]
                mask_draw.ellipse(bbox, fill=255)
            elif shape == "dot":
                radius = np.random.randint(1, 10)
                mask_draw.ellipse([x1_orig-radius, y1_orig-radius, x1_orig+radius, y1_orig+radius], fill=255)

        # --- FILLING / DRAWING ---
        if shape in fillable_shapes and fill_mode != 'none':
            bbox = mask_layer.getbbox()
            if bbox:
                bx1, by1, bx2, by2 = bbox
                shape_w, shape_h = bx2 - bx1, by2 - by1
                shape_mask = mask_layer.crop(bbox)

                fill_img = None
                if fill_mode == 'gradient':
                    color1 = self.get_color(palette, harmony_colors, colorized_hue)
                    color2 = self.get_color(palette, harmony_colors, colorized_hue)
                    fill_img = self._create_gradient_fill(shape_w, shape_h, color1, color2, opacity)
                elif fill_mode == 'blocks':
                    fill_img = self._create_blocks_fill(shape_w, shape_h, palette, harmony_colors, colorized_hue, opacity)
                
                if fill_img:
                    shape_layer.paste(fill_img, (bx1, by1), shape_mask)

        elif shape == "concentric_circles":
            center_x, center_y, max_radius, num_circles = x1, y1, min(abs(size_x), abs(size_y)) // 2, np.random.randint(3, 10)
            for i in range(num_circles, 0, -1):
                radius = int(max_radius * (i / num_circles))
                circle_color = self.get_color(palette, harmony_colors, colorized_hue) + (int(255 * opacity),)
                shape_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=circle_color)
                mask_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=255)
        
        else: # Solid fill for fillable shapes, or line-based shapes
            color = self.get_color(palette, harmony_colors, colorized_hue)
            color_with_alpha = color + (int(255 * opacity),)
            
            if shape in fillable_shapes:
                 solid_fill = Image.new('RGBA', image.size, color_with_alpha)
                 shape_layer.paste(solid_fill, (0,0), mask_layer)
            
            elif shape in ["line", "spline"]:
                points = []
                if shape == "line": points = [(x1_orig, y1_orig), (x2_orig, y2_orig)]
                elif shape == "spline": points = [(np.random.randint(0, width), np.random.randint(0, height)) for _ in range(np.random.randint(3, 6))]
                self.draw_pulsating_line(shape_draw, points, color_with_alpha, component_scale, width, height)
                self.draw_pulsating_line(mask_draw, points, 255, component_scale, width, height)

            elif shape == "arc": 
                start_angle, end_angle = np.random.randint(0, 360), np.random.randint(30, 180)
                shape_draw.arc([x1, y1, x2, y2], start=start_angle, end=end_angle, fill=color_with_alpha, width=np.random.randint(1,10))
                mask_draw.arc([x1, y1, x2, y2], start=start_angle, end=end_angle, fill=255, width=np.random.randint(1,10))

            elif shape == "stripes":
                for _ in range(np.random.randint(1, 4)):
                    points = []
                    for edge in random.sample(range(4), 2):
                        if edge == 0: points.append((np.random.randint(0, width), 0))
                        elif edge == 1: points.append((width, np.random.randint(0, height)))
                        elif edge == 2: points.append((np.random.randint(0, width), height))
                        else: points.append((0, np.random.randint(0, height)))
                    stripe_color = self.get_color(palette, harmony_colors, colorized_hue) + (int(255 * opacity),)
                    self.draw_pulsating_line(shape_draw, points, stripe_color, component_scale, width, height)
                    self.draw_pulsating_line(mask_draw, points, 255, component_scale, width, height)

        shape_layer = apply_noise_to_layer(shape_layer, mask_layer)

        if rotation and shape in ["rectangle", "line", "ellipse", "triangle"]:
             center_x = (x1 + x2) / 2
             center_y = (y1 + y2) / 2
             shape_layer = shape_layer.rotate(angle, center=(center_x, center_y), resample=Image.BICUBIC)
             mask_layer = mask_layer.rotate(angle, center=(center_x, center_y), resample=Image.NEAREST)
        
        return Image.alpha_composite(image, shape_layer), ImageChops.lighter(mask, mask_layer)

    def apply_warp(self, image, warp_type, intensity):
        """
        Apply a geometric warp/distortion to a PIL image and return the warped image.
        
        Supported warp types:
        - "none": no change (also returned when intensity == 0).
        - "wave": sinusoidal horizontal and vertical displacement.
        - "noise_field": random displacement field (produces jittery/noisy warp).
        - "swirl": circular swirl centered on the image, with strength decreasing toward the edges.
        
        Parameters:
            image (PIL.Image.Image): Source image to warp.
            warp_type (str): One of "none", "wave", "noise_field", "swirl".
            intensity (float): Relative strength of the effect (0 yields identity). Higher values increase displacement.
        
        Returns:
            PIL.Image.Image: A new PIL image with the requested warp applied. Coordinates are clipped to image bounds and remapped using OpenCV.
        """
        if warp_type == 'none' or intensity == 0: return image
        img_array = np.array(image)
        rows, cols, _ = img_array.shape
        map_x, map_y = np.meshgrid(np.arange(cols), np.arange(rows))
        if warp_type == 'wave':
            map_x = map_x + intensity * 20 * np.sin(2 * np.pi * map_y / 150)
            map_y = map_y + intensity * 20 * np.cos(2 * np.pi * map_x / 150)
        elif warp_type == 'noise_field':
            map_x = map_x + intensity * 30 * (np.random.rand(rows, cols) - 0.5)
            map_y = map_y + intensity * 30 * (np.random.rand(rows, cols) - 0.5)
        elif warp_type == 'swirl':
            center_x, center_y = cols / 2, rows / 2
            dx, dy = map_x - center_x, map_y - center_y
            angle = np.arctan2(dy, dx)
            radius = np.sqrt(dx**2 + dy**2)
            max_radius = np.sqrt(center_x**2 + center_y**2)
            if max_radius > 0:
                normalized_radius = radius / max_radius
                swirl_angle = intensity * 2 * (1 - normalized_radius)
                new_angle = angle + swirl_angle
                map_x = center_x + radius * np.cos(new_angle)
                map_y = center_y + radius * np.sin(new_angle)
        map_x, map_y = np.clip(map_x, 0, cols-1).astype(np.float32), np.clip(map_y, 0, rows-1).astype(np.float32)
        return Image.fromarray(cv2.remap(img_array, map_x, map_y, interpolation=cv2.INTER_LINEAR))

    def generate_image(self, width, height, components, component_scale, shape_string, color_palette, color_harmony, fill_mode, shape_opacity, background_color, positioning_bias, arrangement, size_distribution, allow_rotation, noise_level, noise_scale, noise_color, warp_type, warp_intensity, blur_radius, seed):
        """
        Generate a procedural image composed of randomized shapes and a corresponding binary mask, returning both as PyTorch tensors.
        
        This orchestrates shape selection, placement, fills, optional noise, warping, and final blur/compositing. Randomness is controlled by the provided seed for reproducible outputs. If `background_color` is "random" a random RGB background is chosen. The function validates `shape_string` and will raise a ValueError if no valid shapes are provided. OpenCV (cv2) is required for warp effects and an ImportError is raised if it is missing.
        
        Parameters:
            width (int): Output image width in pixels.
            height (int): Output image height in pixels.
            components (int): Number of shapes to render.
            component_scale (float): Relative maximum size of each shape (used by draw routines).
            shape_string (str): Comma-separated list of shape names to sample from.
            color_palette (str): Palette choice or "random".
            color_harmony (str): Harmony mode or "random".
            fill_mode (str): Multi-color fill mode ("none", "gradient", "blocks") or "random".
            shape_opacity (float): Opacity for shapes in range [0,1].
            background_color (tuple|str): RGB tuple or "random".
            positioning_bias (str): Placement bias strategy or "random".
            arrangement (str): Layout arrangement ("none", "spiral", "burst", "grid") or "random".
            size_distribution (str): Size sampling preference or "random".
            allow_rotation (bool): Whether shapes may be rotated.
            noise_level (float): Strength of per-shape noise (0 disables).
            noise_scale (float): Spatial scale for noise application.
            noise_color (str): "random" or other noise coloring mode used by draw routines.
            warp_type (str): Warp/distortion type or "random".
            warp_intensity (float): Strength of the warp effect (0 disables).
            blur_radius (float): Gaussian blur radius applied to the final RGB image (0 disables).
            seed (int): Seed for Python and NumPy RNGs (ensures deterministic output).
        
        Returns:
            tuple: (image_tensor, mask_tensor)
                - image_tensor (torch.FloatTensor): Float32 RGB tensor with shape (1, H, W, 3) and values in [0,1].
                - mask_tensor (torch.FloatTensor): Float32 single-channel mask tensor with shape (1, H, W) and values in [0,1].
        
        Raises:
            ImportError: If OpenCV (cv2) is not installed but a warp is requested.
            ValueError: If `shape_string` contains no valid shapes.
        """
        random.seed(seed); np.random.seed(seed % (2**32))
        noise_rng = np.random.RandomState(seed % (2**32))

        if background_color == "random":
            background_color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))

        if positioning_bias == "random": positioning_bias = random.choice(self.POSITIONING_BIAS_OPTIONS)
        if arrangement == "random": arrangement = random.choice(self.ARRANGEMENT_OPTIONS)
        colorize_selected = color_palette == "colorized"
        if color_palette == "random": color_palette = random.choice(self.COLOR_PALETTE_OPTIONS)
        if color_harmony == "random": color_harmony = random.choice(self.COLOR_HARMONY_OPTIONS)
        if fill_mode == "random": fill_mode = random.choice(self.MULTI_COLOR_MODE_OPTIONS)
        if size_distribution == "random": size_distribution = random.choice(self.SIZE_DISTRIBUTION_OPTIONS)
        if warp_type == "random": warp_type = random.choice(self.WARP_TYPE_OPTIONS)
        if colorize_selected or color_palette == "colorized":
            colorized_hue = np.random.rand()
        else:
            colorized_hue = None

        try: import cv2
        except ImportError: raise ImportError("OpenCV is required for the warp effect. Please install it with 'pip install opencv-python'.")
        image, mask = Image.new("RGBA", (width, height), background_color), Image.new("L", (width, height), 0)
        harmony_colors = self.get_harmonized_colors(color_harmony) if color_harmony != "none" else []
        available_shapes = [s.strip().lower() for s in shape_string.split(',') if s.strip()]
        if not available_shapes: raise ValueError("Shape string is empty or contains no valid shapes.")
        arrangement_params = {}
        if arrangement == "spiral": arrangement_params['radius_step'] = min(width, height) / (2 * components)
        elif arrangement == "burst": arrangement_params['max_radius'] = min(width, height) / 2
        elif arrangement == "grid":
            aspect_ratio = width / height
            grid_w = int(math.sqrt(components * aspect_ratio))
            grid_h = int(math.sqrt(components / aspect_ratio))
            arrangement_params['grid_w'] = max(1, grid_w)
            arrangement_params['grid_h'] = max(1, grid_h)

        for i in range(components):
            if arrangement == "spiral": arrangement_params['angle'], arrangement_params['radius'] = i * (360 / components) * (math.pi / 180), i * arrangement_params['radius_step']
            elif arrangement == "burst": arrangement_params['angle'] = np.random.uniform(0, 2 * math.pi)
            elif arrangement == "grid": arrangement_params['index'] = i
            current_shape = random.choice(available_shapes)
            image, mask = self.draw_shape(width, height, component_scale, current_shape, color_palette, image, mask, positioning_bias, size_distribution, allow_rotation, harmony_colors, shape_opacity, noise_level, noise_scale, noise_color, arrangement, arrangement_params, fill_mode, noise_rng, colorized_hue)
        
        if warp_type != 'none' and warp_intensity > 0: image = self.apply_warp(image, warp_type, warp_intensity)
        if blur_radius > 0: image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        image = image.convert("RGB")
        image_np, mask_np = np.array(image).astype(np.float32) / 255.0, np.array(mask).astype(np.float32) / 255.0
        image_tensor, mask_tensor = torch.from_numpy(image_np)[None,], torch.from_numpy(mask_np).unsqueeze(0)
        return (image_tensor, mask_tensor)

NODE_CLASS_MAPPINGS = { "ColorfulStartingImage": ColorfulStartingImage }
NODE_DISPLAY_NAME_MAPPINGS = { "ColorfulStartingImage": "🎨 Colorful Starting Image" }