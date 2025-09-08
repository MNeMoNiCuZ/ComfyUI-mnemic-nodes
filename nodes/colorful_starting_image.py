import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

import random
import math
import colorsys
import cv2

class ColorfulStartingImage:
    COLOR_PALETTE_OPTIONS = ["random_color", "muted", "grayscale", "high_contrast"]
    COLOR_HARMONY_OPTIONS = ["none", "complementary", "analogous", "triadic"]
    MULTI_COLOR_MODE_OPTIONS = ["none", "gradient", "random_vertices"]
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
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The width of the generated image in pixels."}),
                "height": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The height of the generated image in pixels."}),
                "components": ("INT", {"default": 20, "min": 1, "tooltip": "The total number of components (shapes) to draw on the image. More components create a more complex image."}),
                "component_scale": ("FLOAT", {"default": 0.5, "min": 0.01, "step": 0.01, "tooltip": "Controls the maximum potential size of shapes. A shape's max width is `image_width * component_scale`.\nExample: With a 1024px wide image and 0.5 scale, the largest shapes will be around 512px wide."} ),
                "shape_string": ("STRING", {"default": "rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, gradient_rectangle, concentric_circles", "multiline": True, "tooltip": "A comma-separated list of shapes to draw from.\n\nAvailable shapes:\n- rectangle, ellipse, circle, line, spline, dot, stripes, triangle, polygon, arc, gradient_rectangle, concentric_circles"}),
                "color_palette": (["random"] + s.COLOR_PALETTE_OPTIONS, {"tooltip": "The color palette for the shapes.\n\nOptions:\n- random: Picks one of the other palette options at random for each generation.\n- random_color: Any RGB color.\n- muted: Less saturated, softer colors.\n- grayscale: Shades of gray.\n- high_contrast: Pure black and white."}),
                "color_harmony": (["random"] + s.COLOR_HARMONY_OPTIONS, {"tooltip": "Apply a color harmony rule to the generated colors.\n\nOptions:\n- none: No harmony.\n- complementary: Colors from opposite sides of the color wheel.\n- analogous: Colors next to each other on the color wheel.\n- triadic: Three colors evenly spaced around the color wheel."}),
                "multi_color_mode": (["random"] + s.MULTI_COLOR_MODE_OPTIONS, {"tooltip": "Fill shapes with multiple colors.\n\nOptions:\n- none: Shapes are filled with a single color.\n- gradient: Creates a two-color linear gradient.\n- random_vertices: Assigns a random color to each corner of a polygon."}),
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
        base_hue = np.random.rand()
        if harmony == "complementary": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.5) % 1]]
        if harmony == "analogous": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.083) % 1, (base_hue - 0.083) % 1]]
        if harmony == "triadic": return [colorsys.hsv_to_rgb(h, np.random.uniform(0.5, 1), np.random.uniform(0.5, 1)) for h in [base_hue, (base_hue + 0.333) % 1, (base_hue - 0.333) % 1]]
        return []

    def get_color(self, palette, harmony_colors):
        if harmony_colors: color = random.choice(harmony_colors); return (int(color[0]*255), int(color[1]*255), int(color[2]*255))
        if palette == "muted": return (np.random.randint(50, 200), np.random.randint(50, 200), np.random.randint(50, 200))
        if palette == "grayscale": val = np.random.randint(0, 255); return (val, val, val)
        if palette == "high_contrast": return (0,0,0) if np.random.rand() > 0.5 else (255,255,255)
        return (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))

    def get_biased_position(self, width, height, bias, arrangement, arrangement_params):
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
        if distribution == "prefer_small": return int(abs(np.random.normal(0, max_size / 3))) + 1
        if distribution == "prefer_large":
            val = int(max_size - abs(np.random.normal(0, max_size / 3)))
            return max(1, val)
        return np.random.randint(1, max(2, int(max_size)))

    def draw_pulsating_line(self, draw, points, color, component_scale, width, height):
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

    def draw_shape(self, width, height, component_scale, shape, palette, image, mask, pos_bias, size_dist, rotation, harmony_colors, opacity, noise_level, noise_scale, noise_color, arrangement, arrangement_params, multi_color_mode, noise_rng):
        color = self.get_color(palette, harmony_colors)
        color_with_alpha = color + (int(255 * opacity),)
        
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

        if shape in ["line", "spline"]:
            points = []
            if shape == "line":
                points = [(x1_orig, y1_orig), (x2_orig, y2_orig)]
            elif shape == "spline":
                points = [(np.random.randint(0, width), np.random.randint(0, height)) for _ in range(np.random.randint(3, 6))]
            
            self.draw_pulsating_line(shape_draw, points, color_with_alpha, component_scale, width, height)
            self.draw_pulsating_line(mask_draw, points, 255, component_scale, width, height)

        elif shape in ["rectangle", "ellipse", "circle", "dot", "triangle", "polygon"]:
            points = []
            if shape == "rectangle": points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            elif shape == "triangle": points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(3)]
            elif shape == "polygon": num_sides = np.random.randint(5, 9); points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(num_sides)]

            if shape in ["rectangle", "triangle", "polygon"]:
                shape_draw.polygon(points, fill=color_with_alpha)
                mask_draw.polygon(points, fill=255)
            elif shape in ["ellipse", "circle"]:
                if shape == "circle":
                    # Ensure the bounding box is square for circles
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    size = min(x2 - x1, y2 - y1) / 2
                    x1, x2 = center_x - size, center_x + size
                    y1, y2 = center_y - size, center_y + size
                shape_draw.ellipse([x1, y1, x2, y2], fill=color_with_alpha)
                mask_draw.ellipse([x1, y1, x2, y2], fill=255)
            elif shape == "dot":
                radius = np.random.randint(1, 10)
                shape_draw.ellipse([x1_orig-radius, y1_orig-radius, x1_orig+radius, y1_orig+radius], fill=color_with_alpha)
                mask_draw.ellipse([x1_orig-radius, y1_orig-radius, x1_orig+radius, y1_orig+radius], fill=255)

        elif shape == "arc": 
            start_angle = np.random.randint(0, 360)
            end_angle = start_angle + np.random.randint(30, 180)
            shape_draw.arc([x1, y1, x2, y2], start=start_angle, end=end_angle, fill=color_with_alpha, width=np.random.randint(1,10))
            mask_draw.arc([x1, y1, x2, y2], start=start_angle, end=end_angle, fill=255, width=np.random.randint(1,10))

        elif shape == "stripes":
            num_stripes = np.random.randint(1, 4)
            for _ in range(num_stripes):
                points = []
                edge1 = np.random.randint(0, 4)
                edge2 = (edge1 + np.random.randint(1, 4)) % 4
                
                edges = [edge1, edge2]
                for edge in edges:
                    if edge == 0: # Top
                        points.append((np.random.randint(0, width), 0))
                    elif edge == 1: # Right
                        points.append((width, np.random.randint(0, height)))
                    elif edge == 2: # Bottom
                        points.append((np.random.randint(0, width), height))
                    else: # Left
                        points.append((0, np.random.randint(0, height)))

                stripe_color = self.get_color(palette, harmony_colors) + (int(255 * opacity),)
                self.draw_pulsating_line(shape_draw, points, stripe_color, component_scale, width, height)
                self.draw_pulsating_line(mask_draw, points, 255, component_scale, width, height)

        elif shape == "gradient_rectangle" or (shape == "rectangle" and multi_color_mode == 'gradient'):
            color1, color2 = self.get_color(palette, harmony_colors), self.get_color(palette, harmony_colors)
            for i in range(y1, y2):
                ratio = (i - y1) / (y2 - y1) if (y2 - y1) != 0 else 0
                r,g,b = [int(c1 * (1 - ratio) + c2 * ratio) for c1,c2 in zip(color1, color2)]
                shape_draw.line([(x1, i), (x2, i)], fill=(r, g, b, int(255 * opacity)))
            mask_draw.rectangle([x1, y1, x2, y2], fill=255)

        elif shape == "concentric_circles":
            center_x, center_y, max_radius, num_circles = x1, y1, min(abs(size_x), abs(size_y)) // 2, np.random.randint(3, 10)
            for i in range(num_circles, 0, -1):
                radius = int(max_radius * (i / num_circles))
                circle_color = self.get_color(palette, harmony_colors) + (int(255 * opacity),)
                shape_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=circle_color)
                mask_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=255)
        
        shape_layer = apply_noise_to_layer(shape_layer, mask_layer)


        if rotation and shape in ["rectangle", "line", "ellipse", "triangle"]:
             center_x = (x1 + x2) / 2
             center_y = (y1 + y2) / 2
             shape_layer = shape_layer.rotate(angle, center=(center_x, center_y), resample=Image.BICUBIC)
             mask_layer = mask_layer.rotate(angle, center=(center_x, center_y), resample=Image.NEAREST)
        
        return Image.alpha_composite(image, shape_layer), ImageChops.lighter(mask, mask_layer)

    def apply_warp(self, image, warp_type, intensity):
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

    def generate_image(self, width, height, components, component_scale, shape_string, color_palette, color_harmony, multi_color_mode, shape_opacity, background_color, positioning_bias, arrangement, size_distribution, allow_rotation, noise_level, noise_scale, noise_color, warp_type, warp_intensity, blur_radius, seed):
        random.seed(seed); np.random.seed(seed % (2**32))
        noise_rng = np.random.RandomState(seed % (2**32))

        if background_color == "random":
            background_color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))

        if positioning_bias == "random": positioning_bias = random.choice(self.POSITIONING_BIAS_OPTIONS)
        if arrangement == "random": arrangement = random.choice(self.ARRANGEMENT_OPTIONS)
        if color_palette == "random": color_palette = random.choice(self.COLOR_PALETTE_OPTIONS)
        if color_harmony == "random": color_harmony = random.choice(self.COLOR_HARMONY_OPTIONS)
        if multi_color_mode == "random": multi_color_mode = random.choice(self.MULTI_COLOR_MODE_OPTIONS)
        if size_distribution == "random": size_distribution = random.choice(self.SIZE_DISTRIBUTION_OPTIONS)
        if warp_type == "random": warp_type = random.choice(self.WARP_TYPE_OPTIONS)

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
            image, mask = self.draw_shape(width, height, component_scale, current_shape, color_palette, image, mask, positioning_bias, size_distribution, allow_rotation, harmony_colors, shape_opacity, noise_level, noise_scale, noise_color, arrangement, arrangement_params, multi_color_mode, noise_rng)
        
        if warp_type != 'none' and warp_intensity > 0: image = self.apply_warp(image, warp_type, warp_intensity)
        if blur_radius > 0: image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        image = image.convert("RGB")
        image_np, mask_np = np.array(image).astype(np.float32) / 255.0, np.array(mask).astype(np.float32) / 255.0
        image_tensor, mask_tensor = torch.from_numpy(image_np)[None,], torch.from_numpy(mask_np).unsqueeze(0)
        return (image_tensor, mask_tensor)

NODE_CLASS_MAPPINGS = { "ColorfulStartingImage": ColorfulStartingImage }
NODE_DISPLAY_NAME_MAPPINGS = { "ColorfulStartingImage": "🎨 Colorful Starting Image" }