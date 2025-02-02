from pathlib import Path
import folder_paths
import re

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

    def score_filename_match(self, name, filename):
        """Score how well a filename matches the requested name."""
        base_name = Path(filename).name
        base_name_no_ext = Path(filename).stem  # filename without extension
        name_no_ext = Path(name).stem  # search term without extension
        
        # Calculate path depth score
        path_depth = len(Path(filename).parts) - 1
        path_penalty = path_depth * 0.0001
        
        # If searching for a numbered variant, also match the base name
        base_search_name = re.sub(r'\d+$', '', name_no_ext).rstrip('-')
        
        # Exact match gets highest priority (100)
        if base_name_no_ext == name_no_ext:
            return (100 - path_penalty, f"exact match (depth: {path_depth})")
        # Base version match when searching for numbered variant (90)
        elif base_name_no_ext == base_search_name:
            return (90 - path_penalty, f"base version match (depth: {path_depth})")
        
        # Check if it's a numbered variant of the exact name (80)
        if base_name.startswith(name + "-"):
            try:
                num = int(re.findall(r'-(\d+)', base_name)[0])
                return (80 + (num * 0.001) - path_penalty, f"numbered variant ({num}, depth: {path_depth})")
            except (IndexError, ValueError):
                pass
        
        # Check if we're looking for a specific number
        number_search = re.search(r'(\d+)$', name)
        if number_search:
            base_without_number = name[:-len(number_search.group(1))]
            target_number = int(number_search.group(1))
            if base_name.startswith(base_without_number):
                try:
                    file_number = int(re.findall(r'-(\d+)', base_name)[0])
                    number_diff = abs(target_number - file_number)
                    if number_diff == 0:
                        return (95 - path_penalty, f"exact number match ({target_number}, depth: {path_depth})")
                    return (85 - (number_diff * 0.1) - path_penalty, f"number near match ({file_number}, depth: {path_depth})")
                except (IndexError, ValueError):
                    pass
        
        # Simple startswith match (lowest priority)
        if base_name.startswith(name) or filename.startswith(name):
            return (50 - path_penalty, f"prefix match (depth: {path_depth})")
        
        return (0, "no match")

    def find_best_lora_match(self, name, lora_files):
        """Find the best matching LoRA file based on scoring."""
        matches = []
        print(f"\nFinding matches for '{name}':")
        
        # Track filenames to detect duplicates
        seen_filenames = {}
        
        for lora_file in lora_files:
            score, reason = self.score_filename_match(name, lora_file)
            if score > 0:
                base_name = Path(lora_file).name
                if base_name in seen_filenames:
                    # Convert to showing full paths for this filename
                    seen_filenames[base_name] = True
                else:
                    seen_filenames[base_name] = False
                matches.append((score, lora_file, reason))
        
        # Sort by score (highest first)
        matches.sort(reverse=True)
        
        # Print all matches with their scores
        if matches:
            print("\nCandidate files (sorted by relevance):")
            for score, file, reason in matches:
                base_name = Path(file).name
                if seen_filenames[base_name]:
                    # Show full path for duplicates
                    display_name = file
                else:
                    display_name = base_name
                print(f"  {display_name:<50} : {score:>5.1f} ({reason})")
            print(f"\nSelected: {matches[0][1]}")
        else:
            print("  No matching files found")
        
        return matches[0][1] if matches else None

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
            lora_name = self.find_best_lora_match(name, lora_files)
            
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