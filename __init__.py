from .nodes.nodes import *

NODE_CLASS_MAPPINGS = { 
    "Save Text File_mne": SaveTextFile,
    "Generate Negative Prompt_mne": GenerateNegativePrompt,
    }
    
print("\033[34mMNeMiC Nodes: \033[92mLoaded\033[0m")
