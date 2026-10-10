"""Preserve Anima's per-prompt token preprocessing before batched denoising."""

from contextlib import nullcontext

import torch
import torch.nn.functional as F

import comfy.model_base


PROMPTS_KEY = "mnemic_anima_prompts"


class _AnimaBatchConditioning:
    def __init__(self, base_model, original, lora_state):
        self.base_model = base_model
        self.original = original
        self.lora_state = lora_state

    def __call__(self, **kwargs):
        prompts = kwargs.pop(PROMPTS_KEY, None)
        if prompts is None:
            return self.original(**kwargs)
        if kwargs["noise"].shape[0] != len(prompts):
            raise ValueError("Anima batch conditioning must be used with its original latent batch size and order.")
        device = kwargs["device"]
        dtype = self.base_model.get_dtype_inference()
        contexts = []
        # Do this after ComfyUI loads/patches the model, just where native
        # Anima.extra_conds does it. Padding Qwen embeddings before the adapter
        # would change its attention; preprocess the original lengths first.
        for index, (embedding, ids, weights) in enumerate(prompts):
            scope = self.lora_state.image(index) if self.lora_state is not None else nullcontext()
            with scope:
                context = self.base_model.diffusion_model.preprocess_text_embeds(
                    embedding.to(device=device, dtype=dtype),
                    ids.unsqueeze(0).to(device=device),
                    t5xxl_weights=weights.unsqueeze(0).unsqueeze(-1).to(device=device, dtype=dtype),
                )
            contexts.append(context)
        length = max(context.shape[1] for context in contexts)
        kwargs["cross_attn"] = torch.cat([
            F.pad(context, (0, 0, 0, length - context.shape[1])) for context in contexts
        ])
        # These have now been consumed; the original extra_conds must not
        # preprocess the combined embeddings a second time.
        kwargs.pop("t5xxl_ids", None)
        kwargs.pop("t5xxl_weights", None)
        return self.original(**kwargs)


def enable_anima_batching(model):
    anima_type = getattr(comfy.model_base, "Anima", None)
    if anima_type is None or not isinstance(model.model, anima_type):
        return model
    model = model.clone()
    model.add_object_patch("extra_conds", _AnimaBatchConditioning(
        model.model, model.get_model_object("extra_conds"),
        model.attachments.get("mnemic_batch_loras"),
    ))
    return model
