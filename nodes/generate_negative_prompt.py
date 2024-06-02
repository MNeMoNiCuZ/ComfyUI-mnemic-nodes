import os
import re
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2Config

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
        current_directory = os.path.dirname(os.path.realpath(__file__))
        model_directory = 'negativeprompt'
        model_path = os.path.join(current_directory, model_directory)

        print(f"Negative Prompt Model Path: {model_path}")
        
        tokenizer = GPT2Tokenizer.from_pretrained(model_path)
        config = GPT2Config.from_json_file(os.path.join(model_path, 'config.json'))
        model = GPT2LMHeadModel(config)
        model_weights = torch.load(os.path.join(model_path, 'weights.pt'))
        model.load_state_dict(model_weights)
        model.eval()

        input_ids = tokenizer.encode(input_prompt, return_tensors='pt')

        output = model.generate(
            input_ids,
            max_length=max_length + input_ids.shape[-1],
            num_beams=num_beams,
            temperature=temperature,
            early_stopping=False,
            no_repeat_ngram_size=2,
            num_return_sequences=1,
            top_k=top_k,
            top_p=top_p,
        )

        output_text = tokenizer.decode(output[0], skip_special_tokens=True)
        input_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
        generated_text = output_text[len(input_text):]

        generated_text = re.sub(r'^[,\s]+', '', generated_text)
        generated_text = re.sub(r'[,\s]+$', '', generated_text)

        if blocked_words:
            blocked_words_list = blocked_words.split('\n')
            for word in blocked_words_list:
                if word.strip():
                    generated_text = generated_text.replace(word, "")

        return generated_text,
