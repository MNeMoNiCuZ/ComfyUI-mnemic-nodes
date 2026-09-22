import os
import torch
import numpy as np
from PIL import Image

from comfy_api.latest import io


class LoadImagesFromPath(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoadImagesFromPath",
            display_name="📂 Load Images From Path",
            category="⚡ MNeMiC Nodes",
            description="Loads a single image from a directory, allowing sequential iteration through the folder.",
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the image to load, starting at 0. Increments every run by default to step through the folder.",
                ),
                io.String.Input(
                    "input_path",
                    multiline=False,
                    default="",
                    tooltip="Path to a folder containing images or a single image file.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The image at the selected index."),
                io.Mask.Output(display_name="mask", tooltip="Alpha channel of the image, or fully black if it has none."),
                io.String.Output(display_name="image_path", tooltip="Full path of the file that was loaded."),
                io.Int.Output(display_name="current_index", tooltip="Index actually loaded: the seed wrapped around the number of files found."),
                io.Int.Output(display_name="total_count", tooltip="How many images were found at the path."),
            ],
        )

    @classmethod
    def execute(cls, seed: int, input_path: str) -> io.NodeOutput:
        if not input_path:
            raise ValueError("Input path cannot be empty.")

        if not os.path.isabs(input_path):
            from folder_paths import get_input_directory
            input_dir = get_input_directory()
            if not input_dir or not os.path.isdir(input_dir):
                return io.NodeOutput(None, None, "", 0, 0)
            input_path = os.path.join(input_dir, input_path)

        supported_exts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']

        if os.path.isdir(input_path):
            files_found = [os.path.join(input_path, f) for f in sorted(os.listdir(input_path)) if os.path.splitext(f)[1].lower() in supported_exts]
        elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
            files_found = [input_path]
        else:
            files_found = []

        if not files_found:
            return io.NodeOutput(None, None, "", 0, 0)

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
            return io.NodeOutput(None, None, "", current_index, total_count)

        return io.NodeOutput(image_tensor, mask_tensor, image_path, current_index, total_count)
