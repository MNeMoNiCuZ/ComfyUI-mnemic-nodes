import os
import requests
import torch
import numpy as np
from PIL import Image
from io import BytesIO

from comfy_api.latest import io


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


class DownloadImageFromURL(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_DownloadImageFromURL",
            display_name="🖼️ Download Image from URL",
            category="⚡ MNeMiC Nodes",
            description="Downloads an image from a URL.",
            inputs=[
                io.String.Input(
                    "image_url",
                    multiline=False,
                    default="",
                    tooltip="URL of the image to download.",
                ),
                io.String.Input(
                    "save_file_name_override",
                    optional=True,
                    default="",
                    multiline=False,
                    tooltip="Optional override for the name of the saved image file.",
                ),
                io.String.Input(
                    "save_path",
                    optional=True,
                    default="",
                    multiline=False,
                    tooltip="Optional path to save the image. Defaults to the current directory.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The downloaded image"),
                io.Int.Output(display_name="width", tooltip="The width of the image"),
                io.Int.Output(display_name="height", tooltip="The height of the image"),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, image_url, save_path='', save_file_name_override='') -> io.NodeOutput:
        if not image_url:
            print("Error: No image URL provided.")
            return io.NodeOutput(None, None, None)

        file_extension = os.path.splitext(image_url)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            print(f"Error: Unsupported image format `{file_extension}`")
            return io.NodeOutput(None, None, None)

        try:
            response = requests.get(image_url)
            if response.status_code != 200:
                print(f"Error: Failed to fetch image from URL with status code {response.status_code}")
                return io.NodeOutput(None, None, None)

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
            return io.NodeOutput(None, None, None)

        return io.NodeOutput(image_tensor, width, height)
