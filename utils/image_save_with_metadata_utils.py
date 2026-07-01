"""
Source reference:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
Adapted into ComfyUI-mnemic-nodes for the "Image Save With Metadata" node.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional
from collections.abc import Collection, Iterator

import folder_paths
import requests


def sanitize_filename(filename: str) -> str:
    unsafe_chars = r'[<>:"|?*\x00-\x1f]'
    sanitized = re.sub(unsafe_chars, "", filename)
    sanitized = sanitized.rstrip(". ")
    return sanitized


def full_embedding_path_for(embedding: str) -> Optional[str]:
    matching_embedding = get_file_path_match("embeddings", embedding)
    if matching_embedding is None:
        print(f'ComfyUI-Image-Saver: could not find full path to embedding "{embedding}"')
        return None
    return folder_paths.get_full_path("embeddings", matching_embedding)


def full_lora_path_for(lora: str) -> Optional[str]:
    matching_lora = get_file_path_match("loras", lora)
    if matching_lora is None:
        print(f'ComfyUI-Image-Saver: could not find full path to lora "{lora}"')
        return None
    return folder_paths.get_full_path("loras", matching_lora)


def full_checkpoint_path_for(model_name: str) -> str:
    if not model_name:
        return ""

    supported_extensions = set(folder_paths.supported_pt_extensions) | {".gguf"}

    matching_checkpoint = get_file_path_match("checkpoints", model_name, supported_extensions)
    if matching_checkpoint is not None:
        return folder_paths.get_full_path("checkpoints", matching_checkpoint)

    matching_model = get_file_path_match("diffusion_models", model_name, supported_extensions)
    if matching_model:
        return folder_paths.get_full_path("diffusion_models", matching_model)

    print(f'Could not find full path to checkpoint "{model_name}"')
    return ""


def get_file_path_iterator(folder_name: str, supported_extensions: Optional[Collection[str]] = None) -> Iterator[Path]:
    if supported_extensions is None:
        return (Path(x) for x in folder_paths.get_filename_list(folder_name))
    return custom_file_path_generator(folder_name, supported_extensions)


def custom_file_path_generator(folder_name: str, supported_extensions: Collection[str]) -> Iterator[Path]:
    model_paths = folder_paths.folder_names_and_paths.get(folder_name, [[], set()])[0]
    for path in model_paths:
        if os.path.exists(path):
            base_path = Path(path)
            for root, _, files in os.walk(path):
                root_path = Path(root).relative_to(base_path)
                for file in files:
                    file_path = root_path / file
                    if file_path.suffix.lower() in supported_extensions:
                        yield file_path


def get_file_path_match(
    folder_name: str,
    file_name: str,
    supported_extensions: Optional[Collection[str]] = None,
) -> Optional[str]:
    supported_extensions_fallback = (
        supported_extensions if supported_extensions is not None else folder_paths.supported_pt_extensions
    )
    file_path = Path(file_name)

    if file_path.suffix.lower() not in supported_extensions_fallback:
        matching_file_path = next(
            (p for p in get_file_path_iterator(folder_name, supported_extensions) if p.with_suffix("") == file_path),
            None,
        )
        matching_file_path = (
            matching_file_path
            if matching_file_path is not None
            else next(
                (p for p in get_file_path_iterator(folder_name, supported_extensions) if p.stem == file_path.name),
                None,
            )
        )
    else:
        matching_file_path = next(
            (p for p in get_file_path_iterator(folder_name, supported_extensions) if p == file_path),
            None,
        )
        matching_file_path = (
            matching_file_path
            if matching_file_path is not None
            else next(
                (p for p in get_file_path_iterator(folder_name, supported_extensions) if p.name == file_path.name),
                None,
            )
        )

    return str(matching_file_path) if matching_file_path is not None else None


def http_get_json(url: str) -> dict[str, Any] | None:
    try:
        response = requests.get(url, timeout=300)
    except requests.exceptions.Timeout:
        print(f"ComfyUI-Image-Saver: HTTP GET Request timed out for {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"ComfyUI-Image-Saver: Warning - Network connection error for {url}: {e}")
        return None

    if not response.ok:
        print(f"ComfyUI-Image-Saver: HTTP GET Request failed with error code: {response.status_code}: {response.reason}")
        return None

    try:
        return response.json()
    except ValueError as e:
        print(f"ComfyUI-Image-Saver: HTTP Response JSON error: {e}")
    return None
