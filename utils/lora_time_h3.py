import logging
import math
import re

import torch
import torch.nn.functional as F

import comfy.cli_args
import comfy.model_base
import comfy.patcher_extension
from comfy.weight_adapter.lora import LoRAAdapter

from .lora_time import _frame_rate, _sigma_ranges, _time_strength, _video_frame_spans


_KEY = "mnemic_h3_token_loras"


class _TimedBlock:
    def __init__(self, block, entries, previous):
        self.block = block
        self.entries = entries
        self.previous = previous
        self.factors = {}
        self.rows = {}
        self.applied = {}
        self.measurements = {}

    def _indices(self, layout, frames, strengths, count, device, dtype):
        start, end, _ = next(segment for segment in layout.segments if segment[2] == "video")
        if (end - start) % count:
            raise ValueError("H3 timed LoRA: video token layout does not match the latent timeline.")
        key = (start, end, frames, strengths, count, device, dtype)
        if key not in self.rows:
            per_frame = (end - start) // count
            indices = torch.tensor(frames, device=device, dtype=torch.long)[:, None] * per_frame
            rows = (start + indices + torch.arange(per_frame, device=device)).flatten()
            weights = torch.tensor(strengths, device=device, dtype=dtype).repeat_interleave(per_frame)[:, None]
            self.rows[key] = (rows, weights)
        return self.rows[key]

    def _contributions(self, source, layer, active, layout, row_offset=0):
        for index, (layers, strengths, frames, count, _) in active:
            if layer not in layers:
                continue
            up, down, scale = layers[layer]
            key = (index, layer, source.device, source.dtype)
            if key not in self.factors:
                self.factors[key] = (up.to(device=source.device, dtype=source.dtype),
                                     down.to(device=source.device, dtype=source.dtype))
            up, down = self.factors[key]
            indices, weights = self._indices(layout, frames, strengths, count, source.device, source.dtype)
            selected_rows = (indices >= row_offset) & (indices < row_offset + source.shape[0])
            indices, weights = indices[selected_rows], weights[selected_rows]
            if indices.numel() == 0:
                continue
            selected = source.index_select(0, indices - row_offset)
            if layer == "fc2":
                gate, expansion = selected.chunk(2, dim=-1)
                selected = F.silu(gate) * expansion
            delta = F.linear(F.linear(selected, down), up) * (weights * scale)
            if layer not in self.measurements:
                self.measurements[layer] = delta[:32].float().square().mean().sqrt()
            yield indices, delta

    def _add(self, source, output, layer, active, layout, row_offset=0):
        for indices, delta in self._contributions(source, layer, active, layout, row_offset):
            output = output.index_add(0, indices - row_offset, delta.to(output.dtype))
            self.applied[layer] = self.applied.get(layer, 0) + 1
        return output

    def __call__(self, args, extra):
        sigma = args["transformer_options"][_KEY + "_sigma"]
        active = [(index, entry) for index, entry in enumerate(self.entries)
                  if entry[2] and any(lower < sigma <= upper for upper, lower in entry[4])]
        original = self.previous if self.previous is not None else extra["original_block"]
        if not active:
            return original(args, extra) if self.previous is not None else original(args)
        layout = args["layout"]
        pending = []
        row_offset = [0]

        def fc1_hook(module, inputs, output):
            if output.ndim != 2 or row_offset[0] + output.shape[0] > layout.seq_len:
                raise ValueError("H3 timed LoRA: unexpected MLP token shape.")
            offset = row_offset[0]
            output = self._add(inputs[0], output, "fc1", active, layout, offset)
            pending.extend(self._contributions(output, "fc2", active, layout, offset))
            row_offset[0] += output.shape[0]
            return output

        def mlp_hook(module, inputs, output):
            if row_offset[0] != layout.seq_len:
                raise RuntimeError("H3 timed LoRA: the MLP input projection was bypassed.")
            for indices, delta in pending:
                output = output.index_add(0, indices, delta.to(output.dtype))
                self.applied["fc2"] = self.applied.get("fc2", 0) + 1
            pending.clear()
            return output

        handles = []
        try:
            handles.append(self.block.mlp.fc1.register_forward_hook(fc1_hook))
            handles.append(self.block.mlp.register_forward_hook(mlp_hook))
            return original(args, extra) if self.previous is not None else original(args)
        finally:
            for handle in reversed(handles):
                handle.remove()


class _TokenForward:
    def __init__(self, blocks):
        self.blocks = blocks
        self.replacements = {}
        self.verified = False
        self.calls = 0

    def __call__(self, executor, x, timestep, context, transformer_options=None, **kwargs):
        self.calls += 1
        options = dict(transformer_options or {})
        patches = dict(options.get("patches_replace", {}))
        dit = dict(patches.get("dit", {}))
        patches["dit"] = dit
        options["patches_replace"] = patches
        sigma = float(options["sigmas"][0])
        options[_KEY + "_sigma"] = sigma
        expected = []
        for index, entries in self.blocks.items():
            key = ("double_block", index)
            previous = dit.get(key)
            block = executor.class_obj.blocks[index]
            cache_key = (index, id(block), id(previous))
            if cache_key not in self.replacements:
                self.replacements[cache_key] = _TimedBlock(block, entries, previous)
            replacement = self.replacements[cache_key]
            dit[key] = replacement
            layers = {layer for entry in entries
                      if any(lower < sigma <= upper for upper, lower in entry[4])
                      for layer in entry[0]}
            expected.extend((index, replacement, layer, replacement.applied.get(layer, 0)) for layer in layers)
        result = executor(x, timestep, context, options, **kwargs)
        missed = [(index, layer) for index, replacement, layer, count in expected
                  if replacement.applied.get(layer, 0) == count]
        if missed:
            raise RuntimeError(f"H3 timed LoRA was bypassed by the active model forward: {missed}.")
        if expected and not self.verified:
            measurements = torch.stack([replacement.measurements[layer] for _, replacement, layer, _ in expected])
            peak = float(measurements.max())
            if not math.isfinite(peak) or peak == 0:
                raise RuntimeError(f"H3 timed LoRA produced an invalid or zero contribution (sampled RMS {peak}).")
            logging.info("LoraTagLoader: H3 timed LoRA executed in %d blocks / %d MLP projections; peak sampled contribution RMS %.6g.",
                         len({index for index, _, _, _ in expected}), len(expected), peak)
            self.verified = True
        return result


class _TokenSampling:
    def __init__(self, entries):
        self.entries = entries

    def __call__(self, executor, noise, latent_image, sampler, sigmas,
                 denoise_mask=None, callback=None, disable_pbar=False, seed=None, **kwargs):
        guider = executor.class_obj
        shapes = kwargs.get("latent_shapes") or [tuple(latent_image.shape)]
        shape = shapes[0]
        if len(shape) != 5 or shape[2] < 1:
            raise ValueError("H3 timed LoRA requires a video latent timeline.")
        if (len(shapes) > 1 and denoise_mask is not None and denoise_mask.ndim == 3
                and not torch.count_nonzero(denoise_mask[..., :math.prod(shape[1:])])):
            return executor(noise, latent_image, sampler, sigmas, denoise_mask,
                            callback, disable_pbar, seed, **kwargs)
        spans, fallback = _video_frame_spans(guider.model_patcher.model, shape[2])
        fps = _frame_rate(guider.conds, fallback, self.entries)
        blocks = {}
        for patches, strength, options, steps in self.entries:
            profile = tuple((i, _time_strength(options, (a + b) / (2 * fps), strength))
                            for i, (a, b) in enumerate(spans))
            selected = tuple((i, value) for i, value in profile if value is not None and value != 0)
            frames = tuple(i for i, _ in selected)
            strengths = tuple(value for _, value in selected)
            sigma_ranges = _sigma_ranges(steps, sigmas)
            if not frames or not sigma_ranges:
                continue
            for block_index, layers in patches.items():
                blocks.setdefault(block_index, []).append((layers, strengths, frames, shape[2], sigma_ranges))
            logging.info("LoraTagLoader: H3 token LoRA strength %s, time windows %s: %d/%d video latent slices at %.3f fps.",
                         options.get("blend") if options.get("blend") is not None else strength,
                         options["ranges"], len(frames), shape[2], fps)
        if not blocks:
            return executor(noise, latent_image, sampler, sigmas, denoise_mask,
                            callback, disable_pbar, seed, **kwargs)
        transformer = guider.model_options["transformer_options"]
        wrappers = transformer.setdefault("wrappers", {}).setdefault(comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL, {})
        previous = wrappers.get(_KEY)
        forward = _TokenForward(blocks)
        wrappers[_KEY] = [forward]
        compiler = comfy.cli_args.args.disable_comfy_compiler
        try:
            comfy.cli_args.args.disable_comfy_compiler = True
            result = executor(noise, latent_image, sampler, sigmas, denoise_mask,
                              callback, disable_pbar, seed, **kwargs)
            if len(sigmas) > 1 and not forward.verified:
                raise RuntimeError(f"H3 timed LoRA did not execute: diffusion forward calls={forward.calls}.")
            return result
        finally:
            comfy.cli_args.args.disable_comfy_compiler = compiler
            if previous is None:
                wrappers.pop(_KEY, None)
            else:
                wrappers[_KEY] = previous


def add_h3_timed_lora(model, patches, strength, step_ranges, time_options):
    h3_type = getattr(comfy.model_base, "MiniMaxH3", None)
    if h3_type is None or not isinstance(model.model, h3_type) or not patches:
        return False
    blocks = {}
    for key, adapter in patches.items():
        match = re.fullmatch(r"diffusion_model\.blocks\.([0-9]+)\.mlp\.(fc[12])\.weight", key) if isinstance(key, str) else None
        if match is None or not isinstance(adapter, LoRAAdapter):
            return False
        up, down, alpha, mid, dora, reshape = adapter.weights
        if up.ndim != 2 or down.ndim != 2 or mid is not None or dora is not None or reshape is not None:
            return False
        index, layer = int(match[1]), match[2]
        linear = getattr(model.model.diffusion_model.blocks[index].mlp, layer)
        if tuple(linear.weight.shape) != (up.shape[0], down.shape[1]) or up.shape[1] != down.shape[0]:
            return False
        scale = float(alpha) / down.shape[0] if alpha is not None else 1.0
        blocks.setdefault(index, {})[layer] = (up, down, scale)
    entries = tuple(model.get_attachment(_KEY) or ()) + ((blocks, strength, time_options, step_ranges),)
    model.set_attachments(_KEY, entries)
    model.remove_wrappers_with_key(comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, _KEY)
    model.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, _KEY, _TokenSampling(entries))
    return True
