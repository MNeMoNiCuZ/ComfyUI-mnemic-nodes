"""
Save Image With Metadata

Original source code:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
"""

import json
import os
import re

import folder_paths
import numpy as np
from PIL import Image

from comfy_api.latest import io

from ..utils.date_templates import resolve_date_template as _resolve_strftime
from ..utils.image_save_with_metadata_civitai import (
    civitai_lora_key_name,
    get_civitai_sampler_name,
)
from ..utils.image_save_with_metadata_prompt_extractor import PromptMetadataExtractor
from ..utils.image_save_with_metadata_saver import save_image
from ..utils.image_save_with_metadata_utils import (
    full_checkpoint_path_for,
    full_lora_path_for,
    get_sha256,
)
from ..utils.image_save_runtime_capture import cached_output, capture_runtime_prompt_and_loras
from ..utils.batch_wildcard_runtime import get_batch_prompts

SEED_FIELDS = ("seed", "noise_seed")
STEPS_FIELDS = ("steps",)
CFG_FIELDS = ("cfg", "cfg_scale", "guidance")
SAMPLER_FIELDS = ("sampler_name",)
SCHEDULER_FIELDS = ("scheduler",)
DENOISE_FIELDS = ("denoise",)
WIDTH_FIELDS = ("width", "empty_latent_width")
HEIGHT_FIELDS = ("height", "empty_latent_height")
CKPT_NAME_FIELDS = ("ckpt_name", "unet_name")


def _is_node(class_type, *names) -> bool:
    """True when `class_type` refers to one of the named MNeMiC nodes.

    Node ids changed from emoji display strings to `MNeMiC_*`, and workflows on
    disk can still contain either. Pass both spellings of a name, e.g.
    `_is_node(ct, "loratagloader", "lora loader prompt tags")`.
    """
    ct = str(class_type or "").lower()
    for name in names:
        if name.lower() in ct:
            return True
    return False


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
        if _is_node(ct, "loratagloader", "lora loader prompt tags"):
            raw = _text_input(inputs.get("STRING"))
            if raw:
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


CLIP_ENCODER_TYPES = {"CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeFlux"}


def _text_input(value) -> str:
    """A text input as the node received it: typed in, or the output of the node it is linked to."""
    if isinstance(value, list):
        value = cached_output(value[0], value[1])
    return value if isinstance(value, str) else ""


def _first_clip_text(prompt: dict) -> str:
    for node in prompt.values():
        if node.get("class_type", "") in CLIP_ENCODER_TYPES:
            inputs = node.get("inputs", {})
            for key in ("text", "text_g", "t5xxl", "prompt"):
                text = _text_input(inputs.get(key))
                if text.strip():
                    return text
    return ""


def _extract_from_workflow(prompt: dict) -> dict:
    if not prompt:
        return {
            "positive": "",
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

    all_widths = _all_direct(prompt, WIDTH_FIELDS)
    all_heights = _all_direct(prompt, HEIGHT_FIELDS)
    width = max((v for _, v in all_widths), default=512) if all_widths else 512
    height = max((v for _, v in all_heights), default=512) if all_heights else 512

    return {
        "positive": _first_clip_text(prompt),
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
    # Quoted like A1111 infotext values: Civitai only parses the single "Steps:" line and
    # would otherwise read the extra lines as part of the negative prompt.
    if any(c in models_used_str for c in ',\n:"'):
        models_used_str = json.dumps(models_used_str, ensure_ascii=False)

    # Civitai matches resources by AutoV2 hash (first 10 hex chars of the file's SHA-256)
    # and only accepts lowercase "lora:"/"embed:" keys.
    hashes = {}
    if ctx["ckpt_path"]:
        hashes["model"] = get_sha256(ctx["ckpt_path"])[:10]
    lora_paths = {k.replace("LORA:", ""): v[0] for k, v in prompt_loras.items()}
    lora_sources = [(os.path.splitext(os.path.basename(n))[0], n) for (n, _, _) in wf.get("loras", []) if n]
    lora_sources += [(n, n) for n in ctx["runtime_loras"]]
    for name, lora in lora_sources:
        if name not in lora_paths:
            lora_paths[name] = full_lora_path_for(lora)
    for name, path in lora_paths.items():
        if path:
            hashes[f"lora:{name}"] = get_sha256(path)[:10]
    for key, (path, _) in extractor.get_embeddings().items():
        hashes[key] = get_sha256(path)[:10]
    model_hash_str = f", Model hash: {hashes['model']}" if "model" in hashes else ""
    hashes_str = f", Hashes: {json.dumps(hashes, separators=(',', ':'))}" if hashes else ""

    return (
        f"{pos_text}\n"
        f"Negative prompt: {neg_text}\n"
        f"Steps: {ctx['steps']}, Sampler: {ctx['display_sampler']}, CFG scale: {ctx['cfg']}, "
        f"Seed: {ctx['seed']}, Size: {ctx['width']}x{ctx['height']}{model_hash_str}"
        f", Model: {ctx['basemodelname']}{hashes_str}, Models used: {models_used_str}, Version: ComfyUI"
    )


class ImageSaveWithMetadata(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_ImageSaveWithMetadata",
            display_name="💾 Save Image With Metadata",
            category="⚡ MNeMiC Nodes",
            description=(
                "Save images with Civitai-compatible metadata. Auto-extracts model, "
                "sampler, seed, prompts, etc. from the workflow. Only 'images' needs connecting."
            ),
            inputs=[
                io.Image.Input("images", tooltip="The images to save. A batch is saved as separate numbered files."),
                io.String.Input(
                    "filename_prefix",
                    default="%date:yyyy-MM-dd - hh.mm.ss%",
                    tooltip="Filename prefix template.\n\n"
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
                            "%model: resolved model basename",
                ),
                io.String.Input(
                    "folder",
                    default="%date:yyyy-MM-dd%",
                    tooltip="Subfolder under ComfyUI output directory.\n\n"
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
                            "%model: resolved model basename",
                ),
                io.Combo.Input("file_format", options=["png", "jpeg", "webp"], tooltip="File type to write. PNG is lossless; jpeg and webp use the quality setting."),
                io.Int.Input("quality", default=100, min=1, max=100, advanced=True, tooltip="Compression quality for jpeg and webp, 1-100. Ignored for PNG."),
                io.Boolean.Input("embed_workflow", default=True, advanced=True, tooltip="Include workflow in the image."),
                io.Boolean.Input("strip_lora_prompt", default=False, advanced=True, tooltip="Strip LoRAs from prompt."),
                io.String.Input("positive_override", optional=True, default="", multiline=True, force_input=True, tooltip="Override the auto-detected positive prompt. Accepts a single string (applied to every image) or a list of prompts (one per image, looping if the count differs from the number of images)."),
            ],
            outputs=[],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            is_output_node=True,
        )

    @classmethod
    def execute(
        cls,
        images,
        filename_prefix="%date:yyyy-MM-dd - hh.mm.ss%",
        folder="%date:yyyy-MM-dd%",
        file_format="png",
        quality=100,
        embed_workflow=True,
        strip_lora_prompt=False,
        positive_override="",
    ) -> io.NodeOutput:
        prompt = cls.hidden.prompt
        extra_pnginfo = cls.hidden.extra_pnginfo
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
                _is_node(n.get("class_type", ""), "batchwildcardsampler", "batch wildcard")
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
            return runtime_negative

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

        return io.NodeOutput(ui={"images": results})


