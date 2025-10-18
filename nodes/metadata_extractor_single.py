import os
import json
import torch
import numpy as np
from PIL import Image

from ..utils.metadata_utils import extract_metadata_from_file

class MetadataExtractorSingle:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Selects which file to load from a directory. Set to 'increment' to cycle."}),
            },
            "optional": {
                "input_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a single image file or a directory of images."}),
                "image_input": ("IMAGE", {"tooltip": "A single image. If a list/batch is provided, the seed will select one. This has priority over input_path."}),
                "filter_params": ("STRING", {"multiline": False, "default": "", "tooltip": "A comma-separated list of keys to extract (e.g., steps, sampler, seed)."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING",)
    RETURN_NAMES = ("image", "positive_prompt", "negative_prompt", "parsed_params_json", "filtered_params_list", "raw_metadata_json",)
    
    FUNCTION = "extract_metadata"
    CATEGORY = "⚡ MNeMiC Nodes"
    NODE_NAME = "Metadata Extractor (Single)"
    DESCRIPTION = "Extracts metadata from a single image selected from an input source."

    def extract_metadata(self, seed: int, input_path: str = None, image_input=None, filter_params: str = ""):
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
                if not input_dir or not os.path.isdir(input_dir): return (None,) * 6
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
            return (torch.zeros((1, 64, 64, 3)), "", "", "{}", "", "{}")

        filter_keys = [k.strip().lower() for k in filter_params.split(',') if k.strip()]
        def get_filtered_values(params_dict):
            return "\n".join([str(params_dict.get(key, '')) for key in filter_keys])

        pos_prompt = metadata.get('positive_prompt', '')
        neg_prompt = metadata.get('negative_prompt', '')
        parsed_params = metadata.get('parsed_params', {})
        filtered_params_list = get_filtered_values(parsed_params)
        raw_meta_json = json.dumps(metadata.get('metadata', {}), indent=4, default=str)
        parsed_params_json = json.dumps(parsed_params, indent=4, default=str)

        return (image_tensor, pos_prompt, neg_prompt, parsed_params_json, filtered_params_list, raw_meta_json)