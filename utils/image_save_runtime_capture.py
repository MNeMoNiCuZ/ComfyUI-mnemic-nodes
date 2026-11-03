import os
import re
from collections import deque

from . import image_save_runtime_hook as hook


SAMPLER_TYPES = {"KSampler", "KSamplerAdvanced", "SamplerCustomAdvanced"}
SAMPLER_FIELD_MAP = {
    "KSampler": {"positive": "positive", "negative": "negative", "model": "model"},
    "KSamplerAdvanced": {"positive": "positive", "negative": "negative", "model": "model"},
    "SamplerCustomAdvanced": {"positive": "guider", "negative": None, "model": "model"},
}
TEXT_KEYS = ("text", "text_g", "t5xxl", "prompt")


def _find_sampler_for_save_node(prompt: dict, save_node_id: str):
    q = deque([str(save_node_id)])
    seen = set()
    while q:
        nid = q.popleft()
        if nid in seen:
            continue
        seen.add(nid)
        node = prompt.get(nid, {})
        if node.get("class_type", "") in SAMPLER_TYPES:
            return nid
        for _, value in node.get("inputs", {}).items():
            if isinstance(value, list) and len(value) >= 1:
                parent = str(value[0])
                if parent not in seen:
                    q.append(parent)
    return None


def _walk_to_encoder(start_link, prompt: dict):
    """The first text encode node upstream of a conditioning link, and which of its outputs was followed."""
    q = deque([start_link])
    seen = set()
    while q:
        link = q.popleft()
        nid = str(link[0])
        if nid in seen:
            continue
        seen.add(nid)
        node = prompt.get(nid, {})
        if is_text_encoder(node):
            return node, link[1]
        for v in node.get("inputs", {}).values():
            if isinstance(v, list) and len(v) == 2:
                q.append(v)
    return None, 0


def _resolved_inputs(node_id: str):
    import execution
    from nodes import NODE_CLASS_MAPPINGS
    from comfy_execution.graph import DynamicPrompt

    prompt = hook.current_prompt
    extra_data = hook.current_extra_data
    outputs = None
    if hook.prompt_executer is not None:
        try:
            outputs = hook.prompt_executer.caches.outputs
        except Exception:
            return {}
    if outputs is None:
        return {}

    obj = prompt.get(str(node_id), {})
    class_type = obj.get("class_type")
    if class_type not in NODE_CLASS_MAPPINGS:
        return {}
    obj_class = NODE_CLASS_MAPPINGS[class_type]
    try:
        data = execution.get_input_data(
            obj.get("inputs", {}),
            obj_class,
            str(node_id),
            outputs,
            DynamicPrompt(prompt),
            extra_data,
        )
        return data[0] if isinstance(data, (list, tuple)) and data else {}
    except Exception:
        return {}


def cached_output(node_id: str, output_index: int):
    """The value a node already produced in this run, or None if it is not cached."""
    if hook.prompt_executer is None:
        return None
    cached = hook.prompt_executer.caches.outputs.get_local(str(node_id))
    if cached is None or cached.outputs is None or output_index >= len(cached.outputs):
        return None
    value = cached.outputs[output_index]
    return value[0] if isinstance(value, list) and value else value


def text_input(value) -> str:
    """A text input as the node received it: typed in, or the output of the node it is linked to."""
    if isinstance(value, list):
        value = cached_output(value[0], value[1])
    return value if isinstance(value, str) else ""


def is_text_encoder(node: dict) -> bool:
    # CLIPTextEncode, CLIPTextEncodeSDXL, TextEncodeQwenImage21, ...
    return "TextEncode" in node.get("class_type", "")


def encoder_text(node: dict, output_index: int = 0) -> str:
    """The prompt a text encode node received. Encoders with their own negative output read negative_prompt for it."""
    inputs = node.get("inputs", {})
    keys = ("negative_prompt",) if output_index == 1 and "negative_prompt" in inputs else TEXT_KEYS
    for key in keys:
        text = text_input(inputs.get(key))
        if text.strip():
            return text
    return ""


def _collect_loras_from_model_path(start_link, prompt: dict):
    out = []
    seen_names = set()
    q = deque([start_link] if isinstance(start_link, list) else [])
    seen_nodes = set()
    while q:
        link = q.popleft()
        if not isinstance(link, list) or len(link) < 1:
            continue
        nid = str(link[0])
        if nid in seen_nodes:
            continue
        seen_nodes.add(nid)
        node = prompt.get(nid, {})
        ct = str(node.get("class_type", ""))
        inp = _resolved_inputs(nid)

        lname = inp.get("lora_name")
        if isinstance(lname, list) and lname:
            lname = lname[0]
        if isinstance(lname, str) and lname and lname != "None" and lname not in seen_names:
            out.append(lname)
            seen_names.add(lname)

        for k, v in inp.items():
            if isinstance(v, dict) and k.startswith("lora_") and v.get("on", False) and v.get("lora"):
                n = str(v.get("lora"))
                if n and n not in seen_names:
                    out.append(n)
                    seen_names.add(n)

        ct_lower = str(ct or "").lower()
        # Node ids changed from emoji display strings to MNeMiC_*; accept both.
        if "lora loader prompt tags" in ct_lower or "loratagloader" in ct_lower:
            s = inp.get("STRING", "")
            if isinstance(s, list) and s:
                s = s[0]
            if isinstance(s, str):
                for m in re.findall(r"<lora:([^>:]+)", s, flags=re.IGNORECASE):
                    n = m.strip()
                    if n and n not in seen_names:
                        out.append(n)
                        seen_names.add(n)

        for _, v in node.get("inputs", {}).items():
            if isinstance(v, list) and len(v) >= 1:
                q.append(v)
    return out


def capture_runtime_prompt_and_loras():
    prompt = hook.current_prompt or {}
    save_node_id = hook.current_save_node_id
    if not prompt or not save_node_id:
        return None

    sampler_id = _find_sampler_for_save_node(prompt, save_node_id)
    if not sampler_id:
        return None

    sampler_node = prompt.get(sampler_id, {})
    sampler_type = sampler_node.get("class_type", "")
    fmap = SAMPLER_FIELD_MAP.get(sampler_type, {})
    sinputs = sampler_node.get("inputs", {})

    pos_text = ""
    neg_text = ""

    pos_field = fmap.get("positive")
    if pos_field and isinstance(sinputs.get(pos_field), list):
        node, index = _walk_to_encoder(sinputs.get(pos_field), prompt)
        if node:
            pos_text = encoder_text(node, index)

    neg_field = fmap.get("negative")
    if neg_field and isinstance(sinputs.get(neg_field), list):
        node, index = _walk_to_encoder(sinputs.get(neg_field), prompt)
        if node:
            neg_text = encoder_text(node, index)

    model_field = fmap.get("model")
    loras = []
    if model_field and isinstance(sinputs.get(model_field), list):
        loras = _collect_loras_from_model_path(sinputs.get(model_field), prompt)

    loras_clean = [os.path.splitext(os.path.basename(x))[0] for x in loras if x]
    loras_clean = list(dict.fromkeys(loras_clean))

    return {
        "positive": pos_text or "",
        "negative": neg_text or "",
        "loras": loras_clean,
    }
