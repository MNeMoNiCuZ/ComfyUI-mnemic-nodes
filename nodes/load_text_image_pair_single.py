import os
import torch
import numpy as np
from PIL import Image
from ..utils.file_utils import find_image_text_pairs

class LoadTextImagePairSingle:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The index of the pair to load."}),
                "folder_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder containing image and text files with matching basenames. This is used only if image_input and text_input are not connected."}),
            },
            "optional": {
                "image_input": ("IMAGE", {"tooltip": "A single image or a list/batch of images. This input has priority over the folder_path."}),
                "text_input": ("STRING", {"forceInput": True, "tooltip": "A single text string or a list of strings. This input has priority over the folder_path."}),
                "text_format_extension": ("STRING", {"default": "txt", "tooltip": "The file extension for the text files to look for (without the dot)."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("image_single", "string_single", "image_path_single", "image_filename_single", "total_count")
    FUNCTION = "load_pair_single"
    OUTPUT_TOOLTIPS = (
        "The single image selected by the seed.",
        "The text string that is paired with the selected image.",
        "The full absolute path of the selected image.",
        "The filename (without extension) of the selected image.",
        "The total number of pairs found in the dataset."
    )

    def load_pair_single(self, seed, folder_path=None, image_input=None, text_input=None, text_format_extension="txt"):
        if image_input is not None and text_input is not None:
            # Handle direct inputs
            image = image_input
            text = text_input if isinstance(text_input, str) else str(text_input)
            total_count = image.shape[0]
            return (image, text, "", "", total_count)

        if not folder_path or not os.path.isdir(folder_path):
            return (None, "", "", "", 0)

        pairs = find_image_text_pairs(folder_path, text_format_extension)
        if not pairs:
            return (None, "", "", "", 0)

        total_count = len(pairs)
        current_index = seed % total_count

        image_path, text_path, basename = pairs[current_index]

        try:
            i = Image.open(image_path).convert("RGB")
            image = np.array(i).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error loading pair {basename}: {e}")
            return (None, "", "", "", total_count)

        return (image, text, image_path, basename, total_count)
