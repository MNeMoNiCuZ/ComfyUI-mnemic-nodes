import base64
from PIL import Image
import numpy as np
from io import BytesIO
import re
import piexif

def encode_image(image_pil):
    """
    Encode a PIL Image as a base64-encoded JPEG string.
    
    image_pil (PIL.Image.Image): Input image to encode. The image will be saved in JPEG format (modes with alpha will be converted/flattened, and transparency will be lost).
    
    Returns:
        str or None: Base64-encoded UTF-8 string of the JPEG bytes on success, or None if encoding fails.
    """
    try:
        buffered = BytesIO()
        image_pil.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def tensor_to_pil(image_tensor):
    """
    Convert a PyTorch image tensor to a PIL RGB Image.
    
    Accepts a 3D tensor shaped [H, W, 3] or a 4D tensor with a leading batch dim of 1 ([1, H, W, 3]).
    The tensor is moved to CPU, converted to a NumPy array, scaled from [0, 1] to [0, 255], cast to uint8,
    and returned as a PIL.Image.Image in RGB mode.
    
    Parameters:
        image_tensor (torch.Tensor): Image tensor with values typically in [0, 1]. Supported shapes:
            - [H, W, 3]
            - [1, H, W, 3] (batch dimension 1 is removed)
    
    Returns:
        PIL.Image.Image: The converted RGB image.
    
    Raises:
        TypeError: If the tensor shape is not one of the supported formats.
    """
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
    """
    Save a PIL Image to disk at the given filename.
    
    Parameters:
        image_pil (PIL.Image.Image): Image to be written to disk.
        filename (str): Path (including filename) where the image will be saved.
    
    Returns:
        str | None: The provided filename on success; None if saving failed.
    """
    try:
        image_pil.save(filename)
        print(f"Image saved at {filename}")
        return filename
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

def load_image_metadata(file_path):
    """
    Extract a "positive_prompt" string from an image file's embedded metadata (PNG or JPEG).
    
    Attempts to read metadata from the given image file and derive a single-line "positive_prompt" used by some image-generation tools:
    - For PNG: looks for a 'parameters' entry in img.info and returns the substring before "Negative prompt:" if present, otherwise before "Steps:" if present, otherwise the whole parameters string (trimmed).
    - For JPEG: if EXIF data exists, loads it and returns the first line of the Exif UserComment field (decoded as UTF-8, ignoring decode errors).
    
    If metadata is missing, cannot be parsed, or an I/O/error occurs, returns {"positive_prompt": ""} rather than raising.
    Parameters:
        file_path (str): Path to the image file to inspect.
    
    Returns:
        dict: {"positive_prompt": <str>} — the extracted prompt or an empty string when none could be found.
    """
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

    except Exception as e:
        print(f"Could not read metadata from {file_path}: {e}")

    return {"positive_prompt": ""}
