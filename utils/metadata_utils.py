import os
import re
import json
import piexif
import torch
import numpy as np
from PIL import Image
import torchvision.transforms.functional as F
from typing import Dict, Any

def _parse_png_parameters(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to parse parameters from PNG metadata."""
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

def extract_metadata_from_file(file_path: str) -> Dict[str, Any]:
    """Extracts and parses metadata from a single image file."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.png':
            with Image.open(file_path) as img: info = dict(img.info)
            metadata = {"file_path": file_path, "metadata": info}
            return _parse_png_parameters(metadata)
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

def resize_and_crop_image(img_tensor: torch.Tensor, target_height: int, target_width: int) -> torch.Tensor:
    """Resizes and crops a tensor image to a target resolution while maintaining aspect ratio."""
    img_tensor_chw = img_tensor.permute(2, 0, 1)
    _, current_height, current_width = img_tensor_chw.shape
    target_aspect = target_width / target_height
    current_aspect = current_width / current_height

    if current_aspect > target_aspect:
        scale_factor = target_height / current_height
        new_width, new_height = int(current_width * scale_factor), target_height
        resized_tensor = F.resize(img_tensor_chw, [new_height, new_width])
        left, top = (new_width - target_width) / 2, 0
        cropped_tensor = F.crop(resized_tensor, int(top), int(left), target_height, target_width)
    else:
        scale_factor = target_width / current_width
        new_height, new_width = int(current_height * scale_factor), target_width
        resized_tensor = F.resize(img_tensor_chw, [new_height, new_width])
        left, top = 0, (new_height - target_height) / 2
        cropped_tensor = F.crop(resized_tensor, int(top), int(left), target_height, target_width)
    
    return cropped_tensor.permute(1, 2, 0)
