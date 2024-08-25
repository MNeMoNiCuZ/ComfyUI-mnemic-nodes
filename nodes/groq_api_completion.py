import os
import time
import json
import requests
from configparser import ConfigParser
from groq import Groq

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
                    "distil-whisper-large-v3-en"
                ],),
                "preset": ([cls.DEFAULT_PROMPT] + list(cls.load_prompt_options().keys()),),
                "system_message": ("STRING", {"multiline": True, "default": ""}),
                "user_input": ("STRING", {"multiline": True, "default": ""}),
                "temperature": ("FLOAT", {"default": 0.85, "min": 0.1, "max": 2.0, "step": 0.05}), # Max value is 2.0
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 131072, "step": 1}),
                "top_p": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.01}), # Max value is 1.0
                "seed": ("INT", {"default": 42, "min": 0, "max": 4294967295}), # Max value is 4294967295
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
