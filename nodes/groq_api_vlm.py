import os
import json
import random
import numpy as np
import torch
from colorama import init, Fore, Style
from groq import Groq

from ..utils.api_utils import make_api_request, load_prompt_options, get_prompt_content
from ..utils.env_manager import ensure_env_file, get_api_key
from ..utils.image_utils import encode_image, tensor_to_pil

init()  # Initialize colorama

class GroqAPIVLM:
    DEFAULT_PROMPT = "Use [system_message] and [user_input]"
    
    # Deprecation List - https://console.groq.com/docs/deprecations

    VLM_MODELS = [
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    ]
    
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
            os.path.join(groq_directory, 'DefaultPrompts_VLM.json'),
            os.path.join(groq_directory, 'UserPrompts_VLM.json')
        ]
        self.prompt_options = load_prompt_options(prompt_files)
    
    @classmethod
    def INPUT_TYPES(cls):
        try:
            current_directory = os.path.dirname(os.path.realpath(__file__))
            groq_directory = os.path.join(current_directory, 'groq')
            prompt_files = [
                os.path.join(groq_directory, 'DefaultPrompts_VLM.json'),
                os.path.join(groq_directory, 'UserPrompts_VLM.json')
            ]
            prompt_options = load_prompt_options(prompt_files)
        except Exception as e:
            print(Fore.RED + f"Failed to load prompt options: {e}" + Style.RESET_ALL)
            prompt_options = {}
    
        return {
            "required": {
                "model": (cls.VLM_MODELS, {"tooltip": "Select the Vision-Language Model (VLM) to use."}),
                "preset": ([cls.DEFAULT_PROMPT] + list(prompt_options.keys()), {"tooltip": "Select a preset prompt or use a custom prompt for the model."}),
                "system_message": ("STRING", {"multiline": True, "default": "", "tooltip": "Optional system message to guide model behavior."}),
                "user_input": ("STRING", {"multiline": True, "default": "", "tooltip": "User input or prompt for the model to generate a response."}),
                "image": ("IMAGE", {"label": "Image (required for VLM models)", "tooltip": "Upload an image for processing by the VLM model."}),
                "temperature": ("FLOAT", {"default": 0.85, "min": 0.1, "max": 2.0, "step": 0.05, "tooltip": "Controls randomness in responses.\n\nA higher temperature makes the model take more risks, leading to more creative or varied answers.\n\nA lower temperature (closer to 0.1) makes the model more focused and predictable."}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 131072, "step": 1, "tooltip": "Maximum number of tokens to generate in the output."}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.01, "tooltip": "Limits the pool of words the model can choose from based on their combined probability.\n\nSet it closer to 1 to allow more variety in output. Lowering this (e.g., 0.9) will restrict the output to the most likely words, making responses more focused."}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 4294967295, "tooltip": "Seed for random number generation, ensuring reproducibility."}),
                "max_retries": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1, "tooltip": "Maximum number of retries in case of failures."}),
                "stop": ("STRING", {"default": "", "tooltip": "Stop generation when the specified sequence is encountered."}),
                "json_mode": ("BOOLEAN", {"default": False, "tooltip": "Enable JSON mode for structured output.\n\nIMPORTANT: Requires you to use the word 'JSON' in the prompt."}),
            }
        }
    
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("api_response", "success", "status_code")
    OUTPUT_TOOLTIPS = ("The API response. This is the description of your input image generated by the model", "Whether the request was successful", "The status code of the request")
    FUNCTION = "process_completion_request"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Uses Groq API for image processing."
    
    def process_completion_request(self, model, image, temperature, max_tokens, top_p, seed, max_retries, stop, json_mode, preset="", system_message="", user_input=""):
        # Set the seed for reproducibility
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
    
        if preset == self.DEFAULT_PROMPT:
            system_message = system_message
        else:
            system_message = get_prompt_content(self.prompt_options, preset)
    
        url = 'https://api.groq.com/openai/v1/chat/completions'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        if image is not None and isinstance(image, torch.Tensor):
            # Process the image
            image_pil = tensor_to_pil(image)
            base64_image = encode_image(image_pil)
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
            else:
                print(Fore.RED + "Failed to encode image." + Style.RESET_ALL)
                messages = []
        else:
            print(Fore.RED + "Image is required for VLM models." + Style.RESET_ALL)
            return "Image is required for VLM models.", False, "400 Bad Request"
       
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
        
        #print(f"Sending request to {url} with data: {json.dumps(data, indent=4)} and headers: {headers}")
        
        assistant_message, success, status_code = make_api_request(data, headers, url, max_retries)
        return assistant_message, success, status_code
