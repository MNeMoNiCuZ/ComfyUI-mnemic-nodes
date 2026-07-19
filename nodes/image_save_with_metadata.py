"""
Save Image With Metadata

Original source code:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
"""

import json
import os
import re
import threading
from collections import deque
from datetime import datetime

import folder_paths
import numpy as np
from PIL import Image

from ..utils.image_save_with_metadata_civitai import (
    civitai_lora_key_name,
    get_civitai_sampler_name,
)
from ..utils.image_save_with_metadata_prompt_extractor import PromptMetadataExtractor
from ..utils.image_save_with_metadata_saver import save_image
from ..utils.image_save_with_metadata_utils import (
    full_checkpoint_path_for,
    full_lora_path_for,
)
from ..utils.image_save_runtime_capture import capture_runtime_prompt_and_loras
from ..utils.batch_wildcard_runtime import get_batch_prompts
from .wildcard_processor import WildcardProcessor

SEED_FIELDS = ("seed", "noise_seed")
STEPS_FIELDS = ("steps",)
CFG_FIELDS = ("cfg", "cfg_scale", "guidance")
SAMPLER_FIELDS = ("sampler_name",)
SCHEDULER_FIELDS = ("scheduler",)
DENOISE_FIELDS = ("denoise",)
WIDTH_FIELDS = ("width", "empty_latent_width")
HEIGHT_FIELDS = ("height", "empty_latent_height")
CKPT_NAME_FIELDS = ("ckpt_name", "unet_name")

_WILDCARD_PROCESSOR = None
_WILDCARD_PROCESSOR_LOCK = threading.Lock()


def _get_wildcard_processor() -> WildcardProcessor:
    global _WILDCARD_PROCESSOR
    if _WILDCARD_PROCESSOR is not None:
        return _WILDCARD_PROCESSOR
    with _WILDCARD_PROCESSOR_LOCK:
        if _WILDCARD_PROCESSOR is None:
            _WILDCARD_PROCESSOR = WildcardProcessor()
    return _WILDCARD_PROCESSOR


def _is_direct_value(v) -> bool:
    return not isinstance(v, list)


def _first_direct(prompt: dict, field_names: tuple, default=None):
    for _, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in field_names:
            if fname in inputs and _is_direct_value(inputs[fname]):
                return inputs[fname]
    return default


def _all_direct(prompt: dict, field_names: tuple) -> list:
    results = []
    for nid, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in field_names:
            if fname in inputs and _is_direct_value(inputs[fname]):
                results.append((nid, inputs[fname]))
    return results


def _find_checkpoint_name(prompt: dict) -> str:
    for _, node in prompt.items():
        inputs = node.get("inputs", {})
        for fname in CKPT_NAME_FIELDS:
            if fname in inputs and _is_direct_value(inputs[fname]):
                val = str(inputs[fname])
                if val and val.lower() != "none":
                    return val
    return ""


def _find_lora_info(prompt: dict) -> list:
    loras = []
    seen_names = set()

    for _, node in prompt.items():
        ct = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if "lora_name" in inputs and _is_direct_value(inputs.get("lora_name")):
            name = str(inputs["lora_name"])
            if name and name != "None" and name not in seen_names:
                sm = inputs.get("strength_model", 1.0)
                sc = inputs.get("strength_clip", 1.0)
                sm = sm if _is_direct_value(sm) else 1.0
                sc = sc if _is_direct_value(sc) else 1.0
                loras.append((name, float(sm), float(sc)))
                seen_names.add(name)

        if "rgthree" in ct.lower() or "power" in ct.lower() or "lora" in ct.lower():
            for key, val in inputs.items():
                if key.startswith("lora_") and isinstance(val, dict):
                    if val.get("on", False) and val.get("lora"):
                        name = str(val["lora"])
                        if name and name != "None" and name not in seen_names:
                            strength = float(val.get("strength", 1.0))
                            loras.append((name, strength, strength))
                            seen_names.add(name)

        if "stack" in ct.lower() and "lora" in ct.lower():
            for key, val in inputs.items():
                if "lora" in key.lower() and "name" in key.lower() and _is_direct_value(val):
                    name = str(val)
                    if name and name != "None" and name not in seen_names:
                        loras.append((name, 1.0, 1.0))
                        seen_names.add(name)

        # Custom MNeMiC node: LoRA Loader Prompt Tags / LoraTagLoader
        if "lora loader prompt tags" in ct.lower() or ct == "LoraTagLoader":
            raw = inputs.get("STRING", "")
            if isinstance(raw, list):
                raw = _resolve_link_text(raw, prompt)
            if isinstance(raw, str) and raw:
                for m in re.findall(r"<lora:([^>:]+)(?::([^>:]+))?(?::([^>:]+))?>", raw, flags=re.IGNORECASE):
                    name = (m[0] or "").strip()
                    if not name or name in seen_names:
                        continue
                    try:
                        sm = float(m[1]) if m[1] not in (None, "", "0") else 1.0
                    except Exception:
                        sm = 1.0
                    try:
                        sc = float(m[2]) if m[2] not in (None, "", "0") else sm
                    except Exception:
                        sc = sm
                    loras.append((name, sm, sc))
                    seen_names.add(name)

    return loras


SAMPLER_FIELDS_MAP = {
    "KSampler": {"positive": "positive", "negative": "negative"},
    "KSamplerAdvanced": {"positive": "positive", "negative": "negative"},
    "SamplerCustomAdvanced": {"positive": "guider"},
}

CLIP_ENCODER_TYPES = {"CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeFlux"}


def _get_node(prompt: dict, node_id: str) -> dict:
    return prompt.get(str(node_id), {})


def _node_class(node: dict) -> str:
    return str(node.get("class_type", ""))


def _node_widget(node: dict, index: int, default=None):
    values = node.get("widgets_values", [])
    if isinstance(values, list) and len(values) > index:
        return values[index]
    return default


def _resolve_link_text(link, prompt: dict, depth=0, visited=None) -> str:
    if visited is None:
        visited = set()
    if depth > 40 or not isinstance(link, list) or len(link) < 1:
        return ""

    node_id = str(link[0])
    out_idx = int(link[1]) if len(link) > 1 and isinstance(link[1], int) else 0
    key = (node_id, out_idx)
    if key in visited:
        return ""
    visited.add(key)

    node = _get_node(prompt, node_id)
    class_type = _node_class(node)
    inputs = node.get("inputs", {})
    class_lower = class_type.lower()

    if class_type in CLIP_ENCODER_TYPES:
        for k in ("text", "text_g", "t5xxl", "prompt"):
            v = inputs.get(k)
            if isinstance(v, str) and v.strip():
                return v
            if isinstance(v, list):
                r = _resolve_link_text(v, prompt, depth + 1, visited)
                if r:
                    return r

    if class_type == "StringConcat" or "string concat" in class_lower:
        parts = []
        keys = sorted([k for k in inputs.keys() if k.startswith("string_")], key=lambda x: int(x.split("_")[1]))
        for k in keys:
            v = inputs.get(k)
            if isinstance(v, str) and v:
                parts.append(v)
            elif isinstance(v, list):
                rv = _resolve_link_text(v, prompt, depth + 1, visited)
                if rv:
                    parts.append(rv)
        delimiter = str(inputs.get("delimiter", _node_widget(node, 0, "")) or "")
        return delimiter.join(parts)

    if class_type == "WildcardProcessor" or "wildcard processor" in class_lower:
        wildcard_string = str(inputs.get("wildcard_string", _node_widget(node, 0, "")) or "")
        seed_input = inputs.get("seed", _node_widget(node, 1, 0))
        if isinstance(seed_input, list):
            seed = _resolve_link_int(seed_input, prompt, depth + 1, visited)
        else:
            try:
                seed = int(seed_input)
            except Exception:
                seed = 0
        sep = str(inputs.get("multiple_separator", _node_widget(node, 3, " ")) or " ")
        recache = bool(inputs.get("recache_wildcards", _node_widget(node, 4, False)))
        try:
            wp = _get_wildcard_processor()
            return wp.process_wildcards(
                wildcard_string=wildcard_string,
                seed=seed,
                recache_wildcards=recache,
                tag_extraction_tags="",
            )[0]
        except Exception:
            return wildcard_string

    if class_type == "LoraTagLoader" or "lora loader prompt tags" in class_lower:
        source = inputs.get("STRING", "")
        if isinstance(source, list):
            source = _resolve_link_text(source, prompt, depth + 1, visited)
        if not isinstance(source, str):
            source = ""
        # Output index 2 is cleaned prompt string in this node; return cleaned text.
        cleaned = re.sub(r"<[0-9a-zA-Z:\_\-\.\s/()\\]+>", "", source)
        return re.sub(r"\s+", " ", cleaned).strip()

    if class_type == "PromptPropertyExtractor":
        input_string = inputs.get("input_string", "")
        if not isinstance(input_string, str):
            input_string = ""
        if out_idx == 4:
            return _parse_neg_from_prompt_property_input(input_string)
        return input_string

    for key_name in ("text", "text_g", "t5xxl", "prompt", "string", "value", "STRING", "processed_text"):
        val = inputs.get(key_name)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, list):
            resolved = _resolve_link_text(val, prompt, depth + 1, visited)
            if resolved:
                return resolved

    return ""


def _resolve_link_int(link, prompt: dict, depth=0, visited=None) -> int:
    if visited is None:
        visited = set()
    if depth > 40 or not isinstance(link, list) or len(link) < 1:
        return 0
    node = _get_node(prompt, str(link[0]))
    class_type = _node_class(node)
    class_lower = class_type.lower()
    if class_type == "Seed (rgthree)" or class_lower.startswith("seed"):
        try:
            return int(_node_widget(node, 0, 0))
        except Exception:
            return 0
    # fall back: try widget[0]
    try:
        return int(_node_widget(node, 0, 0))
    except Exception:
        return 0


def _parse_neg_from_prompt_property_input(input_string: str) -> str:
    if not isinstance(input_string, str):
        return ""
    tags = re.findall(r"<((?:[^>\\]|\\.)*)>", input_string)
    negatives = []
    for tag in tags:
        parts = tag.split(":", 1)
        if len(parts) < 2:
            continue
        name = parts[0].strip().lower()
        value = parts[1].replace(r"\>", ">").strip()
        if name in ("neg", "negative") and value:
            negatives.append(value)
    return ", ".join(negatives)


def _resolve_text_from_link(link, prompt: dict, depth=0, visited=None) -> str:
    if visited is None:
        visited = set()
    if depth > 20 or not isinstance(link, list) or len(link) < 1:
        return ""
    node_id = str(link[0])
    output_idx = int(link[1]) if len(link) > 1 and isinstance(link[1], int) else 0
    key = (node_id, output_idx)
    if key in visited:
        return ""
    visited.add(key)

    node = prompt.get(node_id, {})
    class_type = node.get("class_type", "")
    inputs = node.get("inputs", {})

    if class_type == "LoraTagLoader" or "lora loader prompt tags" in class_type.lower():
        return _resolve_link_text(link, prompt, depth, visited)

    if class_type == "PromptPropertyExtractor":
        input_string = inputs.get("input_string", "")
        if output_idx == 4:
            return _parse_neg_from_prompt_property_input(input_string)
        return input_string if isinstance(input_string, str) else ""

    return _resolve_link_text(link, prompt, depth, visited)


def _extract_clip_text_from_node(node: dict, prompt: dict) -> str:
    inputs = node.get("inputs", {})
    for key in ("text", "text_g", "t5xxl", "prompt"):
        val = inputs.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, list):
            resolved = _resolve_text_from_link(val, prompt)
            if resolved:
                return resolved
    return ""


def _find_conditioning_text(start_link, prompt: dict, expected: str) -> str:
    if not isinstance(start_link, list) or len(start_link) < 1:
        return ""
    start_node_id = str(start_link[0])
    start_output_idx = int(start_link[1]) if len(start_link) > 1 and isinstance(start_link[1], int) else 0
    queue = deque([(start_node_id, start_output_idx)])
    visited = set()
    while queue:
        nid, out_idx = queue.popleft()
        if (nid, out_idx) in visited:
            continue
        visited.add((nid, out_idx))

        node = prompt.get(nid, {})
        class_type = node.get("class_type", "")
        if class_type in CLIP_ENCODER_TYPES:
            return _extract_clip_text_from_node(node, prompt)
        if class_type == "PromptPropertyExtractor":
            input_string = node.get("inputs", {}).get("input_string", "")
            if expected == "negative":
                return _parse_neg_from_prompt_property_input(input_string)
            if isinstance(input_string, str):
                return input_string

        for val in node.get("inputs", {}).values():
            if isinstance(val, list) and len(val) >= 1:
                next_id = str(val[0])
                next_out = int(val[1]) if len(val) > 1 and isinstance(val[1], int) else 0
                queue.append((next_id, next_out))
    return ""


def _looks_negative(text: str) -> bool:
    t = (text or "").lower()
    hints = ("bad", "worst", "lowres", "blurry", "nsfw", "artifact", "ugly", "deformed", "negative")
    return any(h in t for h in hints)


def _strip_lora_tags(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"<lora:[^>]+>", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_positive_from_lora_tag_loader(prompt: dict) -> str:
    for _, node in prompt.items():
        ct = str(node.get("class_type", "")).lower()
        if "lora loader prompt tags" in ct or ct == "loratagloader":
            src = node.get("inputs", {}).get("STRING", "")
            if isinstance(src, list):
                src = _resolve_link_text(src, prompt)
            if isinstance(src, str) and src.strip():
                return _strip_lora_tags(src)
    return ""


def _find_prompts(prompt: dict) -> tuple:
    positive = ""
    negative = ""

    for _, node in prompt.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        sampler_map = SAMPLER_FIELDS_MAP.get(class_type)
        if not sampler_map:
            continue

        if not positive:
            pos_field = sampler_map.get("positive")
            pos_ref = inputs.get(pos_field) if pos_field else None
            if isinstance(pos_ref, list) and len(pos_ref) >= 1:
                positive = _find_conditioning_text(pos_ref, prompt, "positive")

        if not negative:
            neg_field = sampler_map.get("negative")
            neg_ref = inputs.get(neg_field) if neg_field else None
            if isinstance(neg_ref, list) and len(neg_ref) >= 1:
                negative = _find_conditioning_text(neg_ref, prompt, "negative")

        if positive and negative:
            break

    if not positive or not negative:
        all_texts = []
        for _, node in prompt.items():
            if node.get("class_type", "") in CLIP_ENCODER_TYPES:
                t = _extract_clip_text_from_node(node, prompt)
                if t:
                    all_texts.append(t)
        dedup_texts = list(dict.fromkeys(all_texts))
        all_texts = dedup_texts
        neg_candidates = [t for t in all_texts if _looks_negative(t)]
        pos_candidates = [t for t in all_texts if not _looks_negative(t)]
        if not positive:
            positive = (pos_candidates[0] if pos_candidates else (all_texts[0] if all_texts else ""))
        if not negative:
            negative = (neg_candidates[0] if neg_candidates else (all_texts[1] if len(all_texts) > 1 else ""))

    if positive and negative and positive == negative:
        all_texts = []
        for _, node in prompt.items():
            if node.get("class_type", "") in CLIP_ENCODER_TYPES:
                t = _extract_clip_text_from_node(node, prompt)
                if t:
                    all_texts.append(t)
        neg_candidates = [t for t in all_texts if _looks_negative(t) and t != positive]
        pos_candidates = [t for t in all_texts if (not _looks_negative(t)) and t != negative]
        if neg_candidates:
            negative = neg_candidates[0]
        if pos_candidates:
            positive = pos_candidates[0]

    # Systematic fallback for workflows where positive text is assembled upstream and fed
    # through LoRA Loader Prompt Tags before CLIPTextEncode.
    if (not positive or positive == negative) and prompt:
        lora_loader_positive = _find_positive_from_lora_tag_loader(prompt)
        if lora_loader_positive:
            positive = lora_loader_positive

    return positive, negative


def _extract_from_workflow(prompt: dict) -> dict:
    if not prompt:
        return {
            "positive": "",
            "negative": "",
            "modelname": "",
            "loras": [],
            "seed": 0,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "",
            "scheduler_name": "normal",
            "width": 512,
            "height": 512,
            "denoise": 1.0,
        }

    positive, negative = _find_prompts(prompt)
    all_widths = _all_direct(prompt, WIDTH_FIELDS)
    all_heights = _all_direct(prompt, HEIGHT_FIELDS)
    width = max((v for _, v in all_widths), default=512) if all_widths else 512
    height = max((v for _, v in all_heights), default=512) if all_heights else 512

    return {
        "positive": positive,
        "negative": negative,
        "modelname": _find_checkpoint_name(prompt),
        "loras": _find_lora_info(prompt),
        "seed": _first_direct(prompt, SEED_FIELDS, 0),
        "steps": _first_direct(prompt, STEPS_FIELDS, 20),
        "cfg": _first_direct(prompt, CFG_FIELDS, 7.0),
        "sampler_name": _first_direct(prompt, SAMPLER_FIELDS, ""),
        "scheduler_name": _first_direct(prompt, SCHEDULER_FIELDS, "normal"),
        "width": int(width),
        "height": int(height),
        "denoise": _first_direct(prompt, DENOISE_FIELDS, 1.0),
    }


def _format_like_format_date_time(date_format: str, respect_system_locale: bool = False) -> str:
    now = datetime.now()
    temp_format = date_format.replace("%%", "__DOUBLE_PERCENT_PLACEHOLDER__")
    if not respect_system_locale:
        temp_format = temp_format.replace("%x", "%Y-%m-%d")
        temp_format = temp_format.replace("%c", "%Y-%m-%d %H.%M.%S")
    temp_format = re.sub(r"(?<!%)%w", str(now.weekday()), temp_format)
    temp_format = re.sub(r"(?<!%)%u", str(now.isoweekday() % 7), temp_format)
    formatted_string = now.strftime(temp_format).replace("__DOUBLE_PERCENT_PLACEHOLDER__", "%")
    if "%X" in date_format:
        formatted_string = formatted_string.replace(now.strftime("%X"), now.strftime("%X").replace(":", "."))
    if "%c" in date_format:
        formatted_string = formatted_string.replace(now.strftime("%c"), now.strftime("%c").replace(":", "."))
    return formatted_string


def _resolve_strftime(text: str) -> str:
    pattern = re.compile(r"%date:([^%]+)%")
    if pattern.search(text):
        def repl(match):
            fmt = match.group(1)
            converted = (
                fmt.replace("yyyy", "%Y")
                .replace("MM", "%m")
                .replace("dd", "%d")
                .replace("hh", "%H")
                .replace("mm", "%M")
                .replace("ss", "%S")
            )
            return _format_like_format_date_time(converted)

        return pattern.sub(repl, text)
    return _format_like_format_date_time(text)


def _parse_ckpt_basename(ckpt_name: str) -> str:
    filename = os.path.basename(ckpt_name)
    name, ext = os.path.splitext(filename)
    supported = getattr(folder_paths, "supported_pt_extensions", set()) | {".gguf"}
    return name if ext.lower() in supported else filename


def _get_unique_filename(output_path: str, prefix: str, extension: str) -> str:
    existing = [f for f in os.listdir(output_path) if f.startswith(prefix) and f.endswith(extension)]
    if not existing:
        return prefix
    suffixes = []
    for f in existing:
        name, _ = os.path.splitext(f)
        parts = name.split("_")
        if parts[-1].isdigit():
            suffixes.append(int(parts[-1]))
    return f"{prefix}_{(max(suffixes) + 1) if suffixes else 1:04d}"


def _clean_prompt(prompt_text: str, extractor: PromptMetadataExtractor) -> str:
    from pathlib import Path
    prompt_text = re.sub(extractor.LORA, "", prompt_text)
    prompt_text = re.sub(extractor.EMBEDDING, lambda m: Path(m.group(1)).stem, prompt_text)
    prompt_text = re.sub(r"\b[A-Z]+\([^)]*\)", "", prompt_text)
    return prompt_text


def _build_a111_params(positive: str, negative: str, ctx: dict) -> str:
    wf = ctx["wf"]
    extractor = PromptMetadataExtractor([positive, negative])
    prompt_loras = extractor.get_loras()

    node_lora_keys = []
    for lora_name, _, _ in wf["loras"]:
        key = civitai_lora_key_name(os.path.splitext(os.path.basename(lora_name))[0])
        if key not in prompt_loras:
            node_lora_keys.append(key)

    all_lora_names = [k.replace("LORA:", "") for k in list(prompt_loras.keys()) + node_lora_keys]

    pos_text = _clean_prompt(positive, extractor).strip() if ctx["strip_lora_prompt"] else positive.strip()
    neg_text = _clean_prompt(negative, extractor).strip() if ctx["strip_lora_prompt"] else negative.strip()

    direct_lora_names = [os.path.splitext(os.path.basename(n))[0] for (n, _, _) in wf.get("loras", []) if n]
    direct_lora_names += ctx["runtime_loras"]
    models_used = [ctx["basemodelname"]] + direct_lora_names + all_lora_names
    models_used_str = "\n".join(dict.fromkeys([m for m in models_used if m]))

    return (
        f"{pos_text}\n"
        f"Negative prompt: {neg_text}\n"
        f"Steps: {ctx['steps']}, Sampler: {ctx['display_sampler']}, CFG scale: {ctx['cfg']}, "
        f"Seed: {ctx['seed']}, Size: {ctx['width']}x{ctx['height']}"
        f", Model: {ctx['basemodelname']}, Models used: {models_used_str}, Version: ComfyUI"
    )


class ImageSaveWithMetadata:
    CATEGORY = "⚡ MNeMiC Nodes"
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    RETURN_TYPES = ()
    DESCRIPTION = (
        "Save images with Civitai-compatible metadata. Auto-extracts model, "
        "sampler, seed, prompts, etc. from the workflow. Only 'images' needs connecting."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {
                    "default": "%date:yyyy-MM-dd - hh.mm.ss%",
                    "tooltip": "Filename prefix template.\n\n"
                               "%Y: Year (e.g., 2025)\n"
                               "%m: Month (01-12)\n"
                               "%d: Day of month (01-31)\n"
                               "%H: Hour (24-hour clock) (00-23)\n"
                               "%M: Minute (00-59)\n"
                               "%S: Second (00-59)\n"
                               "%f: Microsecond (000000-999999)\n"
                               "%x: Date representation\n"
                               "%X: Time representation\n"
                               "%c: Date and time representation\n"
                               "%p: AM/PM\n"
                               "%A: Weekday full name (e.g., Thursday)\n"
                               "%a: Weekday abbreviated name (e.g., Thu)\n"
                               "%B: Month full name (e.g., August)\n"
                               "%b: Month abbreviated name (e.g., Aug)\n"
                               "%j: Day of year (001-366)\n"
                               "%W: Week number of year (Monday as first day) (00-53)\n"
                               "%w: Day index of week (Monday is 0) (0-6)\n"
                               "%U: Week number of year (Sunday as first day) (00-53)\n"
                               "%u: Day index of week (Sunday is 0) (0-6)\n"
                               "%%: A literal '%' character\n\n"
                               "%date:yyyy-MM-dd - hh.mm.ss%: custom date token style\n"
                               "%seed: resolved generation seed\n"
                               "%model: resolved model basename"
                }),
                "folder": ("STRING", {
                    "default": "%date:yyyy-MM-dd%",
                    "tooltip": "Subfolder under ComfyUI output directory.\n\n"
                               "%Y: Year (e.g., 2025)\n"
                               "%m: Month (01-12)\n"
                               "%d: Day of month (01-31)\n"
                               "%H: Hour (24-hour clock) (00-23)\n"
                               "%M: Minute (00-59)\n"
                               "%S: Second (00-59)\n"
                               "%f: Microsecond (000000-999999)\n"
                               "%x: Date representation\n"
                               "%X: Time representation\n"
                               "%c: Date and time representation\n"
                               "%p: AM/PM\n"
                               "%A: Weekday full name (e.g., Thursday)\n"
                               "%a: Weekday abbreviated name (e.g., Thu)\n"
                               "%B: Month full name (e.g., August)\n"
                               "%b: Month abbreviated name (e.g., Aug)\n"
                               "%j: Day of year (001-366)\n"
                               "%W: Week number of year (Monday as first day) (00-53)\n"
                               "%w: Day index of week (Monday is 0) (0-6)\n"
                               "%U: Week number of year (Sunday as first day) (00-53)\n"
                               "%u: Day index of week (Sunday is 0) (0-6)\n"
                               "%%: A literal '%' character\n\n"
                               "%date:yyyy-MM-dd - hh.mm.ss%: custom date token style\n"
                               "%seed: resolved generation seed\n"
                               "%model: resolved model basename"
                }),
                "file_format": (["png", "jpeg", "webp"],),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100}),
                "embed_workflow": ("BOOLEAN", {"default": True, "tooltip": "Include workflow in the image."}),
                "strip_lora_prompt": ("BOOLEAN", {"default": False, "tooltip": "Strip LoRAs from prompt."}),
            },
            "optional": {
                "positive_override": ("STRING", {"default": "", "multiline": True, "forceInput": True, "tooltip": "Override the auto-detected positive prompt. Accepts a single string (applied to every image) or a list of prompts (one per image, looping if the count differs from the number of images)."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def save_images(
        self,
        images,
        filename_prefix="%date:yyyy-MM-dd - hh.mm.ss%",
        folder="%date:yyyy-MM-dd%",
        file_format="png",
        quality=100,
        embed_workflow=True,
        strip_lora_prompt=False,
        positive_override="",
        prompt=None,
        extra_pnginfo=None,
    ):
        # positive_override may be a single string or a list of per-image prompts
        # (e.g. wired from the Batch Wildcard Sampler's resolved_prompts list output).
        override_list = None
        override_text = ""
        if isinstance(positive_override, (list, tuple)):
            items = [str(x) for x in positive_override]
            if any(s.strip() for s in items):
                override_list = items
        elif isinstance(positive_override, str):
            override_text = positive_override
        elif positive_override is not None:
            override_text = str(positive_override)

        wf = _extract_from_workflow(prompt or {})
        runtime = capture_runtime_prompt_and_loras()
        runtime_positive = (runtime or {}).get("positive", "")
        runtime_negative = (runtime or {}).get("negative", "")
        runtime_loras = (runtime or {}).get("loras", [])

        num_images = len(images)

        # Batch Wildcard Sampler auto-pickup: per-image prompts published by that node.
        # Guarded so it only engages when such a node is actually in the current graph.
        batch_pos, batch_neg, batch_seed, batch_active = [], [], None, False
        try:
            has_batch_node = any(
                "batch wildcard" in str(n.get("class_type", "")).lower()
                for n in (prompt or {}).values()
            )
            if has_batch_node:
                batch = get_batch_prompts()
                batch_pos = batch.get("positive") or []
                batch_neg = batch.get("negative") or []
                batch_seed = batch.get("seed")
                batch_active = bool(batch_pos)
        except Exception as e:
            print(f"[ImageSaveWithMetadata] Batch prompt pickup skipped: {e}")
            batch_active = False

        modelname = wf["modelname"]
        seed = wf["seed"]
        steps = wf["steps"]
        cfg = wf["cfg"]
        sampler_name = wf["sampler_name"]
        scheduler_name = wf["scheduler_name"]
        width = wf["width"]
        height = wf["height"]

        resolved_folder = _resolve_strftime(folder).strip().rstrip("/")
        resolved_prefix = _resolve_strftime(filename_prefix)

        ckpt_path = full_checkpoint_path_for(modelname)
        display_sampler = get_civitai_sampler_name(sampler_name.replace("_gpu", ""), scheduler_name)
        basemodelname = _parse_ckpt_basename(modelname)

        ctx = {
            "wf": wf,
            "modelname": modelname,
            "ckpt_path": ckpt_path,
            "runtime_loras": runtime_loras,
            "strip_lora_prompt": strip_lora_prompt,
            "steps": steps,
            "cfg": cfg,
            "display_sampler": display_sampler,
            "seed": seed,
            "width": width,
            "height": height,
            "basemodelname": basemodelname,
        }

        # Resolve the positive/negative/seed for a given image index. Lists loop
        # (modulo) so a count mismatch never errors. Precedence for the positive:
        # explicit override (list or text) > batch auto-pickup > runtime/workflow.
        def positive_for(i):
            if override_list:
                return override_list[i % len(override_list)]
            if override_text.strip():
                return override_text
            if batch_active:
                return batch_pos[i % len(batch_pos)]
            return runtime_positive or wf["positive"]

        def negative_for(i):
            if batch_active and batch_neg:
                return batch_neg[i % len(batch_neg)]
            return runtime_negative or wf["negative"]

        def seed_for(i):
            if batch_active and batch_seed is not None:
                return batch_seed + i
            return seed

        resolved_prefix = resolved_prefix.replace("%seed", str(seed))
        resolved_prefix = resolved_prefix.replace("%model", basemodelname)

        output_dir = folder_paths.get_output_directory()
        full_output_path = os.path.join(output_dir, resolved_folder) if resolved_folder else output_dir
        os.makedirs(full_output_path, exist_ok=True)

        ext = "jpg" if file_format == "jpeg" else file_format
        results = []
        for idx, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            unique_name = _get_unique_filename(full_output_path, resolved_prefix, ext)
            final_filename = f"{unique_name}.{ext}"
            filepath = os.path.join(full_output_path, final_filename)

            # Always use the actual pixel dimensions of this image so the Size field
            # in the metadata matches the file on disk.  When an upscale pass runs
            # the decoded image is larger than the first-pass width/height stored in
            # the workflow; using stale workflow dimensions causes tools like Civitai
            # to reject the entire metadata block (including the prompt).
            actual_w, actual_h = img.size  # PIL gives (width, height)
            img_ctx = ctx if (actual_w == ctx["width"] and actual_h == ctx["height"]) else {**ctx, "width": actual_w, "height": actual_h}
            image_params = _build_a111_params(positive_for(idx), negative_for(idx), {**img_ctx, "seed": seed_for(idx)})

            save_image(
                img,
                filepath,
                ext,
                quality,
                True,
                False,
                image_params,
                prompt if embed_workflow else None,
                extra_pnginfo if embed_workflow else None,
                embed_workflow,
            )

            subfolder = os.path.normpath(resolved_folder) if resolved_folder else ""
            results.append({"filename": final_filename, "subfolder": subfolder if subfolder != "." else "", "type": "output"})

        return {"ui": {"images": results}}


NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageSaveWithMetadata": "💾 Save Image With Metadata",
}
