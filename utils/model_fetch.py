import configparser
import os
import openai
from groq import Groq
from enum import Enum

# Instructions for future integration
"""
Usage:

1. To fetch models from a provider (Groq or OpenAI), use:
   `fetch_provider_models(provider, model_type)`

2. Parameters:
   - `provider`: Use `Provider.GROQ` or `Provider.OPENAI`.
   - `model_type`: Specify the type of models you want to fetch: 'text', 'image', or 'audio'.

3. Example:
   `models = fetch_provider_models(Provider.GROQ, 'text')`

4. Returns:
   - A list of dictionaries containing `id` and `context_window` of the models filtered by the specified type.
"""


# Global config paths
GROQ_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'groq', 'GroqConfig.ini')
OPENAI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'openai', 'OpenAIConfig.ini')

AUDIO_KEYWORDS = ["whisper"]
IMAGE_KEYWORDS = ["llava", "vision"]

class Provider(Enum):
    GROQ = 1
    OPENAI = 2

class ModelFetchStrategy:
    def __init__(self):
        pass

    def fetch_models(self, api_obj, key: str):
        raise NotImplementedError("Subclasses should implement this!")

# Fetch OpenAI models
class FetchByProperty(ModelFetchStrategy):
    def fetch_models(self, api_obj, key: str):
        api_obj.api_key = key
        try:
            models = api_obj.models.list()
        except Exception as e:
            print(f"OpenAI Key is invalid or missing, unable to generate list of models. Error: {e}")
            return None
        return models

# Fetch Groq models
class FetchByMethod(ModelFetchStrategy):
    def fetch_models(self, api_obj, key: str):
        client = api_obj(api_key=key)
        try:
            model_list = client.models.list()
        except Exception as e:
            print(f"Groq Key is invalid or missing, unable to generate list of models. Error: {e}")
            return None
        return model_list

# Define FetchModels class
class FetchModels:
    def __init__(self, strategy, api_obj):
        self.strategy = strategy
        self.api_obj = api_obj

    def fetch_models(self, api_key):
        return self.strategy.fetch_models(self.api_obj, api_key)

# Helper function to load config and key
def load_config(filepath):
    config = configparser.ConfigParser()
    if not os.path.exists(filepath):
        print(f"Configuration file {filepath} does not exist.")
        return None
    config.read(filepath)
    try:
        return config['API']['key']
    except KeyError:
        print(f"Key 'key' not found in {filepath} or invalid key.")
        return None

# Helper function to filter models based on type
def filter_models(models, model_type):
    filtered_models = []
    for model in models:
        model_id = model["id"]
        context_window = model.get("context_window", None)

        if model_type == "audio":
            if any(keyword in model_id.lower() for keyword in AUDIO_KEYWORDS):
                filtered_models.append({"id": model_id, "context_window": context_window})

        elif model_type == "image":
            if any(keyword in model_id.lower() for keyword in IMAGE_KEYWORDS):
                filtered_models.append({"id": model_id, "context_window": context_window})

        elif model_type == "text":
            if not any(keyword in model_id.lower() for keyword in AUDIO_KEYWORDS + IMAGE_KEYWORDS):
                filtered_models.append({"id": model_id, "context_window": context_window})

    return filtered_models

# Fetch models from provider
def fetch_provider_models(provider, model_type):
    api_key = None
    fetcher = None

    if provider == Provider.OPENAI:
        api_key = load_config(OPENAI_CONFIG_PATH)
        fetcher = FetchModels(strategy=FetchByProperty(), api_obj=openai)

    elif provider == Provider.GROQ:
        api_key = load_config(GROQ_CONFIG_PATH)
        fetcher = FetchModels(strategy=FetchByMethod(), api_obj=Groq)

    if not api_key:
        print("API key missing or invalid, cannot proceed.")
        return []

    models = fetcher.fetch_models(api_key=api_key)

    # Filter models by type (audio, image, text)
    return filter_models(models, model_type)
