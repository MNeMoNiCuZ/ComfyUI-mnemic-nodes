import os
import json
import torch
import numpy as np
from PIL import Image
from typing import List
import itertools

from ..utils.metadata_utils import extract_metadata_from_file, resize_and_crop_image

class MetadataExtractorList:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Determines the starting point in the list. Set to 'increment' to cycle through."}),
            },
            "optional": {
                "input_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder of images or a single image file. Used if image_input is not connected."}),
                "image_input": ("IMAGE", {"tooltip": "A list/batch of images. This has priority over input_path."}),
                "filter_params": ("STRING", {"multiline": False, "default": "", "tooltip": "Comma-separated list of keys to extract (e.g., steps, sampler, seed)."}),
                "max_file_count": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "Max number of items to return. 0 for all."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING",)
    RETURN_NAMES = ("image", "positive_prompt", "negative_prompt", "parsed_params_json", "filtered_params_grouped", "raw_metadata_json",)
    
    FUNCTION = "extract_metadata"
    CATEGORY = "⚡ MNeMiC Nodes"
    NODE_NAME = "Metadata Extractor (List)"
    DESCRIPTION = "Extracts metadata from a list of images or a folder of images."

    def extract_metadata(self, seed: int, input_path: str = None, image_input=None, filter_params: str = "", max_file_count: int = 0):
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
                if not input_dir or not os.path.isdir(input_dir): return (torch.zeros((0, 64, 64, 3)), [], [], [], [], [])
                input_path = os.path.join(input_dir, input_path)

            supported_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif']
            files_found = []
            if os.path.isdir(input_path):
                # Get the initial list of files, sorted for deterministic order.
                files_found = sorted([os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.splitext(f)[1].lower() in supported_exts])
            elif os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
                files_found = [input_path]

            if not files_found: return (torch.zeros((0, 64, 64, 3)), [], [], [], [], [])

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
            return (torch.zeros((0, 64, 64, 3)), [], [], [], [], [])

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

        return (image_list, pos_prompt_list, neg_prompt_list, parsed_params_list_json, filtered_params_list_grouped, raw_meta_list_json)
