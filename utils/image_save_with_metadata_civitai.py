"""
Source reference:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
Adapted into ComfyUI-mnemic-nodes for the "Image Save With Metadata" node.
"""


def civitai_embedding_key_name(embedding: str) -> str:
    return f"embed:{embedding}"


def civitai_lora_key_name(lora: str) -> str:
    return f"LORA:{lora}"


CIVITAI_SAMPLER_MAP = {
    "euler_ancestral": "Euler a",
    "euler": "Euler",
    "lms": "LMS",
    "heun": "Heun",
    "dpm_2": "DPM2",
    "dpm_2_ancestral": "DPM2 a",
    "dpmpp_2s_ancestral": "DPM++ 2S a",
    "dpmpp_2m": "DPM++ 2M",
    "dpmpp_sde": "DPM++ SDE",
    "dpmpp_2m_sde": "DPM++ 2M SDE",
    "dpmpp_3m_sde": "DPM++ 3M SDE",
    "dpm_fast": "DPM fast",
    "dpm_adaptive": "DPM adaptive",
    "ddim": "DDIM",
    "plms": "PLMS",
    "uni_pc_bh2": "UniPC",
    "uni_pc": "UniPC",
    "lcm": "LCM",
}


def get_civitai_sampler_name(sampler_name: str, scheduler: str) -> str:
    if sampler_name in CIVITAI_SAMPLER_MAP:
        civitai_name = CIVITAI_SAMPLER_MAP[sampler_name]
        if scheduler == "karras":
            civitai_name += " Karras"
        elif scheduler == "exponential":
            civitai_name += " Exponential"
        return civitai_name
    if scheduler != "normal":
        return f"{sampler_name}_{scheduler}"
    return sampler_name


