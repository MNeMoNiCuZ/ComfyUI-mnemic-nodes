import folder_paths
import logging
import re

from comfy_api.latest import io

from ..utils.file_utils import find_best_match
from ..utils.settings_utils import is_lora_console_log_enabled, is_lora_fuzzy_search_enabled, get_lora_max_logged_candidates

# Import ComfyUI files
import comfy.sd
import comfy.utils
import comfy.model_base
import comfy.lora
import comfy.lora_convert
import comfy.hooks
import comfy.patcher_extension

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

# Cache of the most recently loaded LoRA, kept at module level because V3 nodes
# execute as classmethods on a per-run class clone and cannot hold instance state.
_LOADED_LORA = None

# Regular expression pattern to match tags enclosed in angle brackets
TAG_PATTERN = r"\<[0-9a-zA-Z:=,\_\-\.\s/()\\]+\>"


def _parse_schedule(parts, name):
    """Separate named step limits from the existing positional strengths."""
    positional = []
    limits = {}
    for part in parts:
        if "=" not in part:
            positional.append(part)
            continue
        key, value = (item.strip() for item in part.split("=", 1))
        if key not in ("start", "end", "range") or key in limits:
            raise ValueError(f"LoRA '{name}': unknown or repeated option '{key}'.")
        limits[key] = value
    if "range" in limits:
        if "start" in limits or "end" in limits:
            logging.warning("LoraTagLoader: LoRA '%s': range= takes priority; ignoring start= and end= options.", name)
        ranges = []
        for item in limits["range"].split(","):
            match = re.fullmatch(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?", item)
            if match is None:
                raise ValueError(f"LoRA '{name}': range must contain steps or inclusive ranges, e.g. range=2-4,8-10.")
            start = int(match[1])
            end = int(match[2]) if match[2] is not None else start
            if start < 1 or end < start:
                raise ValueError(f"LoRA '{name}': ranges must use positive steps with end >= start.")
            ranges.append((start, end))
        # Normalize overlaps and adjacent ranges so neither order nor duplicate
        # entries cause extra on/off transitions or stack the LoRA strength.
        merged = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return positional, tuple(merged), True

    # Validate only the selected scheduling form. Ignored start/end values
    # cannot prevent a valid range from running, regardless of option order.
    for key, value in limits.items():
        if not value.isascii() or not value.isdecimal() or int(value) < 1:
            raise ValueError(f"LoRA '{name}': {key} must be a positive integer sampling step.")
        limits[key] = int(value)
    start = limits.get("start", 1)
    end = limits.get("end")
    if end is not None and end < start:
        raise ValueError(f"LoRA '{name}': end must be greater than or equal to start.")
    return positional, ((start, end),), bool(limits)


class _StepKeyframes(comfy.hooks.HookKeyframeGroup):
    """Resolve step bounds against this sampling pass's actual noise schedule."""
    def __init__(self, sigma_ranges):
        super().__init__()
        self.sigma_ranges = sigma_ranges
        self.reset()

    @property
    def strength(self):
        return self._current_strength

    def reset(self):
        self._current_strength = 0.0

    def initialize_timesteps(self, model):
        self.reset()

    def prepare_current_keyframe(self, curr_t, transformer_options):
        strength = float(any(lower < curr_t <= upper for upper, lower in self.sigma_ranges))
        changed = strength != self._current_strength
        self._current_strength = strength
        return changed

    def clone(self):
        return _StepKeyframes(self.sigma_ranges)


class _ScheduledLora:
    def __init__(self, hook, ranges):
        self.hook = hook
        self.ranges = ranges

    def __call__(self, executor, noise, latent_image, sampler, sigmas,
                 denoise_mask=None, callback=None, disable_pbar=False, seed=None, **kwargs):
        guider = executor.class_obj
        step_count = len(sigmas) - 1
        # A start past the available steps never activates. An omitted end or
        # an end past the available steps stays active through final denoising.
        sigma_ranges = []
        for start, end in self.ranges:
            if start > step_count:
                continue
            upper_sigma = float("inf") if start == 1 else float(sigmas[start - 1])
            lower_sigma = float(sigmas[end]) if end is not None and end < step_count else -float("inf")
            sigma_ranges.append((upper_sigma, lower_sigma))
        hook = self.hook.clone()
        hook.hook_keyframe = _StepKeyframes(tuple(sigma_ranges))
        scheduled = comfy.hooks.HookGroup()
        scheduled.add(hook)

        # OUTER_SAMPLE runs after ordinary conditioning hooks are registered.
        # Our weights are already registered on the output model; add the fresh
        # per-run hook to every conditioning group without replacing their hooks.
        registered = guider.model_options.get("registered_hooks")
        registered = registered.clone() if registered is not None else comfy.hooks.HookGroup()
        registered.add(hook)
        guider.model_options["registered_hooks"] = registered
        original_conds = guider.conds
        # HookGroup identity controls both CFG batching and ComfyUI's
        # already-applied weight check. Reuse one combined group for conditions
        # with the same existing hooks; separate clones here repatch hundreds of
        # weights whenever sampling switches between positive and negative.
        combined_groups = {None: scheduled}

        def with_scheduled_hook(cond):
            existing = cond.get("hooks")
            if existing not in combined_groups:
                combined_groups[existing] = scheduled.clone_and_combine(existing)
            return dict(cond, hooks=combined_groups[existing])

        guider.conds = {
            key: [with_scheduled_hook(cond) for cond in conds]
            for key, conds in original_conds.items()
        }

        try:
            return executor(noise, latent_image, sampler, sigmas, denoise_mask,
                            callback, disable_pbar, seed, **kwargs)
        finally:
            guider.conds = original_conds


def _apply_lora(model, clip, lora, model_strength, clip_strength, ranges, scheduled, time_options=None):
    if not scheduled and time_options is None:
        return comfy.sd.load_lora_for_models(model, clip, lora, model_strength, clip_strength)
    if time_options is not None and model_strength == 0.0:
        if clip is not None and clip_strength != 0.0:
            _, clip = comfy.sd.load_lora_for_models(None, clip, lora, 0.0, clip_strength)
        return model, clip

    model = model.clone()
    if time_options is not None:
        from ..utils.lora_time_h3 import add_h3_timed_lora
        key_map = comfy.lora.model_lora_keys_unet(model.model, {})
        patches = comfy.lora.load_lora(comfy.lora_convert.convert_lora(lora), key_map)
        if add_h3_timed_lora(model, patches, model_strength, ranges if scheduled else None, time_options):
            if clip is not None and clip_strength != 0.0:
                _, clip = comfy.sd.load_lora_for_models(None, clip, lora, 0.0, clip_strength)
            return model, clip
    # Native weight hooks require the non-dynamic patcher (as CFGGuider does
    # when hooks arrive through conditioning). Do this before registering weights.
    if model.is_dynamic():
        model = model.get_non_dynamic_delegate()
    from ..utils.lora_hooks import enable_quantized_hooks
    enable_quantized_hooks(model)
    # Dynamic loading enables casting on every Comfy operation. The regular
    # hook-compatible patcher must do the same: mixed-dtype checkpoints such as
    # Anima can have FP16 adapter norms alongside BF16 linear weights, including
    # in text preprocessing before the first scheduled hook is applied.
    # Let ComfyUI cast per operation rather than changing checkpoint storage or
    # the model's chosen inference dtype. add_hook_patches below invalidates the
    # patch UUID so an already-loaded clone is reloaded with this flag.
    model.force_cast_weights = True
    key_map = comfy.lora.model_lora_keys_unet(model.model, {})
    patches = comfy.lora.load_lora(comfy.lora_convert.convert_lora(lora), key_map)
    hook = comfy.hooks.WeightHook(strength_model=model_strength, strength_clip=0.0)
    hook.weights = patches
    hook.need_weight_init = False
    model.add_hook_patches(hook, patches, strength_patch=model_strength)
    if time_options is not None:
        from ..utils.lora_time import add_timed_lora
        add_timed_lora(model, hook, ranges if scheduled else None, time_options)
    else:
        model.add_wrapper_with_key(
            comfy.patcher_extension.WrappersMP.OUTER_SAMPLE,
            "mnemic_scheduled_lora", _ScheduledLora(hook, ranges),
        )
    if clip is not None and clip_strength != 0.0:
        _, clip = comfy.sd.load_lora_for_models(None, clip, lora, 0.0, clip_strength)
    return model, clip


def parse_lora_tag(tag_text, has_clip, lora_files, console_log):
    """
    Parse one angle-bracket tag into (lora_name, model_strength, clip_strength,
    ranges, scheduled, time_options). Returns None for non-LoRA tags, disabled
    tags, and tags that match no LoRA file.
    """
    tag = tag_text[1:-1]
    pak = tag.split(":")
    type = pak[0]
    if type != 'lora':
        return None

    # Parse the tag components
    if len(pak) <= 1 or not pak[1]:
        return None
    name = pak[1]
    parts = pak[2:]
    time_options = None
    if any(part.split("=", 1)[0].strip() in ("time", "fps", "blend") for part in parts):
        # No temporal imports, wrappers, masks, or extra predictions for
        # existing constant/step-only tags.
        from ..utils.lora_time import parse_time_options
        parts, time_options = parse_time_options(parts, name)
    weights, ranges, scheduled = _parse_schedule(parts, name)
    pak = pak[:2] + weights

    # Parse weights
    wModel = 1.0
    wClip = 1.0

    if len(pak) > 2 and pak[2]:
        try:
            wModel = float(pak[2])
        except ValueError:
            if console_log:
                print(f"LoraTagLoader Warning: Invalid model strength value '{pak[2]}' for LoRA '{pak[1]}'. Defaulting to 1.0.")
            wModel = 1.0

    # Timed CLIP changes would bake the LoRA into the whole prompt.
    wClip = 0.0 if time_options is not None else wModel

    if len(pak) > 3 and pak[3]:
        try:
            wClip = float(pak[3])
        except ValueError:
            if console_log:
                print(f"LoraTagLoader Warning: Invalid clip strength value '{pak[3]}' for LoRA '{pak[1]}'. Keeping default CLIP strength ({wClip}).")
            # Keep the tag's default: model strength, or zero for time=.

    if time_options is not None and time_options.get("blend") is not None:
        if len(pak) > 2 and pak[2]:
            logging.warning("LoraTagLoader: LoRA '%s': blend= takes priority; ignoring positional model strength.", name)
        wModel = 1.0 if any(value != 0 for value in time_options["blend"]) else 0.0

    # A disabled tag still gets removed from the prompt, but does not need to
    # resolve or load a LoRA file.
    if wModel == 0.0 and (not has_clip or wClip == 0.0):
        return None

    # Use our new matching system
    lora_name = find_best_match(name, lora_files, log=console_log, fuzzy_search=is_lora_fuzzy_search_enabled(), max_logged=get_lora_max_logged_candidates())

    if lora_name is None:
        if console_log:
            print(f"No matching LoRA found for tag: {(type, name, wModel, wClip)}")
        return None

    if console_log:
        logged_weight = time_options["blend"] if time_options is not None and time_options.get("blend") is not None else wModel
        print(f"\nApplying LoRA: {(type, name, logged_weight, wClip)} >> {lora_name}")
        if scheduled:
            range_text = ",".join(f"{start}-{end if end is not None else 'end'}" for start, end in ranges)
            print(f"LoraTagLoader: Model sampling steps {range_text} (inclusive); CLIP strength remains constant.")
        if time_options is not None:
            print(f"LoraTagLoader: Video time windows {time_options['ranges']} seconds.")
            if time_options.get("blend") is not None:
                print(f"LoraTagLoader: Model strength ramps from {time_options['blend'][0]} to {time_options['blend'][1]} within the time window.")

    return lora_name, wModel, wClip, ranges, scheduled, time_options


def load_lora_file(lora_name):
    """Load a LoRA state dict, reusing the cached file when it was the last one loaded."""
    global _LOADED_LORA
    lora_path = folder_paths.get_full_path("loras", lora_name)
    if _LOADED_LORA is not None and _LOADED_LORA[0] == lora_path:
        return _LOADED_LORA[1]
    # Release the previous file before loading the next one.
    _LOADED_LORA = None
    lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
    _LOADED_LORA = (lora_path, lora)
    return lora


class LoraTagLoader(io.ComfyNode):
    """
    LoraTagLoader is responsible for loading Lora tags from the provided text.
    It uses a regex pattern to identify specific tags within the text.
    Original version: https://github.com/badjeff/comfyui_lora_tag_loader
    This version also includes a new matching system to find the "best" matching LoRA file based on scoring.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoraTagLoader",
            display_name="🏷️ LoRA Loader Prompt Tags",
            category="⚡ MNeMiC Nodes",
            description="Loads LoRAs from prompt tags, with optional denoising step ranges, video time windows, or strength ramps, and removes the tags from the prompt.",
            inputs=[
                io.Model.Input("MODEL", tooltip="The model to apply the LoRAs to. Supports step schedules and opt-in time windows for LTX and MiniMax H3 video."),
                io.Clip.Input("CLIP", optional=True, tooltip="The text encoder to patch. CLIP strengths are global; time= tags default to CLIP strength 0."),
                io.String.Input(
                    "STRING",
                    multiline=True,
                    force_input=True,
                    tooltip="LoRA tags with step ranges or time=0-10:blend=0.5-2 in video seconds. Video effects may spread across boundaries; see the node Info panel.",
                ),
            ],
            outputs=[
                io.Model.Output(display_name="MODEL", tooltip="The model with constant LoRAs and optional per-LoRA sampling schedules."),
                io.Clip.Output(display_name="CLIP", tooltip="The text encoder with constant LoRA strengths. None when no CLIP was provided."),
                io.String.Output(display_name="STRING", tooltip="The prompt with angle-bracket tags removed."),
            ],
        )

    @classmethod
    def execute(cls, MODEL, STRING, CLIP=None) -> io.NodeOutput:
        console_log = is_lora_console_log_enabled()
        if console_log:
            print(f"\nLoraTagLoader processing text: {STRING}")

        founds = re.findall(TAG_PATTERN, STRING)
        if len(founds) < 1:
            return io.NodeOutput(MODEL, CLIP, STRING)

        model_lora = MODEL
        clip_lora = CLIP

        lora_files = folder_paths.get_filename_list("loras")
        for f in founds:
            spec = parse_lora_tag(f, clip_lora is not None, lora_files, console_log)
            if spec is None:
                continue
            lora_name, wModel, wClip, ranges, scheduled, time_options = spec
            lora = load_lora_file(lora_name)

            # Apply the LoRA
            is_zit = False
            if hasattr(comfy.model_base, "Lumina2"):
                if isinstance(model_lora.model, comfy.model_base.Lumina2):
                    is_zit = True

            if is_zit:
                if console_log:
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
                    model_lora, clip_lora = _apply_lora(model_lora, clip_lora, lora, wModel, wClip, ranges, scheduled, time_options)
                finally:
                    # Always restore the original function
                    comfy.lora.model_lora_keys_unet = original_model_lora_keys_unet
            else:
                model_lora, clip_lora = _apply_lora(model_lora, clip_lora, lora, wModel, wClip, ranges, scheduled, time_options)

        # Remove the LoRA tags from the text
        plain_prompt = re.sub(TAG_PATTERN, "", STRING)
        return io.NodeOutput(model_lora, clip_lora, plain_prompt)
