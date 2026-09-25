import hashlib
import os

import comfy.model_management
import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

from comfy_api.latest import io


def _temp_image_path(image):
    temp_dir = folder_paths.get_temp_directory()
    image_path = folder_paths.get_annotated_filepath(image, default_dir=temp_dir)
    if not folder_paths.is_within_directory(temp_dir, image_path) or not os.path.isfile(image_path):
        raise ValueError(f"Invalid temporary image: {image!r}")
    return image_path


class LoadImageTemporarily(io.ComfyNode):
    """
    Loads an image and stores it in ComfyUI /temp-folder instead of the /input folder.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        # The temp folder does not exist until ComfyUI first writes to it, and a
        # failure here would take down the whole extension: schemas are built at
        # load time.
        temp_dir = folder_paths.get_temp_directory()
        try:
            files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        except OSError:
            files = []
        files = folder_paths.filter_files_content_types(files, ["image"])
        # Keep new node instances clear by default instead of preselecting
        # whichever temp file currently exists first.
        files = [""] + sorted(files)
        return io.Schema(
            node_id="MNeMiC_LoadImageTemporarily",
            display_name="🖼️ Load Image Temporarily",
            category="⚡ MNeMiC Nodes",
            description="Loads an image and stores it in ComfyUI /temp-folder instead of the /input folder.",
            inputs=[
                io.Combo.Input(
                    "image",
                    options=files,
                    upload=io.UploadType.image,
                    image_folder=io.FolderType.temp,
                    tooltip="Image to load from ComfyUI's temp folder. Uploads through this node go to temp instead of input, so they are cleared when ComfyUI restarts.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The loaded image tensor."),
                io.Mask.Output(display_name="mask", tooltip="The image alpha mask (inverted like ComfyUI LoadImage)."),
                io.Int.Output(display_name="width", tooltip="Image width."),
                io.Int.Output(display_name="height", tooltip="Image height."),
            ],
        )

    @classmethod
    def execute(cls, image) -> io.NodeOutput:
        if not image:
            raise ValueError("Select an image.")
        image_path = _temp_image_path(image)
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

        return io.NodeOutput(output_image, output_mask, w, h)

    @classmethod
    def fingerprint_inputs(cls, image):
        if not image:
            return None
        image_path = _temp_image_path(image)
        m = hashlib.sha256()
        with open(image_path, "rb") as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def validate_inputs(cls, image):
        # An empty selection may belong to an unused lazy branch.
        if not image:
            return True
        try:
            _temp_image_path(image)
        except ValueError as e:
            return str(e)
        return True
