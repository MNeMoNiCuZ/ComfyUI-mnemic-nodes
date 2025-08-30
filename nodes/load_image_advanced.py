import torch
from PIL import Image
import numpy as np
import folder_paths
import os
from utils.image_utils import load_image_metadata

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
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "image_path", "positive_prompt")
    OUTPUT_TOOLTIPS = (
        "The loaded image.",
        "The alpha channel of the image, if it exists.",
        "The full file path of the loaded image.",
        "The positive prompt extracted from the image's metadata."
    )
    FUNCTION = "load_image"

    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        output_images = []
        output_masks = []
        
        metadata = load_image_metadata(image_path)
        positive_prompt = metadata.get("positive_prompt", "")

        for i in Image.Image.split(img):
            i = Image.fromarray(np.array(i).astype(np.uint8), 'RGB')
            output_images.append(i)

        if 'A' in img.getbands():
            mask = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask = torch.from_numpy(mask)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
        
        output_image = torch.cat([torch.from_numpy(np.array(i).astype(np.float32) / 255.0).unsqueeze(0) for i in output_images], dim=0)
        
        return (output_image, mask.unsqueeze(0), image_path, positive_prompt)

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageAdvanced": "🖼️ Load Image Advanced",
}