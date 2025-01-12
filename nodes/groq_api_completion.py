import os
import time
import json
import requests
import random
import numpy as np
import torch
from groq import Groq
import base64
from PIL import Image

from ..utils.api_utils import load_prompt_options, get_prompt_content
from ..utils.env_manager import ensure_env_file, get_api_key

class GroqAPICompletion:
    DEFAULT_PROMPT = "Use [system_message] and [user_input]"
    
    def __init__(self):
        # Set up directories for prompt files
        current_directory = os.path.dirname(os.path.realpath(__file__))
        groq_directory = os.path.join(current_directory, 'groq')
        
        # Get API key from env file
        ensure_env_file()
        self.api_key = get_api_key()
        self.client = Groq(api_key=self.api_key)
        
        # Load prompt options
        prompt_files = [
            os.path.join(groq_directory, 'DefaultPrompts.json'),
            os.path.join(groq_directory, 'UserPrompts.json')
        ]
        self.prompt_options = load_prompt_options(prompt_files)

    @classmethod
    def INPUT_TYPES(cls):
        try:
            prompt_options = cls.load_prompt_options()
        except Exception as e:
            print(f"Failed to load prompt options: {e}")
            prompt_options = {}

        return {
            "required": {
                "model": ([
                    "llama-3.1-8b-instant",
                    "llama-3.1-70b-versatile",
                    "llama3-8b-8192",
                    "llama3-70b-8192",
                    "llama-guard-3-8b",
                    "llama3-groq-8b-8192-tool-use-preview",
                    "llama3-groq-70b-8192-tool-use-preview",
                    "mixtral-8x7b-32768",
                    "gemma-7b-it",
                    "gemma2-9b-it",
                    "whisper-large-v3",
                    "distil-whisper-large-v3-en",
                    "llava-v1.5-7b-4096-preview"
                ],),
                "preset": ([cls.DEFAULT_PROMPT] + list(prompt_options.keys()),),
                "system_message": ("STRING", {"multiline": True, "default": ""}),
                "user_input": ("STRING", {"multiline": True, "default": ""}),
                "temperature": ("FLOAT", {"default": 0.85, "min": 0.1, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 131072, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.01}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 4294967295}),
                "max_retries": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "stop": ("STRING", {"default": ""}),
                "json_mode": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "image": ("IMAGE", {"label": "Image (optional - for llava only)", "optional": True}),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("api_response", "success", "status_code")
    FUNCTION = "process_completion_request"
    CATEGORY = "⚡ MNeMiC Nodes"

    def process_completion_request(self, model, preset, system_message, user_input, temperature, max_tokens, top_p, seed, max_retries, stop, json_mode, image=None):
        # Set the seed for reproducibility
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)

        system_message = system_message if preset == self.DEFAULT_PROMPT else self.get_prompt_content(preset)

        url = 'https://api.groq.com/openai/v1/chat/completions'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]
        
        # If the selected model is llava-v1.5-7b-4096-preview, include the image
        if model == "llava-v1.5-7b-4096-preview":
            if image is not None and isinstance(image, torch.Tensor):
                # Process the image only if it is provided
                image_pil = self.tensor_to_pil(image)
                base64_image = self.encode_image(image_pil)

                if base64_image:
                    combined_message = f"{system_message}\n{user_input}"

                    # Send one single message containing both text and image
                    image_content = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": combined_message},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                    messages = [image_content]
   
        data = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'top_p': top_p,
            'seed': seed
        }
        
        if stop:  # Only add stop if it's not empty
            data['stop'] = stop
        
        print(f"Sending request to {url} with data: {json.dumps(data, indent=4)} and headers: {headers}")
        
        for attempt in range(max_retries):
            response = requests.post(url, headers=headers, json=data)
            print(f"Response status: {response.status_code}, Response body: {response.text}")
            if response.status_code == 200:
                try:
                    response_json = json.loads(response.text)
                    if 'choices' in response_json and response_json['choices']:
                        assistant_message = response_json['choices'][0]['message']['content']
                        print(f"Extracted message: {assistant_message}")
                        return assistant_message, True, "200 OK"
                    else:
                        return "No valid response content found.", False, "200 OK but no content"
                except Exception as e:
                    print(f"Error parsing response: {str(e)}")
                    return "Error parsing JSON response.", False, "200 OK but failed to parse JSON"
            else:
                return "ERROR", False, f"{response.status_code} {response.reason}"

            time.sleep(2)
        
        return "Failed after all retries.", False, "Failed after all retries"

    @classmethod
    def load_prompt_options(cls):
        current_directory = os.path.dirname(os.path.realpath(__file__))
        groq_directory = os.path.join(current_directory, 'groq')
        prompt_options = {}
        json_files = ['DefaultPrompts.json', 'UserPrompts.json']
        for json_file in json_files:
            json_path = os.path.join(groq_directory, json_file)
            try:
                with open(json_path, 'r') as file:
                    prompts = json.load(file)
                    prompt_options.update({prompt['name']: prompt['content'] for prompt in prompts})
            except Exception as e:
                print(f"Failed to load prompts from {json_path}: {str(e)}")
        return prompt_options

    def get_prompt_content(self, prompt_name):
        return self.prompt_options.get(prompt_name, "No content found for selected prompt")

    # Function to encode image in base64
    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    def tensor_to_pil(self, image_tensor):
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

    # Save the image locally for debugging
    def save_image(self, image_pil, filename="vlm_image_temp.png"):
        try:
            current_directory = os.path.dirname(os.path.realpath(__file__))
            groq_directory = os.path.join(current_directory, 'groq')
            image_path = os.path.join(groq_directory, filename)
            image_pil.save(image_path)
            print(f"Image saved at {image_path}")
            return image_path
        except Exception as e:
            print(f"Error saving image: {e}")
            return None