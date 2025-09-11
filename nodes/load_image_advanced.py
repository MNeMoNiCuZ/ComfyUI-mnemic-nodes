import torch
from PIL import Image
import numpy as np
import folder_paths
import os
from ..utils.image_utils import load_image_metadata

class LoadImageAdvanced:
    @classmethod
    def INPUT_TYPES(s):
        """
        Return the dynamic INPUT_TYPES dictionary for the node, listing files available in the configured input directory.
        
        The function enumerates regular files in folder_paths.get_input_directory(), sorts the filenames, and exposes them as the selectable options for the required "image" input. The returned mapping sets the "image_upload" flag and provides a tooltip indicating that image metadata will be attempted to be extracted.
        """
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
        """
        Load an image file, extract optional positive prompt metadata, and return the image tensor, mask, path, prompt, and dimensions.
        
        Parameters:
            image (str): Filename (as listed by the node UI) of the image to load; resolved to a full path internally.
        
        Returns:
            tuple: (image_tensor, mask_tensor, image_path, positive_prompt, width, height)
                - image_tensor (torch.FloatTensor): RGB image normalized to [0, 1], dtype float32, shape (1, height, width, 3).
                - mask_tensor (torch.FloatTensor): Alpha mask normalized to [0, 1], dtype float32, shape (1, height, width). If the source image has no alpha channel, this is a zero tensor.
                - image_path (str): Resolved full filesystem path to the loaded image.
                - positive_prompt (str): Value of the "positive_prompt" key from image metadata, or empty string if not present.
                - width (int): Image width in pixels.
                - height (int): Image height in pixels.
        
        Notes:
            - The function does not catch I/O or decoding errors from PIL; such exceptions propagate to the caller.
        """
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