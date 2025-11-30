import re
import torch
import folder_paths
import comfy.sd
import comfy.utils
import comfy.model_management
import os
from ..utils.file_utils import find_best_match
from .wildcard_processor import WildcardProcessor
from comfy.samplers import SCHEDULER_NAMES  # Official global scheduler list – the correct one


class PromptPropertyExtractor:
    """
    A node to parse a string for sampler and model settings.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {"multiline": True, "default": "", "tooltip": "Input string with property tags.\nSupported tags:\n- <checkpoint:name> | <model:name> | <ckpt:name>\n- <clip:name>\n- <vae:name>\n- <lora:name:weight>\n- <cfg:value>\n- <steps:value> | <step:value>\n- <sampler:name> | <sampler_name:name>\n- <denoise:value>\n- <width:value>\n- <height:value>\n- <resolution:WxH> | <res:WxH> (e.g. 1024x768)\n- <seed:value>\n- <start_step:value> | <start:value> | <start_at_step:value>\n- <end_step:value> | <end:value> | <end_at_step:value>\n- <neg:value> | <negative:value> (Negative Prompt)\n\nNote: Use \\> to include a literal > in tag values (e.g. <neg:(cat:1.5)\\, ugly>)"}),
                "load_clip_from_checkpoint": ("BOOLEAN", {"default": True, "tooltip": "Determines CLIP source priority:\n1. <clip:name> tag (Highest Priority)\n2. Checkpoint CLIP (if <checkpoint> tag exists AND this is True)\n3. Input CLIP pin (Lowest Priority)\n\nIf no <checkpoint> tag is found, this setting is ignored and the Input CLIP is used."}),
                "load_vae_from_checkpoint": ("BOOLEAN", {"default": True, "tooltip": "Determines VAE source priority:\n1. <vae:name> tag (Highest Priority)\n2. Checkpoint VAE (if <checkpoint> tag exists AND this is True)\n3. Input VAE pin (Lowest Priority)\n\nIf no <checkpoint> tag is found, this setting is ignored and the Input VAE is used."}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "tooltip": "Default CFG scale. Can be overridden by a <cfg:value> tag."}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000, "tooltip": "Default number of steps. Can be overridden by a <steps:value> tag."}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"tooltip": "Default sampler. Can be overridden by a <sampler:name> tag."}),
                # REMOVED TEMPORARILY: "scheduler": (SCHEDULER_NAMES, {"tooltip": "Default scheduler. Can be overridden by a <scheduler:name> tag."}),
                # Issue: ComfyUI validates scheduler types at module load time, before custom nodes like PowerShiftScheduler register their schedulers
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Default denoise value. Can be overridden by a <denoise:value> tag."}),
                "width": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 8, "tooltip": "Default image width. Can be overridden by a <width:value> tag."}),
                "height": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 8, "tooltip": "Default image height. Can be overridden by a <height:value> tag."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Default seed. Can be overridden by a <seed:value> tag."}),
                "start_step": ("INT", {"default": 0, "min": 0, "max": 10000, "tooltip": "Default start step for KSampler. Can be overridden by a <start_step:value> tag."}),
                "end_step": ("INT", {"default": 10000, "min": 0, "max": 10000, "tooltip": "Default end step for KSampler. Can be overridden by a <end_step:value> tag."}),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "Default MODEL input (Lowest Priority).\nOverridden by:\n1. <checkpoint:name> tag (Highest Priority)"}),
                "clip": ("CLIP", {"tooltip": "Default CLIP input (Lowest Priority).\nOverridden by:\n1. <clip:name> tag (Highest Priority)\n2. <checkpoint:name> tag CLIP (if load_clip_from_checkpoint is True)"}),
                "vae": ("VAE", {"tooltip": "Default VAE input (Lowest Priority).\nOverridden by:\n1. <vae:name> tag (Highest Priority)\n2. <checkpoint:name> tag VAE (if load_vae_from_checkpoint is True)"}),
            }
        }

    # REMOVED TEMPORARILY: SCHEDULER_NAMES output (was at index 6)
    # Issue: ComfyUI type validation fails when custom nodes register schedulers after this module loads
    # REMOVED TEMPORARILY: SCHEDULER_NAMES output (was at index 6)
    # Issue: ComfyUI type validation fails when custom nodes register schedulers after this module loads
    # REMOVED TEMPORARILY: SCHEDULER_NAMES output (was at index 6)
    # Issue: ComfyUI type validation fails when custom nodes register schedulers after this module loads
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING", "LATENT", "INT", "INT", "FLOAT", comfy.samplers.KSampler.SAMPLERS, "FLOAT", "INT", "INT", "STRING", "STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE", "positive", "negative", "latent", "seed", "steps", "cfg", "sampler", "denoise", "start_step", "end_step", "positive", "negative", "other_tags", "resolved_string", "width", "height")
    OUTPUT_TOOLTIPS = (
        "The final loaded model after applying checkpoint and LoRA tags.",
        "The final loaded CLIP after applying checkpoint and LoRA tags.",
        "The final loaded VAE after applying checkpoint and VAE tags.",
        "The positive conditioning (CLIP encoding of the cleaned string).",
        "The negative conditioning (CLIP encoding of the <neg:value> or <negative:value> tag).",
        "A latent tensor with dimensions based on the selected width and height.",
        "The final seed value. Tag: <seed:value>",
        "The final number of steps. Tags: <steps:value>, <step:value>",
        "The final CFG scale value. Tag: <cfg:value>",
        "The final sampler name. Tags: <sampler:name>, <sampler_name:name>",
        # REMOVED: "The final scheduler name.",
        "The final denoise value. Tag: <denoise:value>",
        "The final start_step for KSampler. Tags: <start_step:value>, <start:value>, <start_at_step:value>",
        "The final end_step for KSampler. Tags: <end_step:value>, <end:value>, <end_at_step:value>",
        "The input string with all recognized property tags removed. Wildcard content is included in this string. (Positive Prompt)",
        "The negative prompt string extracted from <neg:value> or <negative:value> tags.",
        "A string containing any tags that were not recognized by the parser.",
        "The input string with wildcards resolved but ALL tags still present.",
        "The final image width. Tags: <width:value>, <resolution:WxH>, <res:WxH>",
        "The final image height. Tags: <height:value>, <resolution:WxH>, <res:WxH>",
    )
    FUNCTION = "parse_settings"
    CATEGORY = "⚡ MNeMiC Nodes"

    def __init__(self):
        pass

    def parse_settings(self, input_string, load_clip_from_checkpoint, load_vae_from_checkpoint, cfg, steps, sampler_name, denoise, width, height, seed, start_step, end_step, model=None, clip=None, vae=None):
        # Initialize with default values
        out_model, out_clip, out_vae = model, clip, vae
        out_cfg, out_steps, out_sampler, out_denoise = cfg, steps, sampler_name, denoise
        out_scheduler = 'normal'  # Hardcoded default since scheduler input/output is disabled
        out_width, out_height, out_seed, out_start_step, out_end_step = width, height, seed, start_step, end_step
        
        # Initialize wildcard processor to handle wildcard logic
        wildcard_processor = WildcardProcessor()
        wildcard_processor.console_log = False
        other_tags = []
        loras_to_apply = []
        wildcard_processor.console_log = False
        other_tags = []
        loras_to_apply = []
        negative_string = ""
        print(f"\n{'=' * 30} Prompt Property Extractor {'=' * 30}")
        print(f"[INPUT] {repr(input_string)}")
        
        # STEP 1: Process wildcards FIRST (before tag extraction)
        string_with_wildcards_resolved = wildcard_processor.process_wildcards(
            wildcard_string=input_string,
            seed=out_seed,
            multiple_separator=" ",
            recache_wildcards=False,
            tag_extraction_tags=""
        )[0]

        if input_string != string_with_wildcards_resolved:
            print(f"[WILDCARDS RESOLVED] {repr(string_with_wildcards_resolved)}")

        # STEP 2: Find all property tags in the wildcard-resolved string
        # Regex supports escaped \> within tags: <neg:(cat:1.5)\, ugly>
        # Pattern: <(content)> where content can include \> as literal >
        tags_raw = re.findall(r"<((?:[^>\\]|\\.)*)>", string_with_wildcards_resolved)
        
        # Unescape \> to > and \\ to \ in tag content
        tags = []
        for tag_raw in tags_raw:
            tag_unescaped = tag_raw.replace(r'\>', '>').replace(r'\\', '\\')
            tags.append(tag_unescaped)
        
        if tags:
            print(f"[TAGS FOUND] {len(tags)} tags: {tags}")

        # STEP 3: Process each tag
        # Flags to track if CLIP/VAE were set by explicit tags
        clip_set_by_tag = False
        vae_set_by_tag = False
        res_override = None # To store resolution tag values

        # STEP 3: Process each tag
        for tag in tags:
            # Split only on first colon to get tag_name and value
            # This preserves colons in the value
            parts_initial = tag.split(':', 1)
            tag_name = parts_initial[0].lower().strip()
            tag_value = parts_initial[1] if len(parts_initial) > 1 else ""
            
            try:
                if (tag_name == "checkpoint" or tag_name == "model" or tag_name == "ckpt") and tag_value:
                    ckpt_name = tag_value
                    ckpt_filename = find_best_match(ckpt_name, folder_paths.get_filename_list("checkpoints"), log=False)
                    if ckpt_filename:
                        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_filename)
                        if ckpt_path and os.path.exists(ckpt_path):
                            print(f"  [CHECKPOINT] <{tag}> -> {os.path.basename(ckpt_path)}")
                            normalized_ckpt_path = os.path.normpath(os.path.abspath(ckpt_path)).replace('\\', '/')
                            loaded_checkpoint = comfy.sd.load_checkpoint_guess_config(normalized_ckpt_path)
                            out_model = loaded_checkpoint[0]
                            
                            # Only load CLIP from checkpoint if NOT already set by a tag AND enabled
                            if load_clip_from_checkpoint and not clip_set_by_tag:
                                out_clip = loaded_checkpoint[1]
                            elif clip_set_by_tag:
                                print(f"  [INFO] Checkpoint CLIP ignored because <clip> tag was present.")

                            # Only load VAE from checkpoint if NOT already set by a tag AND enabled
                            if load_vae_from_checkpoint and not vae_set_by_tag:
                                out_vae = loaded_checkpoint[2]
                            elif vae_set_by_tag:
                                print(f"  [INFO] Checkpoint VAE ignored because <vae> tag was present.")

                elif tag_name == "clip" and tag_value:
                    clip_name = tag_value.strip()
                    clip_filename = find_best_match(clip_name, folder_paths.get_filename_list("clip"), log=False)
                    if clip_filename:
                        clip_path = folder_paths.get_full_path("clip", clip_filename)
                        if clip_path and os.path.exists(clip_path):
                            print(f"  [CLIP] <{tag}> -> {os.path.basename(clip_path)}")
                            normalized_clip_path = os.path.normpath(os.path.abspath(clip_path)).replace('\\', '/')
                            out_clip = comfy.sd.load_clip(ckpt_paths=[normalized_clip_path])
                            clip_set_by_tag = True

                elif tag_name == "vae" and tag_value:
                    vae_name = tag_value.strip()
                    vae_filename = find_best_match(vae_name, folder_paths.get_filename_list("vae"), log=False)
                    if vae_filename:
                        vae_path = folder_paths.get_full_path("vae", vae_filename)
                        if vae_path and os.path.exists(vae_path):
                            print(f"  [VAE] <{tag}> -> {os.path.basename(vae_path)}")
                            vae_sd = comfy.utils.load_torch_file(vae_path)
                            out_vae = comfy.sd.VAE(sd=vae_sd)
                            vae_set_by_tag = True

                elif tag_name == "cfg" and tag_value:
                    out_cfg = max(1.0, float(tag_value))
                    print(f"  [CFG] <{tag}> -> {out_cfg}")

                elif (tag_name == "sampler" or tag_name == "sampler_name") and tag_value:
                    sampler_match = find_best_match(tag_value.strip(), comfy.samplers.KSampler.SAMPLERS)
                    if sampler_match:
                        out_sampler = sampler_match
                        print(f"  [SAMPLER] <{tag}> -> {out_sampler}")

                elif tag_name == "scheduler" and tag_value:
                    scheduler_match = find_best_match(tag_value.strip(), list(SCHEDULER_NAMES))
                    if scheduler_match:
                        out_scheduler = scheduler_match
                        print(f"  [SCHEDULER] <{tag}> -> {out_scheduler}")

                elif (tag_name == "steps" or tag_name == "step") and tag_value:
                    out_steps = max(1, int(tag_value))
                    print(f"  [STEPS] <{tag}> -> {out_steps}")

                elif tag_name == "denoise" and tag_value:
                    out_denoise = max(0.0, min(1.0, float(tag_value)))
                    print(f"  [DENOISE] <{tag}> -> {out_denoise}")

                elif tag_name == "width" and tag_value:
                    out_width = int(tag_value)
                    print(f"  [WIDTH] <{tag}> -> {out_width}")

                elif tag_name == "height" and tag_value:
                    out_height = int(tag_value)
                    print(f"  [HEIGHT] <{tag}> -> {out_height}")

                elif (tag_name == "resolution" or tag_name == "res") and tag_value:
                    res_string = tag_value.strip()
                    if 'x' in res_string:
                        res_parts = res_string.split('x')
                    elif ':' in res_string:
                        res_parts = res_string.split(':')
                    else:
                        res_parts = []
                    
                    if len(res_parts) == 2:
                        try:
                            r_width = int(res_parts[0].strip())
                            r_height = int(res_parts[1].strip())
                            res_override = (r_width, r_height)
                            print(f"  [RESOLUTION] <{tag}> -> {r_width}x{r_height}")
                        except ValueError:
                            print(f"  [ERROR] Invalid resolution format: {res_string}")

                elif tag_name == "seed" and tag_value:
                    out_seed = int(tag_value)
                    print(f"  [SEED] <{tag}> -> {out_seed}")

                elif (tag_name == "start_step" or tag_name == "start" or tag_name == "start_at_step") and tag_value:
                    out_start_step = int(tag_value)
                    print(f"  [START STEP] <{tag}> -> {out_start_step}")

                elif (tag_name == "end_step" or tag_name == "end" or tag_name == "end_at_step") and tag_value:
                    out_end_step = int(tag_value)
                    print(f"  [END STEP] <{tag}> -> {out_end_step}")

                elif tag_name == "lora" and tag_value:
                    # LoRA needs special handling: name:model_weight:clip_weight
                    # Supported formats:
                    # <lora:name> -> weight 1.0, clip 1.0
                    # <lora:name:weight> -> weight, clip=weight
                    # <lora:name:model_weight:clip_weight>
                    
                    lora_parts = tag_value.split(':')
                    lora_name = lora_parts[0].strip()
                    lora_model_weight = 1.0
                    lora_clip_weight = 1.0
                    
                    if len(lora_parts) > 1 and lora_parts[1]:
                        try:
                            lora_model_weight = float(lora_parts[1].strip())
                            lora_clip_weight = lora_model_weight # Default clip to model weight
                        except ValueError:
                            print(f"  [WARNING] Invalid LoRA weight: {lora_parts[1]}")
                    
                    if len(lora_parts) > 2 and lora_parts[2]:
                        try:
                            lora_clip_weight = float(lora_parts[2].strip())
                        except ValueError:
                            print(f"  [WARNING] Invalid LoRA CLIP weight: {lora_parts[2]}")

                    lora_filename = find_best_match(lora_name, folder_paths.get_filename_list("loras"), log=False)
                    if lora_filename:
                        lora_path = folder_paths.get_full_path("loras", lora_filename)
                        if lora_path and os.path.exists(lora_path):
                            print(f"  [LORA QUEUED] <{tag}> -> {os.path.basename(lora_path)} (Model: {lora_model_weight}, CLIP: {lora_clip_weight})")
                            loras_to_apply.append((lora_path, lora_model_weight, lora_clip_weight))

                elif (tag_name == "neg" or tag_name == "negative") and tag_value:
                    negative_string = tag_value.strip()
                    print(f"  [NEG] <{tag}> -> {negative_string}")

                elif tag_name not in ["checkpoint", "model", "ckpt", "clip", "vae", "cfg", "sampler", "sampler_name", "scheduler", "steps", "step", "denoise", "width", "height", "resolution", "res", "seed", "start_step", "start", "start_at_step", "end_step", "end", "end_at_step", "lora", "neg", "negative"]:
                    other_tags.append(f"<{tag}>")

            except (ValueError, IndexError) as e:
                print(f"  [ERROR] Error parsing tag '{tag}': {e}")

        # Apply resolution override if present
        if res_override:
            out_width, out_height = res_override
            print(f"  [INFO] Resolution tag override applied: {out_width}x{out_height}")

        # STEP 4: Create the cleaned_string by removing all property tags
        cleaned_string_final = string_with_wildcards_resolved
        for tag in tags:
            cleaned_string_final = cleaned_string_final.replace(f"<{tag}>", "")

        # STEP 5: Apply LoRAs
        if loras_to_apply and out_model and out_clip:
            for lora_path, lora_model_weight, lora_clip_weight in loras_to_apply:
                try:
                    lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                    print(f"  [LORA APPLIED] {os.path.basename(lora_path)} (Model: {lora_model_weight}, CLIP: {lora_clip_weight})")
                    out_model, out_clip = comfy.sd.load_lora_for_models(out_model, out_clip, lora, lora_model_weight, lora_clip_weight)
                except Exception as e:
                    print(f"  [ERROR] Failed to load LoRA {lora_path}: {e}")

        # Final cleaning of the string (collapse multiple spaces)
        cleaned_string = re.sub(r"\s+", " ", cleaned_string_final).strip()
        
        # Join other tags
        other_tags_str = "".join(other_tags)
        if other_tags_str:
            print(f"[UNRECOGNIZED TAGS] {other_tags_str}")
        print(f"[OUTPUT] {repr(cleaned_string)}")
        
        # Encode conditioning
        pos_conditioning = None
        neg_conditioning = None
        
        if out_clip:
            # Positive
            tokens = out_clip.tokenize(cleaned_string)
            cond, pooled = out_clip.encode_from_tokens(tokens, return_pooled=True)
            pos_conditioning = [[cond, {"pooled_output": pooled}]]
            
            # Negative
            tokens_neg = out_clip.tokenize(negative_string)
            cond_neg, pooled_neg = out_clip.encode_from_tokens(tokens_neg, return_pooled=True)
            neg_conditioning = [[cond_neg, {"pooled_output": pooled_neg}]]
        else:
            print("[WARNING] No CLIP model available for encoding conditioning.")

        # Create latent tensor
        try:
            device = comfy.model_management.intermediate_device()
            # Latent space is 8x smaller than pixel space
            # Default batch size is 1 as we don't have a batch inputs
            latent_tensor = torch.zeros([1, 4, out_height // 8, out_width // 8], device=device)
            out_latent = {"samples": latent_tensor}
        except Exception as e:
            print(f"[ERROR] Failed to create latent tensor: {e}")
            out_latent = None

        print(f"{'=' * 30} Prompt Property Extractor End {'=' * 30}\n")

        # REMOVED SCHEDULER OUTPUT: was (out_model, out_clip, out_vae, out_cfg, out_steps, out_sampler, out_scheduler, out_denoise, ...)
        # REMOVED SCHEDULER OUTPUT: was (out_model, out_clip, out_vae, out_cfg, out_steps, out_sampler, out_scheduler, out_denoise, ...)
        return (out_model, out_clip, out_vae, pos_conditioning, neg_conditioning, out_latent, out_seed, out_steps, out_cfg, out_sampler, out_denoise, out_start_step, out_end_step, cleaned_string, negative_string, other_tags_str, string_with_wildcards_resolved, out_width, out_height)


NODE_CLASS_MAPPINGS = {
    "PromptPropertyExtractor": PromptPropertyExtractor
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptPropertyExtractor": "Prompt Property Extractor"
}