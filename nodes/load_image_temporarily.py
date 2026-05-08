import hashlib
import os

import comfy.model_management
import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence


class LoadImageTemporarily:
    """
    Load image using ComfyUI's native upload/reference flow, but from temp storage.
    This mirrors core LoadImage decode behavior while avoiding /input persistence.
    """

    @classmethod
    def INPUT_TYPES(cls):
        temp_dir = folder_paths.get_temp_directory()
        files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])
        # Keep new node instances clear by default instead of preselecting
        # whichever temp file currently exists first.
        files = [""] + sorted(files)
        return {
            "required": {
                "image": (files, {"image_upload": True, "image_folder": "temp"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT")
    RETURN_NAMES = ("image", "mask", "width", "height")
    OUTPUT_TOOLTIPS = (
        "The loaded image tensor.",
        "The image alpha mask (inverted like ComfyUI LoadImage).",
        "Image width.",
        "Image height.",
    )
    FUNCTION = "load_image"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Load image from ComfyUI temp uploads with core LoadImage behavior."

    def load_image(self, image):
        image_path = folder_paths.get_annotated_filepath(image)
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        output_masks = []
        w, h = None, None
        dtype = comfy.model_management.intermediate_dtype()

        for frame in ImageSequence.Iterator(img):
            frame = node_helpers.pillow(ImageOps.exif_transpose, frame)

            if frame.mode == "I":
                frame = frame.point(lambda i: i * (1 / 255))
            image_rgb = frame.convert("RGB")

            if len(output_images) == 0:
                w = image_rgb.size[0]
                h = image_rgb.size[1]

            if image_rgb.size[0] != w or image_rgb.size[1] != h:
                continue

            image_np = np.array(image_rgb).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_np)[None,]

            if "A" in frame.getbands():
                mask = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
                mask = 1.0 - torch.from_numpy(mask)
            elif frame.mode == "P" and "transparency" in frame.info:
                mask = np.array(frame.convert("RGBA").getchannel("A")).astype(np.float32) / 255.0
                mask = 1.0 - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

            output_images.append(image_tensor.to(dtype=dtype))
            output_masks.append(mask.unsqueeze(0).to(dtype=dtype))

            if img.format == "MPO":
                break

        if len(output_images) > 1:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return (output_image, output_mask, w, h)

    @classmethod
    def IS_CHANGED(cls, image):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, "rb") as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not folder_paths.exists_annotated_filepath(image):
            return f"Invalid image file: {image}"
        return True


NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageTemporarily": "🖼️ Load Image Temporarily",
}
