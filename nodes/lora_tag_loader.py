from pathlib import Path
import folder_paths
import re
from ..utils.file_utils import find_best_match

# Import ComfyUI files
import comfy.sd
import comfy.utils

class LoraTagLoader:
    """
    LoraTagLoader is responsible for loading Lora tags from the provided text.
    It uses a regex pattern to identify specific tags within the text.
    Original version: https://github.com/badjeff/comfyui_lora_tag_loader
    This version also includes a new matching system to find the "best" matching LoRA file based on scoring.
    """

    def __init__(self):
        # Initialize the loader with no Lora model loaded
        self.loaded_lora = None

        # Regular expression pattern to match tags enclosed in angle brackets
        self.tag_pattern = r"\<[0-9a-zA-Z:\_\-\.\s/()\\]+\>"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "MODEL": ("MODEL", {"tooltip": "The model (checkpoint) to apply the LoRA to"}),
                "CLIP": ("CLIP", {"tooltip": "The CLIP model being used"}),
                "STRING": ("STRING", {"multiline": True, "forceInput": True, "tooltip": "Input text containing LoRA tags to be processed. Tags should be enclosed in angle brackets, e.g., <lora:loraName:1>"}),
            }
        }

    # Defines the types of values this class will return
    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "STRING")  # Human-readable names for the return values
    OUTPUT_TOOLTIPS = ("The model output after the LoRA was loaded", "The CLIP output after the LoRA was loaded", "The input text cleaned up with the LoRA tags removed")
    FUNCTION = "load_lora"  # Name of the method that processes the inputs

    CATEGORY = "⚡ MNeMiC Nodes"  # Category for organizing the node in a UI or library
    DESCRIPTION = "Loads LoRA tags from the provided input string (usually the prompt) and applies them to the model without needing one or multiple LoRA Loader nodes"


    def load_lora(self, MODEL, CLIP, STRING):
        print(f"\nLoraTagLoader processing text: {STRING}")

        founds = re.findall(self.tag_pattern, STRING)
        if len(founds) < 1:
            return (MODEL, CLIP, STRING)

        model_lora = MODEL
        clip_lora = CLIP
        
        lora_files = folder_paths.get_filename_list("loras")
        for f in founds:
            tag = f[1:-1]
            pak = tag.split(":")
            type = pak[0]
            if type != 'lora':
                continue
            
            # Parse the tag components
            if len(pak) <= 1 or not pak[1]:
                continue
            name = pak[1]
            
            # Parse weights
            wModel = wClip = 0
            try:
                if len(pak) > 2 and pak[2]:
                    wModel = float(pak[2])
                    wClip = wModel
                if len(pak) > 3 and pak[3]:
                    wClip = float(pak[3])
            except ValueError:
                continue

            # Use our new matching system
            lora_name = find_best_match(name, lora_files, log=True)
            
            if lora_name is None:
                print(f"No matching LoRA found for tag: {(type, name, wModel, wClip)}")
                continue
            
            print(f"\nApplying LoRA: {(type, name, wModel, wClip)} >> {lora_name}")
            
            # Load and apply the LoRA
            lora_path = folder_paths.get_full_path("loras", lora_name)
            lora = None
            
            # Check if we already have this LoRA loaded
            if self.loaded_lora is not None:
                if self.loaded_lora[0] == lora_path:
                    lora = self.loaded_lora[1]
                else:
                    temp = self.loaded_lora
                    self.loaded_lora = None
                    del temp

            # Load the LoRA if needed
            if lora is None:
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                self.loaded_lora = (lora_path, lora)

            # Apply the LoRA
            model_lora, clip_lora = comfy.sd.load_lora_for_models(model_lora, clip_lora, lora, wModel, wClip)

        # Remove the LoRA tags from the text
        plain_prompt = re.sub(self.tag_pattern, "", STRING)
        return (model_lora, clip_lora, plain_prompt)

NODE_CLASS_MAPPINGS = {
    "LoraTagLoader": LoraTagLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # Loaders
    "LoraTagLoader": "Load LoRA Tag",
}