import os
import requests
import torch
import numpy as np
from PIL import Image
from io import BytesIO

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class DownloadImageFromURL:
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "INT", "INT")  # Image, Width, Height
    RETURN_NAMES = ("image", "width", "height")
    OUTPUT_TOOLTIPS = ("The downloaded image", "The width of the image", "The height of the image")
    FUNCTION = "DownloadImageFromURL"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Downloads an image from a URL."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_url": ("STRING", {"multiline": False, "default": "", "tooltip": "URL of the image to download."}),
            },
            "optional": {
                "save_file_name_override": ("STRING", {"default": "", "multiline": False, "tooltip": "Optional override for the name of the saved image file."}),
                "save_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Optional path to save the image. Defaults to the current directory."})
            }
        }

    def DownloadImageFromURL(self, image_url, save_path='', save_file_name_override=''):
        if not image_url:
            print("Error: No image URL provided.")
            return None, None, None

        file_extension = os.path.splitext(image_url)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            print(f"Error: Unsupported image format `{file_extension}`")
            return None, None, None

        try:
            response = requests.get(image_url)
            if response.status_code != 200:
                print(f"Error: Failed to fetch image from URL with status code {response.status_code}")
                return None, None, None

            image = Image.open(BytesIO(response.content)).convert('RGB')
            width, height = image.size

            if save_path:
                if save_file_name_override:
                    filename = save_file_name_override + (file_extension if '.' not in save_file_name_override else '')
                else:
                    filename = os.path.basename(image_url)
                    if '.' not in filename:
                        filename += '.' + (file_extension if file_extension else 'png')

                file_path = os.path.join(save_path, filename)
                if not os.path.exists(save_path):
                    os.makedirs(save_path, exist_ok=True)
                image.save(file_path, 'PNG')  # Save as PNG to overwrite if exists

            image_tensor = pil2tensor(image)

        except Exception as e:
            print(f"Error processing the image: {e}")
            return None, None, None

        return image_tensor, width, height
