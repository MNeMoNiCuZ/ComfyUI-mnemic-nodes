import os
import json
import re
import piexif
import torch
import numpy as np
from PIL import Image
import torchvision.transforms.functional as F
from typing import Dict, List, Any

class MetadataExtractor:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed determines the starting point for selecting pairs. Set to 'increment' in the workflow options to cycle through all available pairs sequentially."}),
            },
            "optional": {
                "input_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder containing images or a single image file. This is used only if image_input is not connected."}),
                "image_input": ("IMAGE", {"tooltip": "A single image or a list/batch of images. This input has priority over the input_path."}),
                "filter_params": ("STRING", {"multiline": False, "default": "", "tooltip": "A comma-separated list of case-insensitive keys to extract from the parsed parameters (e.g., steps, sampler, seed)."}),
                "max_file_count": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "The maximum number of pairs to return in the output lists. If set to 0, all found pairs will be returned."}),
            }
        }

    RETURN_TYPES = (
        "IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING",
        "IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING",
    )
    RETURN_NAMES = (
        "image_single", "positive_prompt_single", "negative_prompt_single", 
        "parsed_params_single_json", "filtered_params_single_list", "raw_metadata_single_json",
        "image_list", "positive_prompt_list", "negative_prompt_list",
        "parsed_params_list_json", "filtered_params_list_grouped", "raw_metadata_list_json",
    )
    
    OUTPUT_TOOLTIPS = (
        "The single image selected by the seed. Its position in the list determines which item is chosen from the input list.",
        "The parsed positive prompt from the selected image's metadata.",
        "The parsed negative prompt from the selected image's metadata.",
        "All parsed parameters from the selected image, including prompts, as a JSON string.",
        "The specific values requested in 'filter_params' from the selected image, returned as a multi-line string. Use the parsed_params_single_json output for reference, then enter the same parameter name here in a comma separated list. e.g. 'steps, sampler, seed'. Each output will have it's own string list output value.",
        "The complete, raw metadata of the selected image, formatted as a JSON string.",
        "A list of all images from the input list. Images are proportionally scaled to match the aspect ratio of the first image, then cropped to its resolution.",
        "A list of all positive prompts from the input list.",
        "A list of all negative prompts from the input list.",
        "A list of all parsed parameter sets (as JSON strings).",
        "A list of all filtered parameter sets (as multi-line strings).",
        "A list of all raw metadata sets (as JSON strings)."
    )

    FUNCTION = "extract_metadata"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Extracts, parses, and filters metadata from image files or direct image inputs, providing synchronized image and text outputs."

    def _parse_png_parameters(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        parsed_data = {"positive_prompt": "", "negative_prompt": "", "parsed_params": {}}
        params_str = metadata.get('metadata', {}).get('parameters', '')
        if not isinstance(params_str, str):
            metadata.update(parsed_data)
            return metadata

        neg_prompt_index = params_str.find('Negative prompt:')
        steps_index = params_str.find('Steps:')
        
        if neg_prompt_index != -1:
            parsed_data['positive_prompt'] = params_str[:neg_prompt_index].strip()
            end_index = steps_index if steps_index != -1 else len(params_str)
            parsed_data['negative_prompt'] = params_str[neg_prompt_index + len('Negative prompt:'):end_index].strip()
        elif steps_index != -1:
            parsed_data['positive_prompt'] = params_str[:steps_index].strip()
        else:
            parsed_data['positive_prompt'] = params_str.strip()

        parsed_data['parsed_params']['positive_prompt'] = parsed_data['positive_prompt']
        parsed_data['parsed_params']['negative_prompt'] = parsed_data['negative_prompt']

        param_patterns = {
            'steps': r'Steps: (.*?)(?:,|$)', 'sampler': r'Sampler: (.*?)(?:,|$)',
            'cfg scale': r'CFG scale: (.*?)(?:,|$)', 'seed': r'Seed: (.*?)(?:,|$)',
            'size': r'Size: (.*?)(?:,|$)', 'model': r'Model: (.*?)(?:,|$)',
            'denoising strength': r'Denoising strength: (.*?)(?:,|$)', 'clip skip': r'Clip skip: (.*?)(?:,|$)',
            'hires upscale': r'Hires upscale: (.*?)(?:,|$)', 'hires steps': r'Hires steps: (.*?)(?:,|$)',
            'hires upscaler': r'Hires upscaler: (.*?)(?:,|$)', 'lora hashes': r'Lora hashes: "(.*?)"(?:,|$)'
        }
        for key, pattern in param_patterns.items():
            match = re.search(pattern, params_str, re.IGNORECASE)
            if match:
                parsed_data['parsed_params'][key] = match.group(1).strip()
        
        metadata.update(parsed_data)
        return metadata

    def _extract_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.png':
                with Image.open(file_path) as img: info = dict(img.info)
                metadata = {"file_path": file_path, "metadata": info}
                return self._parse_png_parameters(metadata)
            else:
                exif_dict = piexif.load(file_path)
                readable_exif = {}
                for ifd, tags in exif_dict.items():
                    if ifd == "thumbnail": continue
                    readable_exif[ifd] = {}
                    for tag, value in tags.items():
                        tag_name = piexif.TAGS.get(ifd, {}).get(tag, {}).get("name", tag)
                        try: readable_exif[ifd][tag_name] = value.decode('utf-8', 'ignore') if isinstance(value, bytes) else value
                        except: readable_exif[ifd][tag_name] = repr(value)
                return {"file_path": file_path, "metadata": readable_exif, "parsed_params": {}, "positive_prompt": "", "negative_prompt": ""}
        except Exception as e:
            return {"file_path": file_path, "error": f"Error reading metadata: {str(e)}", "parsed_params": {}, "positive_prompt": "", "negative_prompt": ""}

    def _resize_and_crop_image(self, img_tensor: torch.Tensor, target_height: int, target_width: int) -> torch.Tensor:
        # img_tensor is HWC, convert to CHW for F.
        img_tensor_chw = img_tensor.permute(2, 0, 1)
        
        _, current_height, current_width = img_tensor_chw.shape

        # Calculate aspect ratios
        target_aspect = target_width / target_height
        current_aspect = current_width / current_height

        if current_aspect > target_aspect:
            # Image is wider than target, scale by height and then crop width
            scale_factor = target_height / current_height
            new_width = int(current_width * scale_factor)
            new_height = target_height
            resized_tensor = F.resize(img_tensor_chw, [new_height, new_width])
            
            # Calculate crop coordinates for width
            left = (new_width - target_width) / 2
            top = 0
            cropped_tensor = F.crop(resized_tensor, int(top), int(left), target_height, target_width)
        else:
            # Image is taller or same aspect ratio, scale by width and then crop height
            scale_factor = target_width / current_width
            new_height = int(current_height * scale_factor)
            new_width = target_width
            resized_tensor = F.resize(img_tensor_chw, [new_height, new_width])

            # Calculate crop coordinates for height
            left = 0
            top = (new_height - target_height) / 2
            cropped_tensor = F.crop(resized_tensor, int(top), int(left), target_height, target_width)
        
        return cropped_tensor.permute(1, 2, 0) # Convert back to HWC

    def extract_metadata(self, seed: int, input_path: str = None, image_input=None, filter_params: str = "", max_file_count: int = 0):
        all_images, all_metadata = [], []

        if image_input is not None:
            all_images = list(image_input)
            for i in range(len(all_images)):
                all_metadata.append({"file_path": f"from_image_input_{i}", "metadata": {"source": "direct_input"}, "parsed_params": {}, "positive_prompt": "", "negative_prompt": ""})
        elif input_path:
            if not os.path.isabs(input_path):
                from folder_paths import get_input_directory
                input_dir = get_input_directory()
                if not input_dir or not os.path.isdir(input_dir): return (None,)*12
                input_path = os.path.join(input_dir, input_path)

            supported_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif']
            files_found = [os.path.join(input_path, f) for f in sorted(os.listdir(input_path)) if os.path.splitext(f)[1].lower() in supported_exts] if os.path.isdir(input_path) else ([input_path] if os.path.isfile(input_path) else [])

            for file_path in files_found:
                try:
                    img = Image.open(file_path).convert("RGB")
                    image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)
                    all_images.append(image_tensor)
                    all_metadata.append(self._extract_metadata_from_file(file_path))
                except Exception as e:
                    print(f"Skipping file {file_path}: {e}")

        if not all_images:
            return (torch.zeros((1, 64, 64, 3)), "", "", "{}", "", "{}", torch.zeros((0, 64, 64, 3)), [], [], [], [], [])

        # --- Rotation ---
        current_index = seed % len(all_images)
        final_images = all_images[current_index:] + all_images[:current_index]
        final_metadata = all_metadata[current_index:] + all_metadata[:current_index]

        if max_file_count > 0:
            final_images = final_images[:max_file_count]
            final_metadata = final_metadata[:max_file_count]

        # --- Image Batching and Resizing ---
        first_image_height, first_image_width = final_images[0].shape[0], final_images[0].shape[1] # (H, W)
        resized_images = []
        for i, img_tensor in enumerate(final_images):
            current_height, current_width = img_tensor.shape[0], img_tensor.shape[1]
            if current_height != first_image_height or current_width != first_image_width:
                print(f"MetadataExtractor Warning: Image {i+1} (H:{current_height}, W:{current_width}) does not match first image dimensions (H:{first_image_height}, W:{first_image_width}). Resizing and cropping.")
            # Apply proportional scaling and cropping
            processed_tensor = self._resize_and_crop_image(img_tensor, first_image_height, first_image_width)
            resized_images.append(processed_tensor)

        image_list = torch.stack(resized_images)

        # --- Filter Logic ---
        filter_keys = [k.strip().lower() for k in filter_params.split(',') if k.strip()]
        def get_filtered_values(params_dict):
            return [str(params_dict.get(key, '')) for key in filter_keys]

        # --- Single Outputs ---
        image_single = final_images[0].unsqueeze(0)
        meta_single = final_metadata[0]
        pos_prompt_single = meta_single.get('positive_prompt', '')
        neg_prompt_single = meta_single.get('negative_prompt', '')
        parsed_params_single = meta_single.get('parsed_params', {})
        filtered_params_single_list = get_filtered_values(parsed_params_single)
        raw_meta_single_json = json.dumps(meta_single.get('metadata', {}), indent=4, default=str)
        parsed_params_single_json = json.dumps(parsed_params_single, indent=4, default=str)

        # --- List Outputs ---
        pos_prompt_list = [m.get('positive_prompt', '') for m in final_metadata]
        neg_prompt_list = [m.get('negative_prompt', '') for m in final_metadata]
        parsed_params_list_json = [json.dumps(m.get('parsed_params', {}), indent=4, default=str) for m in final_metadata]
        filtered_params_list_grouped = ["\n".join(get_filtered_values(m.get('parsed_params', {}))) for m in final_metadata]
        raw_meta_list_json = [json.dumps(m.get('metadata', {}), indent=4, default=str) for m in final_metadata]

        return (
            image_single, pos_prompt_single, neg_prompt_single, parsed_params_single_json, filtered_params_single_list, raw_meta_single_json,
            image_list, pos_prompt_list, neg_prompt_list, parsed_params_list_json, filtered_params_list_grouped, raw_meta_list_json
        )