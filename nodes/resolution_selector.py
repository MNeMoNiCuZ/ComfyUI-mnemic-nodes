import math
import json
import os
import torch
import comfy.model_management
from pathlib import Path

class ResolutionSelector:
    OUTPUT_NODE = True
    RETURN_TYPES = ("INT", "INT", "LATENT")
    RETURN_NAMES = ("width", "height", "latent")
    OUTPUT_IS_LIST = (False, False, False)
    OUTPUT_TOOLTIPS = (
        "The final scaled width in pixels.",
        "The final scaled height in pixels.",
        "The final scaled latent."
    )
    FUNCTION = "process_resolution"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Flexible resolution selector with presets, image input, min/max lengths, snapping, swapping and resolution multiplication.\n\nPriority order for resolution selection:\n1. Input Image\n2. User Preset\n3. Preset\n4. Custom Values (when preset is set to 'Custom')"
    DOCUMENTATION = "This node provides resolution selection with the following priority order:\n1. Image Input (highest priority)\n2. User Preset\n3. Preset\n4. Custom Values (when preset is set to 'Custom')"

    # Default user presets that will be created if the file doesn't exist
    DEFAULT_USER_PRESETS = {
        "Favorites": [
            {"name": "[Square] 768x768 1:1", "width": 768, "height": 768},
            {"name": "[Portrait] 540x960 9:16", "width": 540, "height": 960},
            {"name": "[Landscape] 960x540 16:9", "width": 960, "height": 540},
            {"name": "[Portrait] 1080x1920 9:16", "width": 1080, "height": 1920},
            {"name": "[Landscape] 1920x1080 16:9", "width": 1920, "height": 1080},
            {"name": "[Portrait] 832x1216 13:19", "width": 832, "height": 1216},
            {"name": "[Landscape] 1216x832 19:13", "width": 1216, "height": 832},
        ]
    }

    @classmethod
    def load_presets(cls):
        """Load presets from config file"""
        presets_path = Path(__file__).parent / "resolution_selector" / "preset_resolution.json"
        if not presets_path.exists():
            return {}
        
        try:
            with open(presets_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading presets: {e}")
            return {}

    @classmethod
    def create_default_user_presets(cls):
        """Create default user presets file with initial entries"""
        presets_path = Path(__file__).parent / "resolution_selector" / "user_resolution.json"
        os.makedirs(os.path.dirname(presets_path), exist_ok=True)
        
        # Format as in preset_resolution.json
        with open(presets_path, 'w') as f:
            f.write("{\n")
            categories = list(cls.DEFAULT_USER_PRESETS.keys())
            for i, category in enumerate(categories):
                f.write(f'    "{category}": [\n')
                presets = cls.DEFAULT_USER_PRESETS[category]
                for j, preset in enumerate(presets):
                    preset_str = json.dumps(preset)
                    if j < len(presets) - 1:
                        f.write(f'        {preset_str},\n')
                    else:
                        f.write(f'        {preset_str}\n')
                if i < len(categories) - 1:
                    f.write('    ],\n')
                else:
                    f.write('    ]\n')
            f.write("}\n")
        
        return cls.DEFAULT_USER_PRESETS

    @classmethod
    def load_user_presets(cls):
        """Load user presets from config file"""
        presets_path = Path(__file__).parent / "resolution_selector" / "user_resolution.json"
        
        if not presets_path.exists():
            # Create user presets file with default entries if it doesn't exist
            return cls.create_default_user_presets()
        
        try:
            with open(presets_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading user presets: {e}")
            return cls.create_default_user_presets()

    @classmethod
    def INPUT_TYPES(cls):
        # Load presets from config
        presets = cls.load_presets()
        
        # Create flattened list of preset names with groups
        preset_choices = ["Custom"]
        for model, model_presets in presets.items():
            for preset in model_presets:
                preset_choices.append(f"{model}: {preset['name']}")

        # Load user presets
        user_presets = cls.load_user_presets()
        user_preset_choices = ["None"]
        
        # Add user presets with categories
        for category, category_presets in user_presets.items():
            for preset in category_presets:
                user_preset_choices.append(f"{category}: {preset['name']}")

        return {
            "required": {
                "preset": (preset_choices, {
                    "default": "Custom",
                    "tooltip": "Select a model-specific resolution preset or use custom dimensions"
                }),
                "preset_user": (user_preset_choices, {
                    "default": "None",
                    "tooltip": "User-defined preset selection (overrides main preset when selected)"
                }),
                "custom_width": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 16384,
                    "step": 8,
                    "tooltip": "Custom width (Only used with Custom preset)"
                }),
                "custom_height": ("INT", {
                    "default": 512,
                    "min": 64,
                    "max": 16384,
                    "step": 8,
                    "tooltip": "Custom height (Only used with Custom preset)"
                }),
                "multiply": ("FLOAT", {
                    "default": 1.0,
                    "min": -16384,
                    "step": 0.1,
                    "tooltip": "Multiplier for the final resolution. Negative values will flip the dimensions."
                }),
                "swap_width_and_height": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Swap width and height dimensions"
                }),
            },
            "optional": {
                "image (optional)": ("IMAGE", {
                    "tooltip": "Priority order for resolution selection:\n1. Input Image\n2. User Preset\n3. Preset\n4. Custom Values (when preset is set to 'Custom')"
                }),
                "image_min_length": ("INT", {
                    "default": 0,
                    "min": 0, 
                    "max": 16384,
                    "step": 1,
                    "tooltip": "When image is provided, ensures the shortest side is at least this length (0 = ignore)"
                }),
                "image_max_length": ("INT", {
                    "default": 0,
                    "min": 0, 
                    "max": 16384,
                    "step": 1,
                    "tooltip": "When image is provided, ensures the longest side is at most this length (0 = ignore)"
                }),
                "snap_to_nearest": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "When enabled, dimensions will be adjusted to the nearest multiple of snap_resolution"
                }),
                "snap_resolution": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 16384,
                    "step": 1,
                    "tooltip": "Snap dimensions to multiples of this value (0 = no snapping)"
                }),
                "batch_size": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "tooltip": "Number of latent images to generate in batch"
                })
            }
        }

    @classmethod
    def validate_dimensions(cls, width, height, snap_to_nearest=False, snap_resolution=8):
        """Validate and adjust dimensions to be valid"""
        # Store sign to preserve direction (negative values represent flipped dimensions)
        width_sign = -1 if width < 0 else 1
        height_sign = -1 if height < 0 else 1
        
        # Work with absolute values for validation
        abs_width = abs(width)
        abs_height = abs(height)
        
        # Ensure dimensions are at least 64 pixels
        abs_width = max(64, abs_width)
        abs_height = max(64, abs_height)
        
        # Snap to nearest multiple if enabled and snap_resolution > 0
        if snap_to_nearest and snap_resolution > 0:
            abs_width = round(abs_width / snap_resolution) * snap_resolution
            abs_height = round(abs_height / snap_resolution) * snap_resolution
            
            # Ensure minimum width/height is at least 64
            if abs_width < 64:
                abs_width = snap_resolution * max(1, int(64 / snap_resolution))
            if abs_height < 64:
                abs_height = snap_resolution * max(1, int(64 / snap_resolution))
        
        # Cap at maximum dimensions
        abs_width = min(abs_width, 16384)
        abs_height = min(abs_height, 16384)
        
        # Reapply original signs
        width = width_sign * abs_width
        height = height_sign * abs_height
        
        return int(width), int(height)

    @classmethod
    def get_preset_info(cls, preset_name, from_user_presets=False):
        """Get information about a specific preset"""
        if preset_name == "Custom" or preset_name == "None":
            return None
            
        try:
            if from_user_presets:
                category, name = preset_name.split(": ", 1)
                user_presets = cls.load_user_presets()
                for preset in user_presets.get(category, []):
                    if preset["name"] == name:
                        return preset
            else:
                model, name = preset_name.split(": ", 1)
                presets = cls.load_presets()
                for preset in presets.get(model, []):
                    if preset["name"] == name:
                        return preset
            return None
        except:
            return None
            
    @classmethod
    def extract_image_dimensions(cls, image, image_min_length=0, image_max_length=0):
        """
        Extract dimensions from an input image tensor and adjust based on min/max constraints
        
        If image_min_length > 0, ensures the shortest side is at least that length
        If image_max_length > 0, ensures the longest side is at most that length
        Both are applied proportionally to maintain aspect ratio
        """
        if image is None or not isinstance(image, torch.Tensor):
            return None, None
            
        try:
            # Important: In ComfyUI, image tensors are in [B, H, W, C] format
            # (Batch, Height, Width, Channels) - different from standard PyTorch!
            if len(image.shape) == 4:  # Batch of images: [batch, height, width, channels]
                height = int(image.shape[1])
                width = int(image.shape[2])
            elif len(image.shape) == 3:  # Single image: [height, width, channels]
                height = int(image.shape[0])
                width = int(image.shape[1])
            else:
                print(f"Unexpected image tensor shape: {image.shape}")
                return None, None
        except Exception as e:
            print(f"Error extracting dimensions: {e}")
            return None, None
        
        # Store original dimensions
        original_width, original_height = width, height
        
        # Apply minimum length constraint (if specified)
        if image_min_length > 0:
            shortest_side = min(width, height)
            if shortest_side < image_min_length:
                scale = image_min_length / shortest_side
                width = int(width * scale)
                height = int(height * scale)
        
        # Apply maximum length constraint (if specified)
        if image_max_length > 0:
            longest_side = max(width, height)
            if longest_side > image_max_length:
                scale = image_max_length / longest_side
                width = int(width * scale)
                height = int(height * scale)
        
        # If no scaling needed, return original dimensions
        if width == original_width and height == original_height:
            return width, height
            
        return width, height

    def process_resolution(self, preset, preset_user, multiply, swap_width_and_height, custom_width, custom_height,
                         **kwargs):
        """Process resolution settings and return final dimensions"""
        try:
            # Extract optional parameters with defaults
            image = kwargs.get("image (optional)", None)
            image_min_length = kwargs.get("image_min_length", 0)
            image_max_length = kwargs.get("image_max_length", 0)
            snap_to_nearest = kwargs.get("snap_to_nearest", False)
            snap_resolution = kwargs.get("snap_resolution", 8)
            batch_size = kwargs.get("batch_size", 1)
            
            # Priority: Image > User Preset > Standard Preset > Custom Values
            width = None
            height = None
            
            # 1. Check if we have an image input (highest priority)
            if image is not None:
                width, height = self.__class__.extract_image_dimensions(
                    image, 
                    image_min_length,
                    image_max_length
                )
                
            # If image processing failed or no image, fall back to presets or custom values
            if width is None or height is None:
                width, height = self._get_dimensions_from_presets(preset, preset_user, custom_width, custom_height)
            
            # Apply dimension swap if requested
            if swap_width_and_height:
                width, height = height, width
            
            # Apply multiplier
            # Negative multiply will result in negative dimensions, which the validate_dimensions 
            # method preserves as a way to represent flipped dimensions
            width = int(round(width * multiply))
            height = int(round(height * multiply))

            # Validate final dimensions and apply snapping if needed
            width, height = self.validate_dimensions(width, height, snap_to_nearest, snap_resolution)
            
            # Get absolute width and height values for the latent
            abs_width = abs(width)
            abs_height = abs(height)
            
            # Create latent tensor (latent space is 8x smaller than pixel space)
            device = comfy.model_management.intermediate_device()
            latent_tensor = torch.zeros([batch_size, 4, abs_height // 8, abs_width // 8], device=device)
            latent = {"samples": latent_tensor}
            
            return (width, height, latent)
        
        except Exception as e:
            print(f"Error processing resolution: {e}")
            import traceback
            traceback.print_exc()
            # Include latent in safe fallback
            device = comfy.model_management.intermediate_device()
            latent = {"samples": torch.zeros([1, 4, 64, 64], device=device)}
            return (512, 512, latent)  # Safe fallback
            
    def _get_dimensions_from_presets(self, preset, preset_user, custom_width, custom_height):
        """Helper method to get dimensions from presets based on priority"""
        if preset_user != "None":
            # 2. Try to get user preset
            preset_info = self.__class__.get_preset_info(preset_user, from_user_presets=True)
            if preset_info:
                return preset_info["width"], preset_info["height"]
        
        # 3. Try to get standard preset
        if preset != "Custom":
            preset_info = self.__class__.get_preset_info(preset)
            if preset_info:
                return preset_info["width"], preset_info["height"]
        
        # 4. Fall back to custom values
        return custom_width, custom_height

# Export the node
NODE_CLASS_MAPPINGS = {
    "ResolutionSelector": ResolutionSelector
}