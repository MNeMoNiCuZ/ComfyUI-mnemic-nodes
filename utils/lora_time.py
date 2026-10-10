"""Opt-in video prediction blending for LoRA prompt tags.

Imported only for time= tags. Uses native weight hooks and guider wrappers;
never changes ComfyUI's process-wide sampler or model methods.
"""

import logging
import math
import re

import torch

import comfy.hooks
import comfy.model_base
import comfy.patcher_extension


_KEY = "mnemic_timed_loras"
_NUMBER = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
_WEIGHT = rf"-?{_NUMBER}"


def parse_time_options(parts, name):
    remaining = []
    options = {}
    for part in parts:
        key, separator, value = part.partition("=")
        key = key.strip()
        if not separator or key not in ("time", "fps", "blend"):
            remaining.append(part)
            continue
        if key in options:
            raise ValueError(f"LoRA '{name}': repeated option '{key}'.")
        options[key] = value.strip()
    if "time" not in options:
        raise ValueError(f"LoRA '{name}': fps= and blend= require time=.")
    ranges = []
    for item in options["time"].split(","):
        match = re.fullmatch(rf"\s*({_NUMBER})\s*-\s*({_NUMBER})\s*", item)
        if match is None:
            raise ValueError(f"LoRA '{name}': use time=0-2 or time=0-2,4-6 (seconds).")
        start, end = float(match[1]), float(match[2])
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            raise ValueError(f"LoRA '{name}': time windows require finite seconds with 0 <= start < end.")
        ranges.append((start, end))
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    fps = None
    if "fps" in options:
        try:
            fps = float(options["fps"])
        except ValueError:
            raise ValueError(f"LoRA '{name}': fps must be a positive finite frame rate.") from None
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError(f"LoRA '{name}': fps must be a positive finite frame rate.")
    blend = None
    if "blend" in options:
        match = re.fullmatch(rf"\s*({_WEIGHT})\s*-\s*({_WEIGHT})\s*", options["blend"])
        if match is None:
            raise ValueError(f"LoRA '{name}': use blend=0.5-2 or blend=-8-8 (start/end model weights).")
        blend = (float(match[1]), float(match[2]))
        if not all(math.isfinite(value) for value in blend):
            raise ValueError(f"LoRA '{name}': blend weights must be finite.")
        if len(ranges) != 1:
            raise ValueError(f"LoRA '{name}': blend= requires one time window per tag; use separate tags for separate ramps.")
    return remaining, {"ranges": tuple(merged), "fps": fps, "blend": blend}


def _time_fraction(options, seconds):
    for start, end in options["ranges"]:
        if start <= seconds < end:
            return (seconds - start) / (end - start)
    return None


def _time_strength(options, seconds, constant):
    fraction = _time_fraction(options, seconds)
    if fraction is None:
        return None
    blend = options.get("blend")
    if blend is None:
        return constant
    return (1 - fraction) * blend[0] + fraction * blend[1]


def _video_frame_spans(model, count):
    """Decoded frame intervals represented by each temporal latent slice."""
    h3_type = getattr(comfy.model_base, "MiniMaxH3", None)
    if h3_type is not None and isinstance(model, h3_type):
        # Native H3 FRAME_PER_TOKEN / 17-frame VAE chunks. A uniform stride of
        # four is incorrect because every fifth token represents just one frame.
        start = 0
        spans = []
        for index in range(count):
            end = start + (1 if index % 5 == 0 else 4)
            spans.append((start, end))
            start = end
        return spans, 24.0
    ltx_types = tuple(getattr(comfy.model_base, name) for name in ("LTXV", "LTXAV")
                      if hasattr(comfy.model_base, name))
    if isinstance(model, ltx_types):
        # LTX's causal VAE: first slice is one frame; subsequent slices are
        # temporal_downscale_ratio frames (eight for LTX 2.3/2.5).
        stride = model.latent_format.temporal_downscale_ratio
        return [(0, 1)] + [(1 + (i - 1) * stride, 1 + i * stride)
                          for i in range(1, count)], 25.0
    raise ValueError("LoRA time= currently supports native LTXV/LTXAV and MiniMax H3 models only.")


def _frame_rate(conds, fallback, entries):
    overrides = {entry[2]["fps"] for entry in entries if entry[2]["fps"] is not None}
    if len(overrides) > 1:
        raise ValueError("All time= tags on a video must use the same fps= value.")
    if overrides:
        return overrides.pop()
    rates = {float(cond[key]) for group in conds.values() for cond in group
             for key in ("frame_rate", "fps") if cond.get(key) is not None}
    if len(rates) > 1:
        raise ValueError("LoRA time= found conflicting conditioning frame rates; specify fps= on the timed tag.")
    fps = rates.pop() if rates else fallback
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("LoRA time= requires a positive finite video frame rate.")
    return fps


def _sigma_ranges(ranges, sigmas):
    if ranges is None:
        return ((float("inf"), -float("inf")),)
    count = len(sigmas) - 1
    return tuple((float("inf") if start == 1 else float(sigmas[start - 1]),
                  float(sigmas[end]) if end is not None and end < count else -float("inf"))
                 for start, end in ranges if start <= count)


class _TimePrediction:
    def __init__(self, entries, frame_sets, shape, shapes, sigma_ranges):
        self.entries = entries
        self.frame_sets = frame_sets
        self.shape = shape
        self.shapes = shapes
        self.sigma_ranges = sigma_ranges
        self.source_conds = None
        self.cond_cache = {}
        self.mask_cache = {}

    def _conds(self, source, active):
        if source is not self.source_conds:
            self.source_conds = source
            self.cond_cache.clear()
        if active not in self.cond_cache:
            added = comfy.hooks.HookGroup()
            for index in active:
                added.add(self.entries[index][0])
            groups = {}

            def combine(cond):
                existing = cond.get("hooks")
                if existing not in groups:
                    groups[existing] = added.clone_and_combine(existing)
                return dict(cond, hooks=groups[existing])

            self.cond_cache[active] = {key: [combine(cond) for cond in group]
                                       for key, group in source.items()} if active else source
        return self.cond_cache[active]

    def _mask(self, frames, include_audio, x):
        cache_key = (tuple(frames), include_audio, x.device, x.dtype)
        if cache_key not in self.mask_cache:
            # Build a broadcast mask for video-only latents. Packed AV latents
            # need channel/spatial repeats matching comfy.utils.pack_latents.
            video = x.new_zeros((1, 1, self.shape[2], 1, 1), dtype=torch.bool)
            video[:, :, frames] = 1
            if x.ndim == 3:
                video = video.expand((1,) + tuple(self.shape[1:])).reshape(1, 1, -1)
                other_size = sum(math.prod(shape[1:]) for shape in self.shapes[1:])
                other = x.new_full((1, 1, other_size), include_audio, dtype=torch.bool)
                video = torch.cat((video, other), dim=-1)
            self.mask_cache[cache_key] = video
        return self.mask_cache[cache_key]

    def __call__(self, executor, x, timestep, model_options=None, seed=None):
        guider = executor.class_obj
        source = guider.conds
        sigma = float(timestep[0])
        eligible = {index for index, ranges in enumerate(self.sigma_ranges)
                    if any(lower < sigma <= upper for upper, lower in ranges)}
        partitions = {}
        for active, frames in self.frame_sets.items():
            effective = tuple(index for index in active if index in eligible)
            partitions.setdefault(effective, []).extend(frames)
        # Audio always uses the prediction without timed LoRAs. Keep ordinary
        # LoRAs, step hooks, conditioning, guidance, and original wrappers.
        if len(self.shapes) > 1:
            partitions.setdefault((), [])
        output = None
        try:
            for active, frames in partitions.items():
                guider.conds = self._conds(source, active)
                prediction = executor(x, timestep, model_options, seed)
                if len(partitions) == 1:
                    return prediction  # All streams use this state; no mask needed.
                mask = self._mask(frames, not active, prediction)
                # Hard temporal selection avoids multiplying an unselected
                # branch by zero (which would still propagate NaNs from it).
                if output is None:
                    output = torch.zeros_like(prediction)
                output = torch.where(mask, prediction, output)
            return output
        finally:
            guider.conds = source


def _blend_states(entries, spans, fps):
    runtime = []
    indices = {}
    endpoints = []
    for hook, steps, options in entries:
        hooks = options["endpoints"] if options.get("blend") is not None else (hook,)
        choices = []
        for endpoint in hooks:
            if endpoint is None:
                choices.append(None)
                continue
            if endpoint not in indices:
                indices[endpoint] = len(runtime)
                runtime.append((endpoint.clone(), steps, options))
            choices.append(indices[endpoint])
        endpoints.append(tuple(choices))
    states = {}
    for frame, (start, end) in enumerate(spans):
        seconds = (start + end) / (2 * fps)
        combinations = {(): 1.0}
        for (_, _, options), choices in zip(entries, endpoints):
            fraction = _time_fraction(options, seconds)
            if fraction is None:
                continue
            weights = (1 - fraction, fraction) if options.get("blend") is not None else (1.0,)
            combined = {}
            for state, amount in combinations.items():
                for index, weight in zip(choices, weights):
                    if weight == 0:
                        continue
                    target = state if index is None else state + (index,)
                    combined[target] = combined.get(target, 0.0) + amount * weight
            combinations = combined
        for state, amount in combinations.items():
            states.setdefault(state, [0.0] * len(spans))[frame] = amount
    return tuple(runtime), states


class _BlendPrediction(_TimePrediction):
    def _mask(self, weights, include_audio, x):
        key = (tuple(weights), include_audio, x.device, x.dtype)
        if key not in self.mask_cache:
            video = x.new_tensor(weights).reshape(1, 1, self.shape[2], 1, 1)
            if x.ndim == 3:
                video = video.expand((1,) + tuple(self.shape[1:])).reshape(1, 1, -1)
                other_size = sum(math.prod(shape[1:]) for shape in self.shapes[1:])
                other = x.new_full((1, 1, other_size), float(include_audio))
                video = torch.cat((video, other), dim=-1)
            self.mask_cache[key] = video
        return self.mask_cache[key]

    def __call__(self, executor, x, timestep, model_options=None, seed=None):
        guider = executor.class_obj
        source = guider.conds
        sigma = float(timestep[0])
        eligible = {index for index, ranges in enumerate(self.sigma_ranges)
                    if any(lower < sigma <= upper for upper, lower in ranges)}
        partitions = {}
        for active, weights in self.frame_sets.items():
            effective = tuple(index for index in active if index in eligible)
            target = partitions.setdefault(effective, [0.0] * self.shape[2])
            for frame, weight in enumerate(weights):
                target[frame] += weight
        if len(self.shapes) > 1:
            partitions.setdefault((), [0.0] * self.shape[2])
        output = None
        try:
            for active, weights in partitions.items():
                guider.conds = self._conds(source, active)
                prediction = executor(x, timestep, model_options, seed)
                if len(partitions) == 1:
                    return prediction
                mask = self._mask(weights, not active, prediction)
                if output is None:
                    output = torch.zeros_like(prediction)
                output.add_(torch.where(mask != 0, prediction, 0) * mask)
            return output
        finally:
            guider.conds = source


class _TimeSampling:
    def __init__(self, entries):
        self.entries = entries

    def __call__(self, executor, noise, latent_image, sampler, sigmas,
                 denoise_mask=None, callback=None, disable_pbar=False, seed=None, **kwargs):
        guider = executor.class_obj
        shapes = kwargs.get("latent_shapes") or [tuple(latent_image.shape)]
        shape = shapes[0]
        if len(shape) != 5 or shape[2] < 1:
            raise ValueError("LoRA time= requires a video latent [batch, channels, time, height, width], with video first in packed AV latents.")
        spans, fallback = _video_frame_spans(guider.model_patcher.model, shape[2])
        fps = _frame_rate(guider.conds, fallback, self.entries)
        has_blend = any(entry[2].get("blend") is not None for entry in self.entries)
        if has_blend:
            runtime_entries, frame_sets = _blend_states(self.entries, spans, fps)
        else:
            frame_sets = {}
            for index, (start, end) in enumerate(spans):
                seconds = (start + end) / (2 * fps)
                active = tuple(i for i, entry in enumerate(self.entries)
                               if _time_fraction(entry[2], seconds) is not None)
                frame_sets.setdefault(active, []).append(index)
            runtime_entries = tuple((hook.clone(), ranges, options) for hook, ranges, options in self.entries)
        registered = guider.model_options.get("registered_hooks")
        registered = registered.clone() if registered is not None else comfy.hooks.HookGroup()
        for hook, _, _ in runtime_entries:
            registered.add(hook)
        guider.model_options["registered_hooks"] = registered
        prediction_type = _BlendPrediction if has_blend else _TimePrediction
        prediction = prediction_type(runtime_entries, frame_sets, shape, shapes,
                                     tuple(_sigma_ranges(ranges, sigmas) for _, ranges, _ in runtime_entries))
        options = guider.model_options["transformer_options"]
        wrappers = options.setdefault("wrappers", {}).setdefault(comfy.patcher_extension.WrappersMP.PREDICT_NOISE, {})
        previous = wrappers.get(_KEY)
        wrappers[_KEY] = [prediction]
        mode = guider.model_patcher.hook_mode
        guider.model_patcher.hook_mode = comfy.hooks.EnumHookMode.MaxSpeed
        logging.info("LoraTagLoader: timed video prediction blending enabled at %.3f fps (%d temporal states); audio uses the base prediction.", fps, len(frame_sets))
        try:
            return executor(noise, latent_image, sampler, sigmas, denoise_mask,
                            callback, disable_pbar, seed, **kwargs)
        finally:
            guider.model_patcher.hook_mode = mode
            if previous is None:
                wrappers.pop(_KEY, None)
            else:
                wrappers[_KEY] = previous


def add_timed_lora(model, hook, step_ranges, time_options):
    # Fail before queueing expensive sampling for unsupported image/model types.
    _video_frame_spans(model.model, 1)
    if time_options.get("blend") is not None:
        endpoints = {}
        for strength in time_options["blend"]:
            if strength in endpoints:
                continue
            endpoint = None
            if strength != 0:
                endpoint = comfy.hooks.WeightHook(strength_model=strength, strength_clip=0.0)
                endpoint.weights = hook.weights
                endpoint.need_weight_init = False
                model.add_hook_patches(endpoint, endpoint.weights, strength_patch=strength)
            endpoints[strength] = endpoint
        time_options = dict(time_options, endpoints=tuple(endpoints[value] for value in time_options["blend"]))
    entries = tuple(model.get_attachment(_KEY) or ()) + ((hook, step_ranges, time_options),)
    model.set_attachments(_KEY, entries)
    model.remove_wrappers_with_key(comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, _KEY)
    model.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, _KEY, _TimeSampling(entries))
