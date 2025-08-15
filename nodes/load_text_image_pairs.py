import os
import torch
import numpy as np
from PIL import Image
import torchvision.transforms.functional as F
from typing import List, Tuple

class LoadTextImagePairs:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed determines the starting point for selecting pairs. Set to 'increment' in the workflow options to cycle through all available pairs sequentially."}),
            },
            "optional": {
                "folder_path": ("STRING", {"multiline": False, "default": "", "tooltip": "Path to a folder containing image and text files with matching basenames. This is used only if image_input and text_input are not connected."}),
                "image_input": ("IMAGE", {"tooltip": "A single image or a list/batch of images. This input has priority over the folder_path."}),
                "text_input": ("STRING", {"forceInput": True, "tooltip": "A single text string or a list of strings. This input has priority over the folder_path."}),
                "max_pair_count": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1, "tooltip": "The maximum number of pairs to return in the output lists. If set to 0, all found pairs will be returned."}),
                "text_format_extension": ("STRING", {"default": "txt", "tooltip": "The file extension for the text files to look for (without the dot)."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image_single_output", "string_single_output", "image_list_output", "string_list_output", "full_path_single", "filename_single", "full_path_list", "filename_list")
    OUTPUT_TOOLTIPS = (
        "The single image selected by the seed. Its position in the list determines which item is chosen from the dataset.",
        "The text string that is paired with the selected image.",
        "A list of all images from the dataset, rotated so that the selected image is the first item in the list.",
        "A list of all text strings from the dataset, rotated so that the selected text is the first item in the list.",
        "The full absolute path of the selected image.",
        "The filename (without extension) of the selected image.",
        "A list of full absolute paths of all images.",
        "A list of filenames (without extension) of all images."
    )
    FUNCTION = "load_pairs"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Loads text-image pairs, selects one based on a seed, and provides a rotated list output."

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

    def load_pairs(self, seed, folder_path=None, image_input=None, text_input=None, max_pair_count=0, text_format_extension="txt"):
        print("LoadTextImagePairs: Starting stateless process.")
        all_images, all_texts, all_image_paths, all_image_basenames = [], [], [], []

        # --- Data Loading ---
        has_input_connection = image_input is not None or text_input is not None
        
        if has_input_connection:
            print("LoadTextImagePairs: Loading from direct input.")
            # Standardize inputs to lists
            images = image_input if isinstance(image_input, list) else ([image_input] if image_input is not None else [])
            texts = text_input if isinstance(text_input, list) else ([text_input] if text_input is not None else [])

            # Handle tensor vs. list for images
            if images and isinstance(images[0], torch.Tensor) and images[0].ndim == 4:
                # Batch of tensors
                img_list = [img.unsqueeze(0) for img in images[0]]
            else:
                img_list = images

            img_len, txt_len = len(img_list), len(texts)

            if img_len == 0 and txt_len > 0:
                print(f"LoadTextImagePairs Warning: Received {txt_len} texts but no images. Cannot form pairs.")
                return (None, None, None, [], "", "", [], [])
            if txt_len == 0 and img_len > 0:
                print(f"LoadTextImagePairs Warning: Received {img_len} images but no texts. Cannot form pairs.")
                return (None, None, None, [], "", "", [], [])

            if img_len != txt_len:
                print(f"LoadTextImagePairs Warning: Mismatched inputs. Got {img_len} images and {txt_len} texts. Using the smaller count: {min(img_len, txt_len)}.")
            
            min_len = min(img_len, txt_len)
            all_images.extend(img_list[:min_len])
            all_texts.extend(texts[:min_len])

        elif folder_path:
            print(f"LoadTextImagePairs: Loading from folder: {folder_path}")
            folder_path = os.path.normpath(folder_path)
            if not os.path.isabs(folder_path):
                from folder_paths import get_input_directory
                input_dir = get_input_directory()
                if not input_dir or not os.path.isdir(input_dir):
                     return (None, None, None, [], "", "", [], [])
                folder_path = os.path.join(input_dir, folder_path)

            if os.path.isdir(folder_path):
                image_files, text_files = {}, {}
                image_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
                text_exts = [f'.{text_format_extension.lower()}']
                for f in sorted(os.listdir(folder_path)):
                    basename, ext = os.path.splitext(f)
                    if ext.lower() in image_exts: image_files[basename] = os.path.join(folder_path, f)
                    elif ext.lower() in text_exts: text_files[basename] = os.path.join(folder_path, f)
                
                for basename in sorted(image_files.keys()):
                    if basename in text_files:
                        try:
                            i = Image.open(image_files[basename]).convert("RGB")
                            image = np.array(i).astype(np.float32) / 255.0
                            all_images.append(torch.from_numpy(image)[None,])
                            with open(text_files[basename], 'r', encoding='utf-8') as f_text:
                                all_texts.append(f_text.read())
                            all_image_paths.append(image_files[basename])
                            all_image_basenames.append(basename)
                        except Exception as e:
                            print(f"LoadTextImagePairs Error: Could not load pair for {basename}: {e}")

        if not all_images or not all_texts:
            print("LoadTextImagePairs: No valid image-text pairs were found.")
            # Create a black image tensor as a placeholder
            black_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            black_image_list = torch.zeros((0, 64, 64, 3), dtype=torch.float32)
            return (black_image, "", black_image_list, [], "", "", [], [])

        # --- Main Logic ---
        # The seed loops through all available pairs.
        current_index = seed % len(all_images)
        print(f"LoadTextImagePairs: Seed {seed} on list of {len(all_images)} => index {current_index}")

        # Get the single item.
        image_single = all_images[current_index]
        string_single = all_texts[current_index]
        full_path_single = all_image_paths[current_index] if all_image_paths else ""
        filename_single = all_image_basenames[current_index] if all_image_basenames else ""

        # The list output is always a rotation of the full list.
        rotated_images = all_images[current_index:] + all_images[:current_index]
        rotated_texts = all_texts[current_index:] + all_texts[:current_index]
        rotated_paths = all_image_paths[current_index:] + all_image_paths[:current_index] if all_image_paths else []
        rotated_basenames = all_image_basenames[current_index:] + all_image_basenames[:current_index] if all_image_basenames else []

        # The list is then sliced by max_pair_count.
        if max_pair_count > 0:
            final_images = rotated_images[:max_pair_count]
            final_texts = rotated_texts[:max_pair_count]
            final_paths = rotated_paths[:max_pair_count]
            final_basenames = rotated_basenames[:max_pair_count]
        else:
            final_images = rotated_images
            final_texts = rotated_texts
            final_paths = rotated_paths
            final_basenames = rotated_basenames

        # --- Image Batching and Resizing ---
        if final_images:
            first_image_height, first_image_width = final_images[0].shape[1], final_images[0].shape[2] # (B, H, W, C) -> (H, W)
            processed_images = []
            for i, img_tensor in enumerate(final_images):
                current_height, current_width = img_tensor.shape[1], img_tensor.shape[2]
                if current_height != first_image_height or current_width != first_image_width:
                    print(f"LoadTextImagePairs Warning: Image {i+1} (H:{current_height}, W:{current_width}) does not match first image dimensions (H:{first_image_height}, W:{first_image_width}). Resizing and cropping.")
                    # Remove the batch dimension (B, H, W, C) -> (H, W, C) for _resize_and_crop_image
                    img_tensor_hwc = img_tensor.squeeze(0)
                    processed_tensor_hwc = self._resize_and_crop_image(img_tensor_hwc, first_image_height, first_image_width)
                    # Add the batch dimension back (H, W, C) -> (1, H, W, C)
                    processed_images.append(processed_tensor_hwc.unsqueeze(0))
                else:
                    processed_images.append(img_tensor)
            image_list = torch.cat(processed_images, dim=0)
        else:
            image_list = None
            
        string_list = final_texts

        return (image_single, string_single, image_list, string_list, full_path_single, filename_single, final_paths, final_basenames)
