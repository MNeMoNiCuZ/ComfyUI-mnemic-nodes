import os
import torch
import numpy as np
from PIL import Image
import torchvision.transforms.functional as F
from ..utils.file_utils import find_image_text_pairs

class LoadTextImagePairsList:
    def __init__(self):
        self.cached_data = None
        self.cached_folder_path = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed determines the starting point for selecting pairs. Set to 'increment' in the workflow options to cycle through all available pairs sequentially."}),
                "folder_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder containing image and text files with matching basenames. This is used only if image_input and text_input are not connected."}),
                "force_reload": ("BOOLEAN", {"default": False, "tooltip": "If true, forces a reload of data from disk, bypassing the cache."}),
            },
            "optional": {
                "image_input": ("IMAGE", {"tooltip": "A single image or a list/batch of images. This input has priority over the folder_path."}),
                "text_input": ("STRING", {"forceInput": True, "tooltip": "A single text string or a list of strings. This input has priority over the folder_path."}),
                "limit_count": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "The maximum number of pairs to return in the output lists. If set to 0, all found pairs will be returned."}),
                "text_format_extension": ("STRING", {"default": "txt", "tooltip": "The file extension for the text files to look for (without the dot)."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("image_list", "string_list", "image_path_list", "image_filename_list", "total_count")
    OUTPUT_TOOLTIPS = (
        "A list of all images from the dataset, rotated so that the selected image is the first item in the list.",
        "A list of all text strings from the dataset, rotated so that the selected text is the first item in the list.",
        "A list of full absolute paths of all images.",
        "A list of filenames (without extension) of all images.",
        "The total number of pairs found in the dataset."
    )
    FUNCTION = "load_pairs_list"

    def _resize_and_crop_image(self, img_tensor: torch.Tensor, target_height: int, target_width: int) -> torch.Tensor:
        img_tensor_chw = img_tensor.permute(2, 0, 1)
        _, current_height, current_width = img_tensor_chw.shape
        target_aspect = target_width / target_height
        current_aspect = current_width / current_height
        if current_aspect > target_aspect:
            scale_factor = target_height / current_height
            new_width = int(current_width * scale_factor)
            resized_tensor = F.resize(img_tensor_chw, [target_height, new_width])
            left = (new_width - target_width) / 2
            cropped_tensor = F.crop(resized_tensor, 0, int(left), target_height, target_width)
        else:
            scale_factor = target_width / current_width
            new_height = int(current_height * scale_factor)
            resized_tensor = F.resize(img_tensor_chw, [new_height, target_width])
            top = (new_height - target_height) / 2
            cropped_tensor = F.crop(resized_tensor, int(top), 0, target_height, target_width)
        return cropped_tensor.permute(1, 2, 0)

    def load_pairs_list(self, seed, folder_path, force_reload=False, limit_count=0, text_format_extension="txt", image_input=None, text_input=None):
        if image_input is not None and text_input is not None:
            # Handle direct inputs
            # Assuming image_input is a batch of images (tensor)
            # Assuming text_input is a single string or a list of strings
            # Determine the effective number of pairs based on the minimum of images and texts
            num_images = image_input.shape[0]
            
            if isinstance(text_input, str):
                # If text_input is a single string, it applies to all images
                num_texts = num_images
                all_texts_raw = [text_input] * num_images
            else: # Assuming it's a list of strings
                num_texts = len(text_input)
                all_texts_raw = text_input

            total_count = min(num_images, num_texts)

            # Truncate images and texts to the determined total_count
            all_images = [image_input[i:i+1] for i in range(total_count)]
            all_texts = all_texts_raw[:total_count]

            # For direct inputs, paths and basenames are not applicable, so use empty strings
            all_paths = [""] * total_count
            all_basenames = [""] * total_count
            
            # Re-batch images after potential truncation
            batched_images = torch.cat(all_images, dim=0) if all_images else torch.empty(0)

            self.cached_data = (all_images, all_texts, all_paths, all_basenames, batched_images)
            self.cached_folder_path = None # No folder path when using direct inputs
            
            # Skip folder loading logic and proceed to output processing
            current_index = seed % total_count if total_count > 0 else 0

            # Rotate lists
            rotated_texts = all_texts[current_index:] + all_texts[:current_index]
            rotated_paths = all_paths[current_index:] + all_paths[:current_index]
            rotated_basenames = all_basenames[current_index:] + all_basenames[:current_index]

            # Slice lists by limit_count
            if limit_count > 0:
                final_texts = rotated_texts[:limit_count]
                final_paths = rotated_paths[:limit_count]
                final_basenames = rotated_basenames[:limit_count]
                final_images = torch.cat((batched_images[current_index:], batched_images[:current_index]), dim=0)
                final_images = final_images[:limit_count]
            else:
                final_texts = rotated_texts
                final_paths = rotated_paths
                final_basenames = rotated_basenames
                final_images = torch.cat((batched_images[current_index:], batched_images[:current_index]), dim=0)

            return (final_images, final_texts, final_paths, final_basenames, total_count)

        if not force_reload and self.cached_folder_path == folder_path and self.cached_data:
            print("LoadTextImagePairsList: Using cached data.")
            all_images, all_texts, all_paths, all_basenames, batched_images = self.cached_data
        else:
            if not folder_path or not os.path.isdir(folder_path):
                return (None, "", "", "", None, [], [], [], 0)
            
            print("LoadTextImagePairsList: Loading new data from disk.")
            pairs = find_image_text_pairs(folder_path, text_format_extension)
            if not pairs:
                return (None, "", "", "", None, [], [], [], 0)

            all_images, all_texts, all_paths, all_basenames = [], [], [], []
            for image_path, text_path, basename in pairs:
                try:
                    i = Image.open(image_path).convert("RGB")
                    image = np.array(i).astype(np.float32) / 255.0
                    all_images.append(torch.from_numpy(image)[None,])
                    with open(text_path, 'r', encoding='utf-8') as f:
                        all_texts.append(f.read())
                    all_paths.append(image_path)
                    all_basenames.append(basename)
                except Exception as e:
                    print(f"Error loading pair {basename}: {e}")
            
            if not all_images:
                return (None, "", "", "", None, [], [], [], 0)

            first_img_h, first_img_w = all_images[0].shape[1], all_images[0].shape[2]
            processed_images = []
            for img_tensor in all_images:
                if img_tensor.shape[1] != first_img_h or img_tensor.shape[2] != first_img_w:
                    img_tensor_hwc = img_tensor.squeeze(0)
                    processed_tensor_hwc = self._resize_and_crop_image(img_tensor_hwc, first_img_h, first_img_w)
                    processed_images.append(processed_tensor_hwc.unsqueeze(0))
                else:
                    processed_images.append(img_tensor)
            batched_images = torch.cat(processed_images, dim=0)

            self.cached_data = (all_images, all_texts, all_paths, all_basenames, batched_images)
            self.cached_folder_path = folder_path

        total_count = len(all_texts)
        current_index = seed % total_count

        # Rotate lists
        rotated_texts = all_texts[current_index:] + all_texts[:current_index]
        rotated_paths = all_paths[current_index:] + all_paths[:current_index]
        rotated_basenames = all_basenames[current_index:] + all_basenames[:current_index]

        # Slice lists by max_list_count
        if limit_count > 0:
            final_texts = rotated_texts[:limit_count]
            final_paths = rotated_paths[:limit_count]
            final_basenames = rotated_basenames[:limit_count]
            final_images = torch.cat((batched_images[current_index:], batched_images[:current_index]), dim=0)
            final_images = final_images[:limit_count]
        else:
            final_texts = rotated_texts
            final_paths = rotated_paths
            final_basenames = rotated_basenames
            final_images = torch.cat((batched_images[current_index:], batched_images[:current_index]), dim=0)

        return (final_images, final_texts, final_paths, final_basenames, total_count)
