import torch
from PIL import Image
import numpy as np
import folder_paths
import os

from comfy_api.latest import io

from ..utils.image_utils import load_image_metadata


class LoadImageAdvanced(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        input_dir = folder_paths.get_input_directory()
        try:
            files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        except OSError:
            files = []
        return io.Schema(
            node_id="MNeMiC_LoadImageAdvanced",
            display_name="🖼️ Load Image Advanced",
            category="⚡ MNeMiC Nodes",
            description="Loads an image and extracts its file path and positive prompt from metadata.",
            inputs=[
                io.Combo.Input(
                    "image",
                    options=sorted(files),
                    upload=io.UploadType.image,
                    tooltip="The image file to load. The node will also attempt to extract metadata from this image.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The loaded image."),
                io.Mask.Output(display_name="mask", tooltip="The alpha channel of the image, if it exists."),
                io.String.Output(display_name="image_path", tooltip="The full file path of the loaded image."),
                io.String.Output(display_name="positive_prompt", tooltip="The positive prompt extracted from the image's metadata."),
                io.Int.Output(display_name="width", tooltip="The width of the loaded image."),
                io.Int.Output(display_name="height", tooltip="The height of the loaded image."),
            ],
        )

    @classmethod
    def execute(cls, image) -> io.NodeOutput:
        image_path = folder_paths.get_annotated_filepath(image)
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                metadata = load_image_metadata(image_path)
                positive_prompt = metadata.get("positive_prompt", "")

                img_rgb = img.convert("RGB")
                np_image = np.asarray(img_rgb, dtype=np.float32) / 255.0  # [H,W,3]
                output_image = torch.from_numpy(np_image).unsqueeze(0).contiguous()  # [1,H,W,3]

                if "A" in img.getbands():
                    mask_np = np.asarray(img.getchannel("A"), dtype=np.float32) / 255.0  # [H,W]
                    mask = torch.from_numpy(mask_np).unsqueeze(0)  # [1,H,W]
                else:
                    mask = torch.zeros((1, height, width), dtype=torch.float32)
        except Exception as e:
            raise RuntimeError(f"Failed to load image '{image_path}': {e}")

        return io.NodeOutput(output_image, mask, image_path, positive_prompt, width, height)
