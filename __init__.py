from .nodes.fetch_and_save_image import FetchAndSaveImage
from .nodes.generate_negative_prompt import GenerateNegativePrompt
from .nodes.groq_api_completion import GroqAPICompletion
from .nodes.save_text_file import SaveTextFile

NODE_CLASS_MAPPINGS = { 
    "💾 Save Text File With Path": SaveTextFile,
    "🖼️ Download Image from URL": FetchAndSaveImage,
    "✨ Groq LLM API": GroqAPICompletion,
    "⛔ Generate Negative Prompt": GenerateNegativePrompt,
}

print("\033[34mMNeMiC Nodes: \033[92mLoaded\033[0m")
