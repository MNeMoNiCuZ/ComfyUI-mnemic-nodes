import os
import re
import time
import socket
import datetime
import requests
from PIL import Image
from io import BytesIO


###############################################################################################
# Hello World Test
###############################################################################################
class PrintHelloWorld:

    @classmethod
    def INPUT_TYPES(cls):
               
        return {"required": {       
                    "text": ("STRING", {"multiline": False, "default": "Hello World"}),
                    }
                }

    RETURN_TYPES = ()
    FUNCTION = "print_text"
    OUTPUT_NODE = True
    CATEGORY = "MNeMiC Nodes"

    def print_text(self, text):

        print(f"Tutorial Text : {text}")
        
        return {}


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
    FUNCTION = "save_text_file"
    CATEGORY = "MNeMiC Nodes"

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

        output_path = f"{filename_prefix}{delimiter}{str(counter).zfill(number_padding)}"

        self.writeTextFile(file_path, text)

        return text, output_path
        
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
class FetchAndSaveImage:
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "INT", "INT")  # Image, Width, Height
    FUNCTION = "FetchAndSaveImage"
    CATEGORY = "MNeMiC Nodes"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_url": ("STRING", {"forceInput": True}),
                "save_path": ("STRING", {"default": './input/', "multiline": False})
            }
        }

    def FetchAndSaveImage(self, image_url, save_path='./input/'):
        # Check for valid image format before downloading
        file_extension = os.path.splitext(image_url)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            if file_extension == '':
                print("Warning: File extension not found in URL, will attempt to fetch image.")
            else:
                print(f"Error: Unsupported image format `{file_extension}`")
                return None, None, None

        # Create the save path directory if it doesn't exist
        if not os.path.exists(save_path):
            os.makedirs(save_path, exist_ok=True)

        try:
            response = requests.get(image_url)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        except requests.RequestException as e:
            print(f"Error: Unable to fetch image from URL `{image_url}`. Details: {e}")
            return None, None, None

        try:
            image = Image.open(BytesIO(response.content))
            width, height = image.size

            # Use a dynamic approach to determine the file extension if not in URL
            if file_extension == '':
                file_extension = image.format.lower()

            filename = os.path.basename(image_url)
            if '.' not in filename:
                filename += '.' + file_extension

            file_path = os.path.join(save_path, filename)
            image.save(file_path)
            print(f"Image saved successfully at `{file_path}`")
            
        except Exception as e:
            print(f"Error processing the image: {e}")
            return None, None, None

        if not isinstance(image, Image.Image):
            print("Error: The fetched image is not a PIL Image object.")
            return None, None, None

        return image, width, height
    
###############################################################################################
# Generate Negative Prompt
###############################################################################################
import os
from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2Config
import torch
import re

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
    FUNCTION = "generate_negative_prompt"
    CATEGORY = "MNeMiC Nodes"

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
