"""
Source reference:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
Adapted into ComfyUI-mnemic-nodes for the "Image Save With Metadata" node.
"""

import re
from typing import Dict, List, Tuple

from .image_save_with_metadata_civitai import civitai_embedding_key_name, civitai_lora_key_name
from .image_save_with_metadata_utils import full_embedding_path_for, full_lora_path_for

escape_important = None
unescape_important = None
token_weights = None

for _module_path in ("comfy.sd1_clip", "comfy.text_encoders.sd1_clip"):
    try:
        import importlib
        _mod = importlib.import_module(_module_path)
        escape_important = getattr(_mod, "escape_important", None)
        unescape_important = getattr(_mod, "unescape_important", None)
        token_weights = getattr(_mod, "token_weights", None)
        if escape_important is not None:
            break
    except (ImportError, ModuleNotFoundError):
        continue

if escape_important is None:
    print("[Image Save With Metadata] Warning: Could not import clip tokenizer functions. Using basic embedding/lora extraction.")

    def escape_important(text):
        return text

    def unescape_important(text):
        return text

    def token_weights(text, default_weight):
        return [(text, default_weight)]


class PromptMetadataExtractor:
    EMBEDDING: str = r"embedding:([^,\s\(\)\:]+)"
    LORA: str = r"<lora:([^>:]+)(?::([^>]+))?>"

    def __init__(self, prompts: List[str]) -> None:
        self.__embeddings: Dict[str, Tuple[str, float]] = {}
        self.__loras: Dict[str, Tuple[str, float]] = {}
        self.__perform(prompts)

    def get_embeddings(self) -> Dict[str, Tuple[str, float]]:
        return self.__embeddings

    def get_loras(self) -> Dict[str, Tuple[str, float]]:
        return self.__loras

    def __perform(self, prompts: List[str]) -> None:
        for prompt in prompts:
            parsed = ((unescape_important(value), weight) for value, weight in token_weights(escape_important(prompt), 1.0))
            for text, weight in parsed:
                embeddings = re.findall(self.EMBEDDING, text, re.IGNORECASE | re.MULTILINE)
                for embedding in embeddings:
                    self.__extract_embedding_information(embedding, weight)
            loras = re.findall(self.LORA, prompt, re.IGNORECASE | re.MULTILINE)
            for lora in loras:
                self.__extract_lora_information(lora)

    def __extract_embedding_information(self, embedding: str, weight: float) -> None:
        embedding_name = civitai_embedding_key_name(embedding)
        embedding_path = full_embedding_path_for(embedding)
        if embedding_path is None:
            return
        self.__embeddings[embedding_name] = (embedding_path, weight)

    def __extract_lora_information(self, lora: Tuple[str, str]) -> None:
        lora_name = civitai_lora_key_name(lora[0])
        lora_path = full_lora_path_for(lora[0])
        if lora_path is None:
            return
        try:
            lora_weight = float(lora[1].split(":")[0])
        except (ValueError, TypeError):
            lora_weight = 1.0
        self.__loras[lora_name] = (lora_path, lora_weight)
