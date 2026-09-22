import os
import json
import torch
import numpy as np
from PIL import Image
from typing import List
import itertools

from comfy_api.latest import io

from ..utils.metadata_utils import extract_metadata_from_file, resize_and_crop_image


class MetadataExtractorList(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_MetadataExtractorList",
            display_name="🖼️📊 Metadata Extractor (List)",
            category="⚡ MNeMiC Nodes",
            description="Extracts metadata from a list of images or a folder of images.",
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the first file to load from a folder, starting at 0. Increments every run by default to step through the folder.",
                ),
                io.String.Input(
                    "input_path",
                    optional=True,
                    multiline=False,
                    default="",
                    tooltip="Path to a folder of images or a single image file. Used if image_input is not connected.",
                ),
                io.Image.Input(
                    "image_input",
                    optional=True,
                    tooltip="A list/batch of images. This has priority over input_path.",
                ),
                io.String.Input(
                    "filter_params",
                    advanced=True,
                    optional=True,
                    multiline=False,
                    default="",
                    tooltip="Comma-separated list of keys to extract (e.g., steps, sampler, seed).",
                ),
                io.Int.Input(
                    "max_file_count",
                    advanced=True,
                    optional=True,
                    default=0,
                    min=0,
                    max=10000,
                    step=1,
                    tooltip="Max number of items to return. 0 for all.",
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The image the metadata was read from. A 64x64 black image if nothing could be loaded."),
                io.String.Output(display_name="positive_prompt", tooltip="Positive prompt found in the image metadata. Empty if there is none."),
                io.String.Output(display_name="negative_prompt", tooltip="Negative prompt found in the image metadata. Empty if there is none."),
                io.String.Output(display_name="parsed_params_json", tooltip="All recognised generation settings (steps, sampler, cfg, seed, ...) as indented JSON."),
                io.String.Output(display_name="filtered_params_grouped", tooltip="Just the keys named in filter_params, one value per line, one entry per image."),
                io.String.Output(display_name="raw_metadata_json", tooltip="The unparsed metadata block from the file, as indented JSON."),
            ],
        )

    @classmethod
    def execute(cls, seed: int, input_path: str = None, image_input=None, filter_params: str = "", max_file_count: int = 0) -> io.NodeOutput:
        final_images, final_metadata = [], []

        if image_input is not None:
            # This logic is for an already-in-memory tensor list, so direct slicing is fine.
            all_images = list(image_input)
            all_metadata = [{"file_path": f"from_image_input_{i}", "metadata": {"source": "direct_input"}, "parsed_params": {}, "positive_prompt": "", "negative_prompt": ""} for i in range(len(all_images))]
            
            current_index = seed % len(all_images)
            rotated_images = all_images[current_index:] + all_images[:current_index]
            rotated_metadata = all_metadata[current_index:] + all_metadata[:current_index]

            final_images = rotated_images[:max_file_count] if max_file_count > 0 else rotated_images
            final_metadata = rotated_metadata[:max_file_count] if max_file_count > 0 else rotated_metadata

        elif input_path:
            if not os.path.isabs(input_path):
                from folder_paths import get_input_directory
                input_dir = get_input_directory()
                if not input_dir or not os.path.isdir(input_dir): return io.NodeOutput(torch.zeros((0, 64, 64, 3)), [], [], [], [], [])
                input_path = os.path.join(input_dir, input_path)

            supported_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif']
            files_found = []
            if os.path.isdir(input_path):
                # Get the initial list of files, sorted for deterministic order.
                files_found = sorted([os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.splitext(f)[1].lower() in supported_exts])
            elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
                files_found = [input_path]

            if not files_found: return io.NodeOutput(torch.zeros((0, 64, 64, 3)), [], [], [], [], [])

            total_files = len(files_found)
            start_index = seed % total_files
            
            # Create a memory-efficient iterator for rotation using itertools
            rotated_files_iterator = itertools.chain(itertools.islice(files_found, start_index, None), itertools.islice(files_found, start_index))

            # Create a memory-efficient iterator for slicing to max_file_count
            limit = max_file_count if max_file_count > 0 else total_files
            files_to_process_iterator = itertools.islice(rotated_files_iterator, limit)

            for file_path in files_to_process_iterator:
                try:
                    img = Image.open(file_path).convert("RGB")
                    image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)
                    final_images.append(image_tensor)
                    final_metadata.append(extract_metadata_from_file(file_path))
                except Exception as e:
                    print(f"Skipping file {file_path}: {e}")

        if not final_images:
            return io.NodeOutput(torch.zeros((0, 64, 64, 3)), [], [], [], [], [])

        first_image_height, first_image_width = final_images[0].shape[0], final_images[0].shape[1]

        needs_resizing = any(img.shape[0] != first_image_height or img.shape[1] != first_image_width for img in final_images[1:])
        if needs_resizing:
            print(f"MetadataExtractorList Warning: Found images with varying dimensions. All {len(final_images)} images will be resized and cropped to match the first image's dimensions ({first_image_height}H x {first_image_width}W).")

        resized_images = [resize_and_crop_image(img, first_image_height, first_image_width) for img in final_images]
        image_list = torch.stack(resized_images) if resized_images else torch.zeros((0, first_image_height, first_image_width, 3))

        filter_keys = [k.strip().lower() for k in filter_params.split(',') if k.strip()]
        def get_filtered_values(params_dict):
            return [str(params_dict.get(key, '')) for key in filter_keys]

        pos_prompt_list = [m.get('positive_prompt', '') for m in final_metadata]
        neg_prompt_list = [m.get('negative_prompt', '') for m in final_metadata]
        parsed_params_list_json = [json.dumps(m.get('parsed_params', {}), indent=4, default=str) for m in final_metadata]
        filtered_params_list_grouped = ["\n".join(get_filtered_values(m.get('parsed_params', {}))) for m in final_metadata]
        raw_meta_list_json = [json.dumps(m.get('metadata', {}), indent=4, default=str) for m in final_metadata]

        return io.NodeOutput(image_list, pos_prompt_list, neg_prompt_list, parsed_params_list_json, filtered_params_list_grouped, raw_meta_list_json)
