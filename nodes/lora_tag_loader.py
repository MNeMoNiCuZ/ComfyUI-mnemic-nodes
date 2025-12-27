from pathlib import Path
import folder_paths
import re
from ..utils.file_utils import find_best_match

# Import ComfyUI files
import comfy.sd
import comfy.utils
import comfy.model_base
import comfy.lora

def z_image_to_diffusers(mmdit_config, output_prefix=""):
    n_layers = mmdit_config.get("n_layers", 0)
    hidden_size = mmdit_config.get("dim", 0)
    key_map = {}
    for index in range(n_layers):
        prefix_from = "layers.{}".format(index)
        prefix_to = "{}layers.{}".format(output_prefix, index)
        for end in ("weight", "bias"):
            k = "{}.attention.".format(prefix_from)
            qkv = "{}.attention.qkv.{}".format(prefix_to, end)
            key_map["{}to_q.{}".format(k, end)] = (qkv, (0, 0, hidden_size))
            key_map["{}to_k.{}".format(k, end)] = (qkv, (0, hidden_size, hidden_size))
            key_map["{}to_v.{}".format(k, end)] = (qkv, (0, hidden_size * 2, hidden_size))
        block_map = {
            "attention.norm_q.weight": "attention.q_norm.weight",
            "attention.norm_k.weight": "attention.k_norm.weight",
            "attention.to_out.0.weight": "attention.out.weight",
            "attention.to_out.0.bias": "attention.out.bias",
        }
        for k in block_map:
            key_map["{}.{}".format(prefix_from, k)] = "{}.{}".format(prefix_to, block_map[k])
    MAP_BASIC = {
        # Final layer
        ("final_layer.linear.weight", "all_final_layer.2-1.linear.weight"),
        ("final_layer.linear.bias", "all_final_layer.2-1.linear.bias"),
        ("final_layer.adaLN_modulation.1.weight", "all_final_layer.2-1.adaLN_modulation.1.weight"),
        ("final_layer.adaLN_modulation.1.bias", "all_final_layer.2-1.adaLN_modulation.1.bias"),
        # X embedder
        ("x_embedder.weight", "all_x_embedder.2-1.weight"),
        ("x_embedder.bias", "all_x_embedder.2-1.bias"),
    }
    for k in MAP_BASIC:
        key_map[k[1]] = "{}{}".format(output_prefix, k[0])
    return key_map

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
            wModel = 1.0
            wClip = 1.0

            if len(pak) > 2 and pak[2]:
                try:
                    strength = float(pak[2])
                    wModel = strength if strength != 0 else 1.0
                except ValueError:
                    print(f"LoraTagLoader Warning: Invalid model strength value '{pak[2]}' for LoRA '{pak[1]}'. Defaulting to 1.0.")
                    wModel = 1.0
            
            wClip = wModel # default clip to model weight

            if len(pak) > 3 and pak[3]:
                try:
                    clip_strength = float(pak[3])
                    wClip = clip_strength if clip_strength != 0 else 1.0
                except ValueError:
                    print(f"LoraTagLoader Warning: Invalid clip strength value '{pak[3]}' for LoRA '{pak[1]}'. Defaulting to model weight ({wClip}).")
                    # wClip is already set to wModel, so no change needed here, just the warning.

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
            is_zit = False
            if hasattr(comfy.model_base, "Lumina2"):
                if isinstance(model_lora.model, comfy.model_base.Lumina2):
                    is_zit = True

            if is_zit:
                print(f"LoraTagLoader: ZiT model detected, applying custom key mapping via monkeypatch.")
                # Monkeypatch approach: temporarily modify model_lora_keys_unet to include ZiT support
                # This replicates the logic from the ComfyUI commit
                original_model_lora_keys_unet = comfy.lora.model_lora_keys_unet
                
                def patched_model_lora_keys_unet(model, key_map={}):
                    # Call the original function first
                    key_map = original_model_lora_keys_unet(model, key_map)
                    
                    # Add ZiT-specific mappings if it's a Lumina2 model
                    if isinstance(model, comfy.model_base.Lumina2):
                        diffusers_keys = z_image_to_diffusers(model.model_config.unet_config, output_prefix="diffusion_model.")
                        for k in diffusers_keys:
                            to = diffusers_keys[k]
                            key_lora = k[:-len(".weight")]
                            key_map["diffusion_model.{}".format(key_lora)] = to
                            key_map["lycoris_{}".format(key_lora.replace(".", "_"))] = to
                    
                    return key_map
                
                # Temporarily replace the function
                comfy.lora.model_lora_keys_unet = patched_model_lora_keys_unet
                
                try:
                    # Use the standard loading path, which will now use our patched function
                    model_lora, clip_lora = comfy.sd.load_lora_for_models(model_lora, clip_lora, lora, wModel, wClip)
                finally:
                    # Always restore the original function
                    comfy.lora.model_lora_keys_unet = original_model_lora_keys_unet
            else:
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