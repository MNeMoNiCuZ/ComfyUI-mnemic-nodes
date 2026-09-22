import os
import torch
import numpy as np
from PIL import Image

from comfy_api.latest import io

from ..utils.file_utils import find_image_text_pairs


class LoadTextImagePairSingle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoadTextImagePairSingle",
            display_name="🖼️+📝 Load Text-Image Pair (Single)",
            category="⚡ MNeMiC Nodes",
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the pair to load, starting at 0. Increments every run by default to step through the folder.",
                ),
                io.String.Input(
                    "folder_path",
                    multiline=False,
                    default="",
                    tooltip="Path to a folder containing image and text files with matching basenames. This is used only if image_input and text_input are not connected.",
                ),
                io.Image.Input(
                    "image_input",
                    optional=True,
                    tooltip="A single image or a list/batch of images. This input has priority over the folder_path.",
                ),
                io.String.Input(
                    "text_input",
                    optional=True,
                    force_input=True,
                    tooltip="A single text string or a list of strings. This input has priority over the folder_path.",
                ),
                io.String.Input(
                    "text_format_extension",
                    optional=True,
                    default="txt",
                    tooltip="The file extension for the text files to look for (without the dot).",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image_single", tooltip="The single image selected by the seed."),
                io.String.Output(display_name="string_single", tooltip="The text string that is paired with the selected image."),
                io.String.Output(display_name="image_path_single", tooltip="The full absolute path of the selected image."),
                io.String.Output(display_name="image_filename_single", tooltip="The filename (without extension) of the selected image."),
                io.Int.Output(display_name="total_count", tooltip="The total number of pairs found in the dataset."),
            ],
        )

    @classmethod
    def execute(cls, seed, folder_path=None, image_input=None, text_input=None, text_format_extension="txt") -> io.NodeOutput:
        if image_input is not None and text_input is not None:
            # Handle direct inputs
            image = image_input
            text = text_input if isinstance(text_input, str) else str(text_input)
            total_count = image.shape[0]
            return io.NodeOutput(image, text, "", "", total_count)

        if not folder_path or not os.path.isdir(folder_path):
            return io.NodeOutput(None, "", "", "", 0)

        pairs = find_image_text_pairs(folder_path, text_format_extension)
        if not pairs:
            return io.NodeOutput(None, "", "", "", 0)

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
            return io.NodeOutput(None, "", "", "", total_count)

        return io.NodeOutput(image, text, image_path, basename, total_count)
