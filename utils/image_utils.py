import base64
from PIL import Image
import numpy as np
from io import BytesIO

def encode_image(image_pil):
    try:
        buffered = BytesIO()
        image_pil.save(buffered, format="JPEG")
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