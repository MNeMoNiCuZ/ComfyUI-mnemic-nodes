import os
import re
import time
import socket
import datetime
import requests
import torch
import numpy as np
import json
from PIL import Image
from io import BytesIO
from configparser import ConfigParser
from groq import Groq
from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2Config
from torchvision.transforms.functional import to_tensor


###############################################################################################
# Save Text File
###############################################################################################
# SaveTextFile originally from YMC_Node_Suite. Refactored here to provide an output of the name
# Replace Tokens method to be used by SaveTextFile
def replace_tokens(string, custom_tokens=None):
    # Define a simple token replacement dictionary
    tokens = {
        '[hostname]': socket.gethostname()
    }
    if custom_tokens:
        tokens.update(custom_tokens)

    # Replace simple tokens
    for token, value in tokens.items():
        string = string.replace(token, value)

    # Handle formatted time tokens
    time_format_pattern = r'\[time\((.*?)\)\]'
    matches = re.findall(time_format_pattern, string)
    for match in matches:
        time_token = f'[time({match})]'
        formatted_time = datetime.datetime.now().strftime(match)
        string = string.replace(time_token, formatted_time)

    return string


# set INPUT_TYPES
class SaveTextFile:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "path": ("STRING", {"default": './output/[time(%Y-%m-%d)]/', "multiline": False}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "filename_delimiter": ("STRING", {"default":"_"}),
                "filename_number_padding": ("INT", {"default":4, "min":2, "max":9, "step":1}),
                "overwrite_mode": (["false", "prefix_as_filename"],),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "output_file_name")
    FUNCTION = "save_text_file"
    CATEGORY = "⚡ MNeMiC Nodes"

    def save_text_file(self, text, path, filename_prefix='ComfyUI', filename_delimiter='_', filename_number_padding=4, overwrite_mode='false'):
    
        path = replace_tokens(path)
        filename_prefix = replace_tokens(filename_prefix)
    
        if not os.path.exists(path):
            print(f"Warning: The path `{path}` doesn't exist! Creating it...")
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                print(f"Error: The path `{path}` could not be created! Is there write access?\n{e}")

        if text.strip() == '':
            print(f"There is no text specified to save! Text is empty.").error.print()

        
        delimiter = filename_delimiter
        number_padding = int(filename_number_padding)
        file_extension = '.txt'

        filename, counter = self.generate_filename(path, filename_prefix, delimiter, number_padding, file_extension)
        if overwrite_mode == 'prefix_as_filename':
            filename = f"{filename_prefix}{file_extension}"
        file_path = os.path.join(path, filename)

        output_file_name = f"{filename_prefix}{delimiter}{str(counter).zfill(number_padding)}"

        self.writeTextFile(file_path, text)

        return text, output_file_name
        
    def generate_filename(self, path, prefix, delimiter, number_padding, extension):
        pattern = f"{re.escape(prefix)}{re.escape(delimiter)}(\\d{{{number_padding}}})"
        existing_counters = [
            int(re.search(pattern, filename).group(1))
            for filename in os.listdir(path)
            if re.match(pattern, filename)
        ]
        existing_counters.sort(reverse=True)

        if existing_counters:
            counter = existing_counters[0] + 1
        else:
            counter = 1

        filename = f"{prefix}{delimiter}{counter:0{number_padding}}{extension}"
        return filename, counter

    def writeTextFile(self, file, content):
        try:
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
        except OSError:
            print(f"Unable to save file `{file}`").error.print()

###############################################################################################
# Save Image From Web
###############################################################################################
def pil2tensor(image):
    """Convert a PIL Image to a PyTorch tensor."""
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class FetchAndSaveImage:
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "INT", "INT")  # Image, Width, Height
    RETURN_NAMES = ("image", "width", "height")
    FUNCTION = "FetchAndSaveImage"
    CATEGORY = "⚡ MNeMiC Nodes"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_url": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "save_file_name_override": ("STRING", {"default": "", "multiline": False}),
                "save_path": ("STRING", {"default": "", "multiline": False})
            }
        }

    def FetchAndSaveImage(self, image_url, save_path='', save_file_name_override=''):
        if not image_url:
            print("Error: No image URL provided.")
            return None, None, None

        file_extension = os.path.splitext(image_url)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            print(f"Error: Unsupported image format `{file_extension}`")
            return None, None, None

        try:
            response = requests.get(image_url)
            if response.status_code != 200:
                print(f"Error: Failed to fetch image from URL with status code {response.status_code}")
                return None, None, None

            image = Image.open(BytesIO(response.content)).convert('RGB')
            width, height = image.size

            if save_path:
                if save_file_name_override:
                    filename = save_file_name_override + (file_extension if '.' not in save_file_name_override else '')
                else:
                    filename = os.path.basename(image_url)
                    if '.' not in filename:
                        filename += '.' + (file_extension if file_extension else 'png')

                file_path = os.path.join(save_path, filename)
                if not os.path.exists(save_path):
                    os.makedirs(save_path, exist_ok=True)
                image.save(file_path, 'PNG')  # Save as PNG to overwrite if exists

            image_tensor = pil2tensor(image)

        except Exception as e:
            print(f"Error processing the image: {e}")
            return None, None, None

        return image_tensor, width, height

###############################################################################################
# Groq Completion
###############################################################################################
class GroqAPICompletion:
    DEFAULT_PROMPT = "Use [system_message] and [user_input]"
    
    def __init__(self):
        current_directory = os.path.dirname(os.path.realpath(__file__))
        groq_directory = os.path.join(current_directory, 'groq')
        config_path = os.path.join(groq_directory, 'GroqConfig.ini')
        self.config = ConfigParser()
        self.config.read(config_path)
        self.api_key = self.config.get('API', 'key')
        self.client = Groq(api_key=self.api_key)
        self.prompt_options = self.load_prompt_options()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (["mixtral-8x7b-32768", "llama3-70b-8192", "llama3-8b-8192", "gemma-7b-it"],),
                "preset": ([cls.DEFAULT_PROMPT] + list(cls.load_prompt_options().keys()),),
                "system_message": ("STRING", {"multiline": True, "default": ""}),
                "user_input": ("STRING", {"multiline": True, "default": ""}),
                "temperature": ("FLOAT", {"default": 0.85, "min": 0.1, "max": 1.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 4096, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.01}),
                "seed": ("INT", {"default": 42, "min": 0}),
                "max_retries": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "stop": ("STRING", {"default": ""}),
                "json_mode": ("BOOLEAN", {"default": False})
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("api_response", "success", "status_code")
    FUNCTION = "process_completion_request"
    CATEGORY = "⚡ MNeMiC Nodes"

    def process_completion_request(self, model, preset, system_message, user_input, temperature, max_tokens, top_p, seed, max_retries, stop, json_mode):
        system_message = system_message if preset == self.DEFAULT_PROMPT else self.get_prompt_content(preset)
        url = 'https://api.groq.com/openai/v1/chat/completions'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        data = {
            'model': model,
            'messages': [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_input}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'top_p': top_p,
            'seed': seed
        }
        if stop:  # Only add stop if it's not empty
            data['stop'] = stop
        if json_mode:  # Only add response_format if JSON mode is True
            data['response_format'] = {"type": "json_object"}

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

###############################################################################################
# Generate Negative Prompt
###############################################################################################
class GenerateNegativePrompt:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_prompt": ("STRING", {"forceInput": True}),
                "max_length": ("INT", {"default": 100, "min": 1, "max": 1024, "step": 1}),
                "num_beams": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "temperature": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.1}),
                "top_k": ("INT", {"default": 50, "min": 0, "max": 100, "step": 1}),
                "top_p": ("FLOAT", {"default": 0.92, "min": 0.0, "max": 1.0, "step": 0.01}),
                "blocked_words": ("STRING", {"default": "Blocked words, one per line, remove unwanted embeddings or words", "multiline": True}),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("negative_prompt",)
    
    FUNCTION = "generate_negative_prompt"
    CATEGORY = "⚡ MNeMiC Nodes"

    def generate_negative_prompt(self, input_prompt, max_length, num_beams, temperature, top_k, top_p, blocked_words):
        # Define the path to your fine-tuned model and tokenizer
        current_directory = os.path.dirname(os.path.realpath(__file__))
        model_directory = 'negativeprompt'  # Name of the model directory
        model_path = os.path.join(current_directory, model_directory)  # Full path to the model directory

        print(f"Negative Prompt Model Path: {model_path}")
        
        # Load the tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained(model_path)
        
        # Load the configuration from file
        config = GPT2Config.from_json_file(os.path.join(model_path, 'config.json'))

        # Initialize the model with the configuration
        model = GPT2LMHeadModel(config)
        
        # Load the weights into the model
        model_weights = torch.load(os.path.join(model_path, 'weights.pt'))
        model.load_state_dict(model_weights)

        model.eval()  # Set the model to evaluation mode

        # Encode the input prompt to tensor
        input_ids = tokenizer.encode(input_prompt, return_tensors='pt')

        # Generate a sequence of tokens from the input
        output = model.generate(
            input_ids,
            max_length=max_length + input_ids.shape[-1],  # Adjust as needed
            num_beams=num_beams,
            temperature=temperature,
            early_stopping=False,
            no_repeat_ngram_size=2,
            num_return_sequences=1,
            top_k=top_k,
            top_p=top_p,
        )

        # Decode the entire generated sequence to a string
        output_text = tokenizer.decode(output[0], skip_special_tokens=True)

        # Remove the part of the output that matches the input prompt
        input_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
        generated_text = output_text[len(input_text):]

        # Clean up the generated text by removing leading spaces and commas
        generated_text = re.sub(r'^[,\s]+', '', generated_text)

        # Remove any trailing spaces and commas
        generated_text = re.sub(r'[,\s]+$', '', generated_text)

        # Remove blocked words if any
        if blocked_words:
            blocked_words_list = blocked_words.split('\n')
            for word in blocked_words_list:
                if word.strip():
                    generated_text = generated_text.replace(word, "")

        # Return the cleaned up generated text
        return generated_text,
