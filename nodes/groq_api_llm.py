import os
import json
import random
import numpy as np
import torch
from colorama import Fore, Style
from groq import Groq

from ..utils.api_utils import make_api_request, load_prompt_options, get_prompt_content
from ..utils.env_manager import ensure_env_file, get_api_key
from ..utils.settings_utils import is_groq_llm_console_log_enabled, get_groq_llm_request_timeout

from comfy_api.latest import io

# Lazily-initialised API key and prompt options, shared by every instance of the
# node. V3 nodes execute as classmethods, so this replaces the old __init__.
_CONTEXT = None


def _get_context():
    """Return (api_key, prompt_options), initialising them on first use."""
    global _CONTEXT
    if _CONTEXT is None:
        current_directory = os.path.dirname(os.path.realpath(__file__))
        groq_directory = os.path.join(current_directory, 'groq')

        # Get API key from env file
        ensure_env_file()
        api_key = get_api_key()
        Groq(api_key=api_key)

        # Load prompt options
        prompt_files = [
            os.path.join(groq_directory, 'DefaultPrompts.json'),
            os.path.join(groq_directory, 'UserPrompts.json')
        ]
        _CONTEXT = (api_key, load_prompt_options(prompt_files))
    return _CONTEXT


class GroqAPILLM(io.ComfyNode):
    DEFAULT_PROMPT = "Use [system_message] and [user_input]"
    
    # Deprecation List - https://console.groq.com/docs/deprecations

    LLM_MODELS = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "moonshotai/kimi-k2-instruct-0905",
        "deepseek-r1-distill-llama-70b",
        "qwen-qwq-32b",
        "gemma2-9b-it",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "llama-guard-3-8b",
        "meta-llama/llama-guard-4-12b",
        "meta-llama/llama-prompt-guard-2-22m",
        "meta-llama/llama-prompt-guard-2-86m",
        "openai/gpt-oss-safeguard-20b",
        "qwen/qwen3-32b",
    ]
    
    @classmethod
    def define_schema(cls) -> io.Schema:
        try:
            current_directory = os.path.dirname(os.path.realpath(__file__))
            groq_directory = os.path.join(current_directory, 'groq')
            prompt_files = [
                os.path.join(groq_directory, 'DefaultPrompts.json'),
                os.path.join(groq_directory, 'UserPrompts.json')
            ]
            prompt_options = load_prompt_options(prompt_files)
        except Exception as e:
            print(Fore.RED + f"Failed to load prompt options: {e}" + Style.RESET_ALL)
            prompt_options = {}
    
        return io.Schema(
            node_id="MNeMiC_GroqAPILLM",
            display_name="✨💬 Groq LLM API",
            category="⚡ MNeMiC Nodes",
            description="Uses Groq API to generate text from language models.",
            inputs=[
                io.Combo.Input("model", options=cls.LLM_MODELS, tooltip="Select the Large Language Model (LLM) to use."),
                io.Combo.Input("preset", options=[cls.DEFAULT_PROMPT] + list(prompt_options.keys()), tooltip="Select a preset or custom prompt for guiding the LLM."),
                io.String.Input("system_message", multiline=True, default="", tooltip="Optional system message to guide the LLM's behavior."),
                io.String.Input("user_input", multiline=True, default="", tooltip="User input or prompt to generate a response from the LLM."),
                io.Float.Input("temperature", default=0.85, min=0.1, max=2.0, step=0.05, tooltip="Controls randomness in responses.\n\nA higher temperature makes the model take more risks, leading to more creative or varied answers.\n\nA lower temperature (closer to 0.1) makes the model more focused and predictable."),
                io.Int.Input("max_tokens", advanced=True, default=1024, min=1, max=131072, step=1, tooltip="Maximum number of tokens to generate in the response."),
                io.Float.Input("top_p", advanced=True, default=1.0, min=0.1, max=1.0, step=0.01, tooltip="Limits the pool of words the model can choose from based on their combined probability.\n\nSet it closer to 1 to allow more variety in output. Lowering this (e.g., 0.9) will restrict the output to the most likely words, making responses more focused."),
                io.Int.Input("seed", advanced=True, default=42, min=0, max=4294967295, tooltip="Seed for random number generation, ensuring reproducibility."),
                io.Int.Input("max_retries", advanced=True, default=2, min=1, max=10, step=1, tooltip="Maximum number of retries in case of request failure."),
                io.String.Input("stop", advanced=True, default="", tooltip="Stop generation when the specified sequence is encountered."),
                io.Boolean.Input("json_mode", advanced=True, default=False, tooltip="Enable JSON mode for structured output.\n\nIMPORTANT: Requires you to use the word 'JSON' in the prompt."),
            ],
            outputs=[
                io.String.Output(display_name="api_response", tooltip="The API response. This is the text generated by the model"),
                io.Boolean.Output(display_name="success", tooltip="Whether the request was successful"),
                io.String.Output(display_name="status_code", tooltip="The status code of the request"),
            ],
        )

    @classmethod
    def execute(cls, model, preset, system_message, user_input, temperature, max_tokens, top_p, seed, max_retries, stop, json_mode) -> io.NodeOutput:
        api_key, prompt_options_loaded = _get_context()
        # Set the seed for reproducibility
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)
    
        if preset == cls.DEFAULT_PROMPT:
            system_message = system_message
        else:
            system_message = get_prompt_content(prompt_options_loaded, preset)
    
        url = 'https://api.groq.com/openai/v1/chat/completions'
        headers = {'Authorization': f'Bearer {api_key}'}
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]
       
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
        
        console_log = is_groq_llm_console_log_enabled()
        if console_log:
            print(f"Sending request to {url} with data: {json.dumps(data, indent=4)} and headers: {{'Authorization': 'Bearer ***'}}")

        assistant_message, success, status_code = make_api_request(data, headers, url, max_retries, console_log=console_log, timeout=get_groq_llm_request_timeout())
        return io.NodeOutput(assistant_message, success, status_code)
