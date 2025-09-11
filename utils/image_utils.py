import base64
from PIL import Image
import numpy as np
from io import BytesIO
import re
import piexif

def encode_image(image_pil):
    try:
        buffered = BytesIO()
        fmt = "PNG" if ("A" in image_pil.getbands()) else "JPEG"
        image_pil.save(buffered, format=fmt)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def tensor_to_pil(image_tensor):
    import torch
    # Remove batch dimension if it exists (tensor shape [1, H, W, C])
    if image_tensor.ndim == 4 and image_tensor.shape[0] == 1:
        image_tensor = image_tensor.squeeze(0)  # Remove the batch dimension

    # Ensure the tensor is in the form [H, W, C] (height, width, channels)
    if image_tensor.ndim == 3 and image_tensor.shape[2] == 3:  # Expecting RGB image with 3 channels
        image_array = image_tensor.cpu().numpy()
        image_array = (image_array * 255).astype(np.uint8)  # Convert from [0, 1] to [0, 255]
        return Image.fromarray(image_array)
    else:
        raise TypeError(f"Unsupported image tensor shape: {image_tensor.shape}")

def save_image(image_pil, filename):
    try:
        image_pil.save(filename)
        print(f"Image saved at {filename}")
        return filename
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

def load_image_metadata(file_path):
    try:
        with Image.open(file_path) as img:
            # For PNG images, metadata is often in the 'info' attribute
            if 'parameters' in img.info:
                params_str = img.info['parameters']
                # The logic from _parse_png_parameters can be simplified
                neg_prompt_index = params_str.find('Negative prompt:')
                if neg_prompt_index != -1:
                    positive_prompt = params_str[:neg_prompt_index].strip()
                else:
                    steps_index = params_str.find('Steps:')
                    if steps_index != -1:
                        positive_prompt = params_str[:steps_index].strip()
                    else:
                        positive_prompt = params_str.strip()
                return {"positive_prompt": positive_prompt}
            # For JPEG images, metadata might be in EXIF
            elif 'exif' in img.info:
                exif_dict = piexif.load(img.info['exif'])
                user_comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment, b'').decode('utf-8', 'ignore')
                # This is just a guess, the actual structure can vary a lot.
                # A1111 saves parameters in user comment.
                if user_comment:
                    # Very basic parsing, might need improvement
                    return {"positive_prompt": user_comment.split('\n')[0]}

    except (OSError, ValueError, KeyError, UnicodeDecodeError) as e:
        print(f"Could not read metadata from {file_path}: {e}")

    return {"positive_prompt": ""}
