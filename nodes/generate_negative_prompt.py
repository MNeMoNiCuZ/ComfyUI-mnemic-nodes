import os
import re
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer, GPT2Config

from comfy_api.latest import io


class GenerateNegativePrompt(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_GenerateNegativePrompt",
            display_name="⛔ Generate Negative Prompt",
            category="⚡ MNeMiC Nodes",
            description="EXPERIMENTAL: Generates a negative prompt matching the input.\n\nThe model is quite weak and random though, so it doesn't work well. It mostly just generates random negative prompts trained on CivitAI negative prompts.\n\nNSFW words may appear.",
            inputs=[
                io.String.Input(
                    "input_prompt",
                    force_input=True,
                    tooltip="The positive prompt you want to generate a negative prompt for.",
                ),
                io.Int.Input(
                    "max_length",
                    default=100,
                    min=1,
                    max=1024,
                    step=1,
                    tooltip="Maximum token length of the generated output.",
                ),
                io.Int.Input(
                    "num_beams",
                    default=1,
                    min=1,
                    max=10,
                    step=1,
                    tooltip="Number of beams for beam search. Higher values improve accuracy.",
                ),
                io.Float.Input(
                    "temperature",
                    default=1.0,
                    min=0.1,
                    max=2.0,
                    step=0.1,
                    tooltip="Sampling temperature. Lower values make the output more deterministic.",
                ),
                io.Int.Input(
                    "top_k",
                    default=50,
                    min=0,
                    max=100,
                    step=1,
                    tooltip="Limits how many of the most likely words are considered for each choice.\n\nFor example, top_k=50 means the model picks from the top 50 most likely words.\n\nA lower value narrows the choices, making the output more predictable, while a higher value adds diversity.",
                ),
                io.Float.Input(
                    "top_p",
                    default=0.92,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Limits the pool of words the model can choose from based on their combined probability.\n\nSet it closer to 1 to allow more variety in output. Lowering this (e.g., 0.9) will restrict the output to the most likely words, making responses more focused.",
                ),
                io.String.Input(
                    "blocked_words",
                    default="Blocked words, one per line, remove unwanted embeddings or words",
                    multiline=True,
                    tooltip="Words to exclude from the output.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="negative_prompt", tooltip="The generated negative prompt"),
            ],
        )

    @classmethod
    def execute(cls, input_prompt, max_length, num_beams, temperature, top_k, top_p, blocked_words) -> io.NodeOutput:
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

        return io.NodeOutput(generated_text)
