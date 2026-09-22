import os
import json
import torch
import numpy as np
from PIL import Image

from comfy_api.latest import io

from ..utils.metadata_utils import extract_metadata_from_file


class MetadataExtractorSingle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_MetadataExtractorSingle",
            display_name="🖼️📊 Metadata Extractor (Single)",
            category="⚡ MNeMiC Nodes",
            description="Extracts metadata from a single image selected from an input source.",
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the file to load from a folder, starting at 0. Increments every run by default to step through the folder.",
                ),
                io.String.Input(
                    "input_path",
                    optional=True,
                    multiline=False,
                    default="",
                    tooltip="Path to a single image file or a directory of images.",
                ),
                io.Image.Input(
                    "image_input",
                    optional=True,
                    tooltip="A single image. If a list/batch is provided, the seed will select one. This has priority over input_path.",
                ),
                io.String.Input(
                    "filter_params",
                    advanced=True,
                    optional=True,
                    multiline=False,
                    default="",
                    tooltip="A comma-separated list of keys to extract (e.g., steps, sampler, seed).",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The image the metadata was read from. A 64x64 black image if nothing could be loaded."),
                io.String.Output(display_name="positive_prompt", tooltip="Positive prompt found in the image metadata. Empty if there is none."),
                io.String.Output(display_name="negative_prompt", tooltip="Negative prompt found in the image metadata. Empty if there is none."),
                io.String.Output(display_name="parsed_params_json", tooltip="All recognised generation settings (steps, sampler, cfg, seed, ...) as indented JSON."),
                io.String.Output(display_name="filtered_params_list", tooltip="Just the keys named in filter_params, one value per line, in the order requested."),
                io.String.Output(display_name="raw_metadata_json", tooltip="The unparsed metadata block from the file, as indented JSON."),
            ],
        )

    @classmethod
    def execute(cls, seed: int, input_path: str = None, image_input=None, filter_params: str = "") -> io.NodeOutput:
        image_tensor, metadata = None, None

        if image_input is not None:
            if len(image_input) > 0:
                index = seed % len(image_input)
                image_tensor = image_input[index].unsqueeze(0)
            metadata = {"file_path": "from_image_input", "metadata": {"source": "direct_input"}, "parsed_params": {}, "positive_prompt": "", "negative_prompt": ""}

        elif input_path:
            if not os.path.isabs(input_path):
                from folder_paths import get_input_directory
                input_dir = get_input_directory()
                if not input_dir or not os.path.isdir(input_dir):
                    return io.NodeOutput(*((None,) * 6))
                input_path = os.path.join(input_dir, input_path)

            file_to_process = None
            supported_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif']

            if os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
                file_to_process = input_path
            elif os.path.isdir(input_path):
                try:
                    files_in_dir = sorted([f for f in os.listdir(input_path) if os.path.splitext(f)[1].lower() in supported_exts])
                    if files_in_dir:
                        index = seed % len(files_in_dir)
                        selected_file_name = files_in_dir[index]
                        file_to_process = os.path.join(input_path, selected_file_name)
                except OSError as e:
                    print(f"Error scanning directory {input_path}: {e}")

            if file_to_process:
                try:
                    img = Image.open(file_to_process).convert("RGB")
                    image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
                    metadata = extract_metadata_from_file(file_to_process)
                except Exception as e:
                    print(f"Error processing file {file_to_process}: {e}")

        if image_tensor is None or metadata is None:
            return io.NodeOutput(torch.zeros((1, 64, 64, 3)), "", "", "{}", "", "{}")

        filter_keys = [k.strip().lower() for k in filter_params.split(',') if k.strip()]

        def get_filtered_values(params_dict):
            return "\n".join([str(params_dict.get(key, '')) for key in filter_keys])

        pos_prompt = metadata.get('positive_prompt', '')
        neg_prompt = metadata.get('negative_prompt', '')
        parsed_params = metadata.get('parsed_params', {})
        filtered_params_list = get_filtered_values(parsed_params)
        raw_meta_json = json.dumps(metadata.get('metadata', {}), indent=4, default=str)
        parsed_params_json = json.dumps(parsed_params, indent=4, default=str)

        return io.NodeOutput(image_tensor, pos_prompt, neg_prompt, parsed_params_json, filtered_params_list, raw_meta_json)
