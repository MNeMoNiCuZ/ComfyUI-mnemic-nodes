import base64
from PIL import Image
import numpy as np
from io import BytesIO
import re
import piexif

def encode_image(image_pil):
    """
    Encode a PIL Image as a base64-encoded JPEG string.
    
    Converts the given PIL Image to JPEG bytes in-memory and returns a UTF-8
    base64 string of those bytes. Returns None if encoding fails.
    
    Parameters:
        image_pil (PIL.Image.Image): Image to encode as JPEG.
    
    Returns:
        str | None: Base64-encoded JPEG string on success, or None on error.
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
    
    Accepts a tensor with shape [H, W, 3] or a single-item batch [1, H, W, 3]. The function will remove a leading batch dimension of 1 if present, move the tensor to CPU, convert to a NumPy array, scale values from the expected [0, 1] float range to [0, 255], cast to uint8, and return a PIL.Image in RGB mode.
    
    Parameters:
        image_tensor (torch.Tensor): Image tensor with channels-last layout and values in [0, 1].
            Accepted shapes: [H, W, 3] or [1, H, W, 3].
    
    Returns:
        PIL.Image.Image: The resulting RGB image.
    
    Raises:
        TypeError: If the tensor does not have shape [H, W, 3] (after optional batch squeeze) or does not have 3 channels.
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
    Save a PIL Image to disk at the given path.
    
    Parameters:
        image_pil (PIL.Image.Image): Image to write.
        filename (str): Destination filepath; image format is inferred from the filename extension.
    
    Returns:
        str or None: The filename on success, or None if an error occurred while saving.
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
    Extracts a "positive_prompt" string from an image's embedded metadata.
    
    This function opens the image at file_path and attempts to extract a positive prompt string commonly stored by image-generation tools:
    - For PNGs: reads img.info['parameters'] and returns the substring before "Negative prompt:" or "Steps:" (or the whole string if neither token is found).
    - For JPEGs: loads EXIF via piexif and returns the first line of the Exif UserComment (if present).
    
    Returns {"positive_prompt": ""} when no suitable metadata is found or if an error occurs.
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
