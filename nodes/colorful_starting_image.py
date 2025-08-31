import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import comfy.model_management as model_management
import random
import math
import colorsys
import cv2

class ColorfulStartingImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The width of the generated image in pixels."}),
                "height": ("INT", {"default": 1024, "min": 64, "step": 64, "tooltip": "The height of the generated image in pixels."}),
                "layers": ("INT", {"default": 20, "min": 1, "tooltip": "The total number of shapes to draw on the image."}),
                "density": ("FLOAT", {"default": 0.5, "min": 0.01, "step": 0.01, "tooltip": "Controls the maximum size of the shapes."}),
                "shape_string": ("STRING", {"default": "rectangle, ellipse, line, spline, dot, stripes, triangle, polygon, arc, gradient_rectangle, concentric_circles", "multiline": True, "tooltip": "A comma-separated list of shapes to draw."}),
                "color_palette": (["random", "muted", "grayscale", "high_contrast"], {"tooltip": "The color palette for the shapes."}),
                "color_harmony": (["none", "complementary", "analogous", "triadic"], {"tooltip": "Apply a color harmony rule."}),
                "multi_color_mode": (["none", "gradient", "random_vertices"], {"tooltip": "Fill shapes with multiple colors. 'gradient' creates a two-color gradient, 'random_vertices' assigns a random color to each corner of a polygon."}),
                "shape_opacity": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.05, "tooltip": "The opacity of the drawn shapes."}),
                "background_color": ("STRING", {"default": "black", "tooltip": "The background color (name or hex)."}),
                "positioning_bias": (["fully_random", "center_weighted", "edge_weighted", "grid_aligned", "random_weighted"], {"tooltip": "Controls where shapes are likely to appear."}),
                "size_distribution": (["uniform", "prefer_small", "prefer_large"], {"tooltip": "Controls the distribution of shape sizes."}),
                "allow_rotation": ("BOOLEAN", {"default": True, "tooltip": "Allow random rotation of shapes."}),
                "stroke_width": ("INT", {"default": 0, "min": 0, "step": 1, "tooltip": "If > 0, draw outlines instead of filled shapes."}),
                "noise_level": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "Fill shapes with noisy texture."}),
                "controlled_chaos": (["none", "spiral", "burst", "grid"], {"tooltip": "Arrange shapes in a structured pattern."}),
                "color_bleed": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1, "tooltip": "Intensity of the color bleed/watercolor effect."}),
                "warp_type": (["none", "wave", "turbulence", "swirl"], {"tooltip": "Type of distortion to apply to the final image."}),
                "warp_intensity": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1, "tooltip": "Strength of the distortion effect."}),
                "blur_radius": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1, "tooltip": "Radius of the final Gaussian blur."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed for the random number generator."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "LATENT", "MASK")
    RETURN_NAMES = ("image", "latent", "mask")
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

    def get_biased_position(self, width, height, bias, chaos_mode, chaos_params):
        if chaos_mode != "none":
            if chaos_mode == "spiral":
                angle, radius = chaos_params['angle'], chaos_params['radius']
                return (int(width / 2 + radius * math.cos(angle)), int(height / 2 + radius * math.sin(angle)))
            if chaos_mode == "burst":
                angle, max_radius = chaos_params['angle'], chaos_params['max_radius']
                radius = np.random.uniform(0, max_radius)
                return (int(width / 2 + radius * math.cos(angle)), int(height / 2 + radius * math.sin(angle)))
            if chaos_mode == "grid":
                grid_size, index = 10, chaos_params['index']
                return ((index % grid_size) * (width // grid_size) + np.random.randint(0, width//grid_size), (index // grid_size) * (height // grid_size) + np.random.randint(0, height//grid_size))
        if bias == "center_weighted": x, y = int(np.random.normal(width / 2, width / 6)), int(np.random.normal(height / 2, height / 6))
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
        else: x, y = np.random.randint(0, width), np.random.randint(0, height)
        return (max(0, min(width, x)), max(0, min(height, y)))

    def get_biased_size(self, max_size, distribution):
        if distribution == "prefer_small": return int(abs(np.random.normal(0, max_size / 3))) + 10
        if distribution == "prefer_large": return int(max_size - abs(np.random.normal(0, max_size / 3)))
        return np.random.randint(10, max(11, max_size))

    def create_noisy_fill(self, color, size, noise_level):
        noise = np.random.normal(0, 255 * noise_level, size + (3,)).astype(np.int16)
        base_color = np.array(color, dtype=np.int16)
        noisy_color = np.clip(base_color + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_color, 'RGB')

    def draw_shape(self, width, height, density, shape, palette, image, mask, pos_bias, size_dist, rotation, harmony_colors, opacity, stroke_width, noise_level, chaos_mode, chaos_params, multi_color_mode):
        color = self.get_color(palette, harmony_colors)
        color_with_alpha = color + (int(255 * opacity),)
        fill, outline = (None, color_with_alpha) if stroke_width > 0 else (color_with_alpha, None)
        shape_layer, mask_layer = Image.new('RGBA', image.size, (0,0,0,0)), Image.new('L', mask.size, 0)
        shape_draw, mask_draw = ImageDraw.Draw(shape_layer), ImageDraw.Draw(mask_layer)
        x1, y1 = self.get_biased_position(width, height, pos_bias, chaos_mode, chaos_params)
        max_size = int(min(width, height) * density)
        size_x, size_y = self.get_biased_size(max_size, size_dist), self.get_biased_size(max_size, size_dist)
        x2, y2 = x1 + size_x, y1 + size_y
        angle = np.random.randint(0, 360) if rotation else 0

        def draw_on_layers(draw_func, *args, **kwargs):
            if noise_level > 0 and fill is not None and multi_color_mode == 'none':
                temp_mask = Image.new('L', image.size, 0)
                temp_draw = ImageDraw.Draw(temp_mask)
                draw_func(temp_draw, *args, fill=255, **kwargs)
                noisy_texture = self.create_noisy_fill(color, image.size, noise_level)
                shape_layer.paste(noisy_texture, (0,0), temp_mask)
            else: draw_func(shape_draw, *args, fill=fill, **kwargs)
            draw_func(mask_draw, *args, fill=255, **kwargs)

        if shape in ["rectangle", "ellipse", "dot", "triangle", "polygon"]:
            points = []
            if shape == "rectangle": points = [(x1,y1), (x2,y1), (x2,y2), (x1,y2)]
            elif shape == "triangle": points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(3)]
            elif shape == "polygon": num_sides = np.random.randint(5, 9); points = [(np.random.randint(x1,x2), np.random.randint(y1,y2)) for _ in range(num_sides)]
            
            if multi_color_mode == 'random_vertices' and points and fill:
                temp_mask = Image.new('L', image.size, 0)
                ImageDraw.Draw(temp_mask).polygon(points, fill=255)
                colors = [self.get_color(palette, harmony_colors) for _ in points]
                # This is a simplified gradient mesh, not a true one.
                for i in range(width):
                    for j in range(height):
                        if temp_mask.getpixel((i,j)) == 255:
                            dists = [math.sqrt((i-p[0])**2 + (j-p[1])**2) for p in points]
                            total_dist = sum(dists)
                            if total_dist == 0: continue
                            weights = [d/total_dist for d in dists]
                            r = sum(c[0] * w for c, w in zip(colors, weights))
                            g = sum(c[1] * w for c, w in zip(colors, weights))
                            b = sum(c[2] * w for c, w in zip(colors, weights))
                            shape_layer.putpixel((i,j), (int(r), int(g), int(b), int(255*opacity)))
                mask_draw.polygon(points, fill=255)
            elif shape == "rectangle": draw_on_layers(lambda d, *a, **k: d.rectangle(*a, **k), [x1, y1, x2, y2], width=stroke_width, outline=outline)
            elif shape == "ellipse": draw_on_layers(lambda d, *a, **k: d.ellipse(*a, **k), [x1, y1, x2, y2], width=stroke_width, outline=outline)
            elif shape == "dot": radius = np.random.randint(1, 10); draw_on_layers(lambda d, *a, **k: d.ellipse(*a, **k), [x1-radius, y1-radius, x1+radius, y1+radius], width=stroke_width, outline=outline)
            elif shape == "triangle": draw_on_layers(lambda d, *a, **k: d.polygon(*a, **k), points, outline=outline)
            elif shape == "polygon": draw_on_layers(lambda d, *a, **k: d.polygon(*a, **k), points, outline=outline)
        elif shape == "line": draw_on_layers(lambda d, *a, **k: d.line(*a, **k), [x1, y1, x2, y2], width=stroke_width or np.random.randint(1,10))
        elif shape == "spline": points = [(np.random.randint(0, width), np.random.randint(0, height)) for _ in range(np.random.randint(3, 6))]; draw_on_layers(lambda d, *a, **k: d.line(*a, **k), points, width=stroke_width or np.random.randint(1,5), joint="curve")
        elif shape == "arc": start_angle = np.random.randint(0, 360); end_angle = start_angle + np.random.randint(30, 180); draw_on_layers(lambda d, *a, **k: d.arc(*a, **k), [x1, y1, x2, y2], start=start_angle, end=end_angle, width=stroke_width or np.random.randint(1,10))
        elif shape == "stripes":
            for i in range(0, width + height, 20):
                stripe_color = self.get_color(palette, harmony_colors) + (int(255 * opacity),)
                shape_draw.line([(i, 0), (0, i)], fill=stripe_color, width=stroke_width or np.random.randint(1, 5))
                mask_draw.line([(i, 0), (0, i)], fill=255, width=stroke_width or np.random.randint(1, 5))
        elif shape == "gradient_rectangle" or (shape == "rectangle" and multi_color_mode == 'gradient'):
            color1, color2 = self.get_color(palette, harmony_colors), self.get_color(palette, harmony_colors)
            for i in range(y1, y2):
                ratio = (i - y1) / (y2 - y1)
                r,g,b = [int(c1 * (1 - ratio) + c2 * ratio) for c1,c2 in zip(color1, color2)]
                shape_draw.line([(x1, i), (x2, i)], fill=(r, g, b, int(255 * opacity)))
            mask_draw.rectangle([x1, y1, x2, y2], fill=255)
        elif shape == "concentric_circles":
            center_x, center_y, max_radius, num_circles = x1, y1, min(size_x, size_y) // 2, np.random.randint(3, 10)
            for i in range(num_circles, 0, -1):
                radius = int(max_radius * (i / num_circles))
                circle_color = self.get_color(palette, harmony_colors) + (int(255 * opacity),)
                shape_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=circle_color if fill is not None else None, outline=outline, width=stroke_width)
                mask_draw.ellipse([center_x-radius, center_y-radius, center_x+radius, center_y+radius], fill=255)
        
        if rotation and shape in ["rectangle", "line"]:
             shape_layer = shape_layer.rotate(angle, center=(x1, y1), resample=Image.BICUBIC)
             mask_layer = mask_layer.rotate(angle, center=(x1, y1), resample=Image.NEAREST)
        return Image.alpha_composite(image, shape_layer), Image.max(mask, mask_layer)

    def apply_warp(self, image, warp_type, intensity):
        if warp_type == 'none' or intensity == 0: return image
        img_array = np.array(image)
        rows, cols, _ = img_array.shape
        map_x, map_y = np.meshgrid(np.arange(cols), np.arange(rows))
        if warp_type == 'wave':
            map_x = map_x + intensity * 20 * np.sin(2 * np.pi * map_y / 150)
            map_y = map_y + intensity * 20 * np.cos(2 * np.pi * map_x / 150)
        elif warp_type == 'turbulence':
            map_x = map_x + intensity * 30 * (np.random.rand(rows, cols) - 0.5)
            map_y = map_y + intensity * 30 * (np.random.rand(rows, cols) - 0.5)
        elif warp_type == 'swirl':
            center_x, center_y = cols / 2, rows / 2
            dx, dy = map_x - center_x, map_y - center_y
            angle = intensity * np.arctan2(dy, dx)
            radius = np.sqrt(dx**2 + dy**2)
            map_x = center_x + radius * np.cos(angle)
            map_y = center_y + radius * np.sin(angle)
        map_x, map_y = np.clip(map_x, 0, cols-1).astype(np.float32), np.clip(map_y, 0, rows-1).astype(np.float32)
        return Image.fromarray(cv2.remap(img_array, map_x, map_y, interpolation=cv2.INTER_LINEAR))

    def generate_image(self, width, height, layers, density, shape_string, color_palette, color_harmony, multi_color_mode, shape_opacity, background_color, positioning_bias, size_distribution, allow_rotation, stroke_width, noise_level, controlled_chaos, color_bleed, warp_type, warp_intensity, blur_radius, seed):
        random.seed(seed); np.random.seed(seed)
        try: import cv2
        except ImportError: raise ImportError("OpenCV is required for the warp effect. Please install it with 'pip install opencv-python'.")
        image, mask = Image.new("RGBA", (width, height), background_color), Image.new("L", (width, height), 0)
        harmony_colors = self.get_harmonized_colors(color_harmony) if color_harmony != "none" else []
        available_shapes = [s.strip().lower() for s in shape_string.split(',') if s.strip()]
        if not available_shapes: raise ValueError("Shape string is empty or contains no valid shapes.")
        chaos_params = {}
        if controlled_chaos == "spiral": chaos_params['radius_step'] = min(width, height) / (2 * layers)
        elif controlled_chaos == "burst": chaos_params['max_radius'] = min(width, height) / 2
        for i in range(layers):
            if controlled_chaos == "spiral": chaos_params['angle'], chaos_params['radius'] = i * (360 / layers) * (math.pi / 180), i * chaos_params['radius_step']
            elif controlled_chaos == "burst": chaos_params['angle'] = np.random.uniform(0, 2 * math.pi)
            elif controlled_chaos == "grid": chaos_params['index'] = i
            current_shape = random.choice(available_shapes)
            image, mask = self.draw_shape(width, height, density, current_shape, palette, image, mask, positioning_bias, size_distribution, rotation, harmony_colors, opacity, stroke_width, noise_level, chaos_mode, chaos_params, multi_color_mode)
        if color_bleed > 0:
            bleed_radius = int(color_bleed * 20)
            bleed_image = image.filter(ImageFilter.GaussianBlur(radius=bleed_radius))
            image = Image.alpha_composite(bleed_image, image)
        if warp_type != 'none' and warp_intensity > 0: image = self.apply_warp(image, warp_type, warp_intensity)
        if blur_radius > 0: image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        image = image.convert("RGB")
        image_np, mask_np = np.array(image).astype(np.float32) / 255.0, np.array(mask).astype(np.float32) / 255.0
        image_tensor, mask_tensor = torch.from_numpy(image_np)[None,], torch.from_numpy(mask_np).unsqueeze(0)
        vae = comfy.sd.VAE(sd=model_management.get_torch_device())
        latent = vae.encode(image_tensor[:,:,:,:3])
        return (image_tensor, {"samples": latent}, mask_tensor)

NODE_CLASS_MAPPINGS = { "ColorfulStartingImage": ColorfulStartingImage }
NODE_DISPLAY_NAME_MAPPINGS = { "ColorfulStartingImage": "🎨 Colorful Starting Image" }