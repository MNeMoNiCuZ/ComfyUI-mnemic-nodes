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
CLIP_TYPES = {"CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeFlux"}


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


def _walk_to_clip(start_link, prompt: dict):
    if not isinstance(start_link, list) or len(start_link) < 1:
        return None
    q = deque([str(start_link[0])])
    seen = set()
    while q:
        nid = q.popleft()
        if nid in seen:
            continue
        seen.add(nid)
        node = prompt.get(nid, {})
        if node.get("class_type", "") in CLIP_TYPES:
            return nid
        for _, v in node.get("inputs", {}).items():
            if isinstance(v, list) and len(v) >= 1:
                q.append(str(v[0]))
    return None


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


def _extract_text_from_clip_node(node_id: str):
    inp = _resolved_inputs(node_id)
    for k in ("text", "text_g", "t5xxl", "prompt"):
        v = inp.get(k)
        if isinstance(v, str):
            return v
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
            return v[0]
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

        if "lora loader prompt tags" in ct.lower() or ct == "LoraTagLoader":
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
        clip_id = _walk_to_clip(sinputs.get(pos_field), prompt)
        if clip_id:
            pos_text = _extract_text_from_clip_node(clip_id)

    neg_field = fmap.get("negative")
    if neg_field and isinstance(sinputs.get(neg_field), list):
        clip_id = _walk_to_clip(sinputs.get(neg_field), prompt)
        if clip_id:
            neg_text = _extract_text_from_clip_node(clip_id)

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
