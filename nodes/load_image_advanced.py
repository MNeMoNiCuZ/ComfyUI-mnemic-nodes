import torch
from PIL import Image
import numpy as np
import folder_paths
import os
from ..utils.image_utils import load_image_metadata

class LoadImageAdvanced:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True, "tooltip": "The image file to load. The node will also attempt to extract metadata from this image."}),
            },
        }

    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Loads an image and extracts its file path and positive prompt from metadata."
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "image_path", "positive_prompt", "width", "height")
    OUTPUT_TOOLTIPS = (
        "The loaded image.",
        "The alpha channel of the image, if it exists.",
        "The full file path of the loaded image.",
        "The positive prompt extracted from the image's metadata.",
        "The width of the loaded image.",
        "The height of the loaded image."
    )
    FUNCTION = "load_image"

    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        width, height = img.size
        
        metadata = load_image_metadata(image_path)
        positive_prompt = metadata.get("positive_prompt", "")

        img_rgb = img.convert("RGB")
        np_image = np.array(img_rgb).astype(np.float32) / 255.0
        output_image = torch.from_numpy(np_image).unsqueeze(0)

        if 'A' in img.getbands():
            mask = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask = torch.from_numpy(mask)
        else:
            mask = torch.zeros((height, width), dtype=torch.float32, device="cpu")
        
        return (output_image, mask.unsqueeze(0), image_path, positive_prompt, width, height)

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageAdvanced": "🖼️ Load Image Advanced",
}