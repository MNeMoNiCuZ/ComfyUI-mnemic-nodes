"""Prompt presets shared between the Groq nodes and the Universal LLM node.

Presets live in `nodes/groq/` as lists of `{"name": ..., "content": ...}`:
`Default*.json` ship with the pack, `User*.json` are yours. Both nodes read the
same files, so a preset added once shows up in every LLM node.
"""

import os

from .api_utils import load_prompt_options

PRESET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "nodes", "groq")

TEXT_PRESET_FILES = ["DefaultPrompts.json", "UserPrompts.json"]
VISION_PRESET_FILES = ["DefaultPrompts_VLM.json", "UserPrompts_VLM.json"]


def load_presets(file_names):
    """Return {name: content} for the given preset files, in file order."""
    return load_prompt_options([os.path.join(PRESET_DIR, name) for name in file_names])


def load_llm_presets():
    """Text presets followed by vision presets, as used by the Universal LLM node."""
    presets = load_presets(TEXT_PRESET_FILES)
    for name, content in load_presets(VISION_PRESET_FILES).items():
        presets.setdefault(name, content)
    return presets
