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
        Return the INPUT_TYPES mapping used by the node system to describe this node's inputs.
        
        Provides a dictionary with a single "required" key mapping input names to type descriptors and metadata (default, min/max/step, tooltips, option lists). Notable inputs and behaviors:
        - width, height: image dimensions in pixels.
        - components, component_scale: number of shapes and maximum relative shape size.
        - shape_string: comma-separated list of shapes (multiline); supported shapes include rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, concentric_circles.
        - color_palette, color_harmony, fill_mode, positioning_bias, arrangement, size_distribution, warp_type: accept "random" plus predefined option lists from the class constants (e.g., COLOR_PALETTE_OPTIONS).
        - background_color: accepts color names or hex codes; the literal "random" selects a random background color.
        - noise_* and warp_intensity/blur_radius: control visual noise, warp, and blur post-processing.
        - seed: deterministic seed — using the same seed and parameters reproduces the same image.
        
        The returned structure is consumed by the host node system to build UI controls and validate inputs.
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
        Return a list of RGB colors generated according to the specified color harmony.
        
        Generates a random base hue and produces colors following the given harmony scheme:
        - "complementary": base hue and its opposite (±0.5).
        - "analogous": base hue and two nearby hues (±0.083).
        - "triadic": three hues spaced ~120° apart (±0.333).
        - "tetradic": four hues spaced ~90° apart (0.25, 0.5, 0.75).
        
        Saturation and value (brightness) for each generated color are randomized in the range [0.5, 1.0]. Colors are returned as (r, g, b) tuples with float components in [0.0, 1.0]. If the harmony is not recognized, an empty list is returned.
        
        Parameters:
            harmony (str): One of "complementary", "analogous", "triadic", "tetradic".
        
        Returns:
            list[tuple[float, float, float]]: List of RGB tuples (floats in [0, 1]) matching the requested harmony, or [] if unknown.
        """
        base_hue = np.random.rand()
        if harmony == "complementary": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.5) % 1]]
        if harmony == "analogous": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.083) % 1, (base_hue - 0.083) % 1]]
        if harmony == "triadic": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.333) % 1, (base_hue - 0.333) % 1]]
        if harmony == "tetradic": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.25) % 1, (base_hue + 0.5) % 1, (base_hue + 0.75) % 1]]
        return []

    def get_color(self, palette, harmony_colors, colorized_hue=None):
        """
        Return an RGB color tuple (R, G, B) in 0–255 range according to the requested palette and optional harmony hints.
        
        Detailed behavior:
        - If `harmony_colors` is provided, colors from that harmony list are preferred for most palettes:
          - For "grayscale" with harmony, uses a harmony hue but maps it to a grayscale-lightness value.
          - For "binary" with harmony, uses a harmony hue and returns a tinted black or white.
          - Otherwise returns a random color from `harmony_colors` converted to 0–255 integers.
        - Palette-specific fallbacks when `harmony_colors` is empty or not used:
          - "muted": random mid-range RGB values (50–199).
          - "grayscale": uniform gray value.
          - "binary": pure black or white.
          - "neon": high-saturation HSV-to-RGB color (bright).
          - "pastel": low-saturation, bright HSV-to-RGB color.
          - "colorized": tints a grayscale value using `colorized_hue` (or a random hue if None).
          - Default: a fully random RGB triple.
        
        Parameters:
            palette (str): Named palette to use (e.g., "muted", "grayscale", "binary", "neon", "pastel", "colorized").
            harmony_colors (Sequence[tuple] | None): Optional list of harmony colors as floats in [0,1] RGB tuples; when present many palettes favor or sample from these.
            colorized_hue (float | None): Hue in [0,1] used only for the "colorized" palette; if None a random hue is chosen.
        
        Returns:
            tuple[int, int, int]: RGB color with each channel in 0–255.
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
        Return a biased (x, y) pixel position inside an image given width/height.
        
        Computes a position according to either an explicit arrangement (spiral, burst, grid) — which takes precedence — or a placement bias (center_weighted, edge_weighted, grid_aligned, random_weighted, compass directions, corners, or default random). Positions are sampled with randomness (normal/uniform) appropriate to the selected strategy and are clamped to the image bounds before being returned.
        
        Parameters:
            width (int): Image width in pixels.
            height (int): Image height in pixels.
            bias (str): Placement bias name used when arrangement == "none". Supported values include
                "center_weighted", "edge_weighted", "grid_aligned", "random_weighted",
                "north", "south", "east", "west", "north_west", "north_east",
                "south_west", "south_east". Any other value falls back to uniform random.
            arrangement (str): Global arrangement mode. If not "none", takes precedence and may be
                "spiral", "burst", or "grid".
            arrangement_params (dict): Parameters required by the chosen arrangement:
                - spiral: {'angle', 'radius'}
                - burst: {'angle', 'max_radius'}
                - grid: {'grid_w', 'grid_h', 'index'} (grid cell computed from index)
        
        Returns:
            tuple[int, int]: (x, y) position clamped to [0, width] x [0, height].
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
        Return an integer size for a shape biased by the requested distribution.
        
        If distribution == "prefer_small", samples a half-normal-like value (absolute value of a normal with std = max_size/3),
        adds 1, and returns that as the size (favoring small sizes but >= 1).
        
        If distribution == "prefer_large", samples a half-normal-like value and subtracts it from max_size to bias toward larger
        sizes; the result is clamped to a minimum of 1.
        
        For any other distribution, returns a uniform random integer in [1, max(1, max_size-1)] (ensures at least 1).
        
        Parameters:
            max_size (int): The maximum allowed size for the shape (used as scale for biasing).
            distribution (str): One of "prefer_small", "prefer_large", or other (treated as uniform).
        
        Returns:
            int: A positive integer size (>= 1) biased according to distribution.
        """
        if distribution == "prefer_small": return int(abs(np.random.normal(0, max_size / 3))) + 1
        if distribution == "prefer_large":
            val = int(max_size - abs(np.random.normal(0, max_size / 3)))
            return max(1, val)
        return np.random.randint(1, max(2, int(max_size)))

    def draw_pulsating_line(self, draw, points, color, component_scale, width, height):
        """
        Draw a filled "pulsating" polyline by constructing and filling a variable-thickness polygon along consecutive points.
        
        The function approximates a thick, wavy stroke between each pair of consecutive points by sampling segments along the segment, computing a perpendicular offset whose magnitude oscillates (sinusoidally) to produce a pulsating/throbbing thickness, and filling the resulting polygon on the provided drawing context. No action is taken if fewer than two points are provided. Random variation in pulsation frequency and base thickness is used for visual variety.
        
        Parameters:
            draw: PIL.ImageDraw.Draw
                Drawing context to render the polygon onto.
            points: Sequence[tuple[float, float]]
                Ordered list of (x, y) coordinates defining the polyline.
            color: tuple|str
                Fill color for the polygon (e.g., RGB tuple or color string).
            component_scale: float
                Scale factor used to compute maximum stroke thickness relative to image size.
            width: int
                Full image width (used to compute thickness).
            height: int
                Full image height (used to compute thickness).
        
        Returns:
            None
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
        Create a vertical RGBA gradient image interpolating between two RGB colors.
        
        The gradient transitions from color1 at the top to color2 at the bottom and has a uniform alpha channel set by opacity.
        
        Parameters:
            width (int): Image width in pixels.
            height (int): Image height in pixels.
            color1 (Sequence[int]): Top color as an (R, G, B) tuple or sequence with 0–255 values.
            color2 (Sequence[int]): Bottom color as an (R, G, B) tuple or sequence with 0–255 values.
            opacity (float): Alpha value applied uniformly to the whole image, in range [0.0, 1.0].
        
        Returns:
            PIL.Image.Image: An RGBA PIL Image of shape (width, height) containing the vertical gradient.
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
        Create a vertical segmented fill made of colored blocks (stripes).
        
        Each image-wide vertical strip is filled with a color sampled from the configured palette/harmony and rendered with the given opacity.
        
        Parameters:
            width (int): Width of the fill image in pixels.
            height (int): Height of the fill image in pixels.
            palette (str): Name of the color palette to sample from.
            harmony_colors (list|None): Optional list of harmony colors to bias sampling.
            colorized_hue (float|None): Optional hue to use when the palette requests a colorized tint.
            opacity (float): Opacity for the blocks in range [0.0, 1.0].
        
        Returns:
            PIL.Image.Image: An RGBA image of size (width, height) containing vertical color blocks.
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
        Render a single shape onto the provided image and update its mask.
        
        Creates an RGBA shape layer and a grayscale mask layer, computes a biased position and size, constructs the shape mask, fills or draws the shape according to the selected fill_mode (solid, gradient, or blocks) or as line-based geometry (line, spline, arc, stripes), optionally applies per-pixel noise, optionally rotates the shape layer, and composites the result over the input image and mask.
        
        Key behaviors:
        - Supported shapes: rectangle, ellipse, circle, dot, triangle, polygon, concentric_circles, line, spline, arc, stripes.
        - Fill modes:
          - 'none' — draws geometry (lines/arcs/stripes) or solid fills for fillable shapes.
          - 'gradient' — uses _create_gradient_fill to produce a two-color gradient fill.
          - 'blocks' — uses _create_blocks_fill to produce vertical color blocks.
        - Color selection for fills and strokes is performed via get_color(...) and may use harmony_colors and colorized_hue when provided.
        - Noise: when noise_level > 0, a Gaussian noise field (generated with noise_rng) is added only to pixels inside the shape mask; noise can be 'colored' or 'monochrome' (or chosen at random). Noise resizing uses OpenCV.
        - Rotation: when rotation is True, the layer and mask are rotated around the shape center; rotation is applied only to certain shapes (rectangle, line, ellipse, triangle).
        - Bounds: shape bounding boxes are clamped to image bounds and degenerate boxes are expanded to at least 1 pixel.
        - Returns a tuple (composited_image, merged_mask) where composited_image is the input image with the drawn shape composited on top and merged_mask is the lighter blend of the input mask and the new shape's mask.
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
            Apply Gaussian noise to the RGB channels of a PIL image layer, restricted to the white (255) areas of a mask.
            
            This function:
            - If noise_level <= 0, returns the input layer unchanged.
            - Generates noise with a normal distribution (mean=0, std=255 * noise_level).
            - Supports "colored" noise (per-channel) and "monochrome" noise (single channel replicated).
            - When noise_color == "random", chooses between "colored" and "monochrome" via noise_rng.
            - Produces the noise at a reduced resolution controlled by noise_scale, then resizes it to the layer size with linear interpolation.
            - Adds the noise only where mask pixels equal 255, clamps RGB values to [0,255], and preserves the original image mode.
            
            Parameters:
                layer (PIL.Image.Image): RGBA-capable image to which noise will be applied.
                mask (PIL.Image.Image): Single-channel mask; regions with value 255 receive noise.
            
            Returns:
                PIL.Image.Image: A new image with noise applied (converted back to the original mode).
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
        Apply a geometric warp/distortion to a PIL image and return the warped image as a new PIL Image.
        
        Supports three warp modes:
        - "wave": applies sinusoidal horizontal and vertical displacements.
        - "noise_field": applies a randomized displacement field.
        - "swirl": applies a center-based swirl whose strength falls off with radius.
        
        Parameters:
            image (PIL.Image.Image): Source image to warp (converted internally to a NumPy array).
            warp_type (str): One of "none", "wave", "noise_field", or "swirl". If "none", the original image is returned.
            intensity (float): Scalar controlling the strength of the effect (0 yields no change).
        
        Returns:
            PIL.Image.Image: A new image with the requested warp applied. Pixel sampling uses bilinear interpolation; out-of-bounds coordinates are clamped to the image extent.
        
        Notes:
        - If warp_type == "none" or intensity == 0 the original image is returned unchanged.
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
        Generate a colorful procedurally composed image and its mask as PyTorch tensors.
        
        Generates `components` shapes on an RGBA canvas of size (width, height) using the specified palettes, harmony, arrangement, positioning bias, fills, optional per-shape noise, rotation, post-warping, and blur. The routine seeds Python and NumPy RNGs from `seed` for deterministic output. The final image is returned as an RGB tensor normalized to [0, 1] and the mask as a single-channel tensor normalized to [0, 1].
        
        Parameters:
            width, height (int): Output image size in pixels.
            components (int): Number of shapes to draw.
            component_scale (float): Global scale factor applied when sizing shapes.
            shape_string (str): Comma-separated shape names to choose from; raises ValueError if empty.
            color_palette (str): Palette name (or "random"); "colorized" uses a single hue tint.
            color_harmony (str): Harmony scheme (or "random"); "none" disables harmonization.
            fill_mode (str): Fill strategy for multi-color shapes ("none", "gradient", "blocks", or "random").
            shape_opacity (float): Per-shape opacity in [0,1].
            background_color (str or tuple): RGB tuple or "random".
            positioning_bias (str): Placement bias strategy (or "random").
            arrangement (str): Global arrangement mode (or "random") such as "spiral", "burst", or "grid".
            size_distribution (str): Size bias ("uniform", "prefer_small", "prefer_large", or "random").
            allow_rotation (bool): If True, individual shapes may be rotated.
            noise_level (float): Strength of per-shape Gaussian noise (0 disables).
            noise_scale (float): Spatial scale for noise application.
            noise_color (bool): If True, noise affects color channels.
            warp_type (str): Warp effect to apply after composition ("none", "wave", "noise_field", "swirl", or "random").
            warp_intensity (float): Strength of the warp effect (0 disables).
            blur_radius (float): Gaussian blur radius applied after warping (0 disables).
            seed (int): Seed for deterministic random generation.
        
        Returns:
            tuple: (image_tensor, mask_tensor)
              - image_tensor (torch.Tensor): Float32 tensor shape (1, H, W, 3) with values in [0,1].
              - mask_tensor (torch.Tensor): Float32 tensor shape (1, H, W) with values in [0,1].
        
        Raises:
            ImportError: If OpenCV is required for the selected warp and not installed.
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