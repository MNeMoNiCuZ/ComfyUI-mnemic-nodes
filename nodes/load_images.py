import os
import torch
import numpy as np
from PIL import Image

class LoadImagesFromPath:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The index of the image to load. Set 'Control After Generate' to 'Increment' in the workflow options to cycle through images sequentially."}),
                "input_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder containing images or a single image file."}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "image_path", "current_index", "total_count")
    OUTPUT_IS_LIST = (False, False, False, False, False)
    
    FUNCTION = "load_images"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Loads a single image from a directory, allowing sequential iteration through the folder."

    def load_images(self, seed: int, input_path: str):
        if not input_path:
            raise ValueError("Input path cannot be empty.")
            
        if not os.path.isabs(input_path):
            from folder_paths import get_input_directory
            input_dir = get_input_directory()
            if not input_dir or not os.path.isdir(input_dir):
                return (None, None, "", 0, 0)
            input_path = os.path.join(input_dir, input_path)

        supported_exts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']
        
        if os.path.isdir(input_path):
            files_found = [os.path.join(input_path, f) for f in sorted(os.listdir(input_path)) if os.path.splitext(f)[1].lower() in supported_exts]
        elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
            files_found = [input_path]
        else:
            files_found = []

        if not files_found:
            return (None, None, "", 0, 0)

        total_count = len(files_found)
        current_index = seed % total_count
        
        image_path = files_found[current_index]

        try:
            with Image.open(image_path) as img:
                img_rgb = img.convert("RGB")
                image_np = np.array(img_rgb).astype(np.float32) / 255.0
                image_tensor = torch.from_numpy(image_np).unsqueeze(0)
                
                if "A" in img.getbands():
                    mask_np = np.array(img.getchannel("A")).astype(np.float32) / 255.0
                    mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)
                else:
                    mask_tensor = torch.zeros((1, image_tensor.shape[1], image_tensor.shape[2]), dtype=torch.float32)

        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return (None, None, "", current_index, total_count)

        return (image_tensor, mask_tensor, image_path, current_index, total_count)

NODE_CLASS_MAPPINGS = {
    "LoadImagesFromPath": LoadImagesFromPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImagesFromPath": "Load Images From Path"
}
