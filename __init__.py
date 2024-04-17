from .nodes.nodes import *

NODE_CLASS_MAPPINGS = { 
    "💾 Save Text File With Path": SaveTextFile,
    "🖼️ Download Image from URL": FetchAndSaveImage,
    "✨ Groq LLM API": GroqAPICompletion,
    "⛔ Generate Negative Prompt": GenerateNegativePrompt,
    }
    
print("\033[34mMNeMiC Nodes: \033[92mLoaded\033[0m")
