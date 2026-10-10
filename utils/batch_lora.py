"""
Per-image LoRAs inside one batched sampler call.

Merged LoRA weights are shared by every image in a batch, so LoRAs that differ
between images are applied in bypass form instead: each patched layer returns
base(x) + strength[row] * delta(x), where delta is the adapter's own bypass
term from comfy.weight_adapter and strength holds one value per batch row. For
LoRA, LoHa and LoKr adapters (and plain weight/bias diffs) this is the same math
as merging the weights, just evaluated per image.
"""

import uuid
from contextlib import contextmanager

import torch
import torch.nn.functional as F

import comfy.patcher_extension
import comfy.utils
from comfy.patcher_extension import PatcherInjection
from comfy.weight_adapter.bypass import get_module_type_info
from comfy.weight_adapter.lora import LoRAAdapter
from comfy.weight_adapter.loha import LoHaAdapter
from comfy.weight_adapter.lokr import LoKrAdapter

_KEY = "mnemic_batch_loras"

# Index of the DoRA scale in each supported adapter's weights. DoRA renormalizes
# the merged weight, so it has no per-row additive form.
_DORA_INDEX = {LoRAAdapter: 4, LoHaAdapter: 7, LoKrAdapter: 8}

_CONV_OPS = (None, F.conv1d, F.conv2d, F.conv3d)


class _BatchLoraState:
    """Per-slot strengths for every batch image, expanded to the rows a layer sees."""

    def __init__(self, strengths, ranges, batch_size):
        self.strengths = strengths
        self.ranges = ranges
        self.batch_size = batch_size
        self.model_rows = batch_size
        self.active = (True,) * len(strengths)
        self.scales = {}
        self.image_index = None

    @contextmanager
    def image(self, index):
        """Route model-side text preprocessing to this image's adapters."""
        previous = self.model_rows, self.image_index, self.scales, self.active
        self.model_rows, self.image_index, self.scales = 1, index, {}
        # As with native scheduled weight hooks, step-only patches are not
        # baked into preprocessing that runs before the denoising schedule.
        self.active = tuple(ranges is None for ranges in self.ranges)
        try:
            yield
        finally:
            self.model_rows, self.image_index, self.scales, self.active = previous

    def __call__(self, executor, x, t, c_concat, c_crossattn, control, transformer_options, **kwargs):
        # The sampler stacks the latent batch once per cond/uncond chunk, so model
        # row r belongs to image r % batch_size.
        self.model_rows = x.shape[0]
        if self.model_rows % self.batch_size:
            raise ValueError("Batch LoRA model must be used with its original latent batch size and order.")
        self.scales = {}
        if any(ranges is not None for ranges in self.ranges):
            from .lora_time import _sigma_ranges
            sigmas = transformer_options["sample_sigmas"].tolist()
            sigma = float(t[0])
            self.active = tuple(
                ranges is None or any(lower < sigma <= upper for upper, lower in _sigma_ranges(ranges, sigmas))
                for ranges in self.ranges
            )
        try:
            return executor(x, t, c_concat, c_crossattn, control, transformer_options, **kwargs)
        finally:
            self.model_rows = self.batch_size
            self.active = (True,) * len(self.strengths)
            self.scales = {}

    def row_scales(self, out):
        """Return a [slots, rows] strength tensor for a layer output of out.shape[0] rows."""
        rows = out.shape[0]
        key = (rows, out.dtype, out.device)
        scales = self.scales.get(key)
        if scales is None:
            if rows % self.model_rows != 0:
                raise RuntimeError(f"Batch LoRA: a layer saw {rows} rows, which does not match the model batch of {self.model_rows}.")
            images = ([self.image_index] if self.image_index is not None
                      else [r % self.batch_size for r in range(self.model_rows)])
            scales = torch.tensor(
                [[strengths[i] if active else 0.0 for i in images] for strengths, active in zip(self.strengths, self.active)],
                dtype=out.dtype, device=out.device,
            )
            # Layers that flatten tokens into the batch dimension see each model row repeated.
            if rows != self.model_rows:
                scales = scales.repeat_interleave(rows // self.model_rows, dim=1)
            self.scales[key] = scales
        return scales

    def sample(self, executor, noise, latent_image, sampler, sigmas,
               denoise_mask=None, callback=None, disable_pbar=False, seed=None, **kwargs):
        if latent_image.shape[0] != self.batch_size:
            raise ValueError("Batch LoRA model must be used with its original latent batch size and order.")
        return executor(noise, latent_image, sampler, sigmas, denoise_mask,
                        callback, disable_pbar, seed, **kwargs)


class _BatchLoraLayer:
    """Replaces one module's forward with base output plus per-row LoRA deltas."""

    def __init__(self, module, state, entries):
        self.module = module
        self.state = state
        # (slot, kind, patch, offset); kind is "adapter", "weight" (diff) or "bias" (diff).
        self.entries = entries
        info = get_module_type_info(module)
        self.conv_dim = info["conv_dim"]
        self.kw_dict = {k: info[k] for k in ("stride", "padding", "dilation", "groups")} if info["is_conv"] else {}
        for _, kind, patch, _ in entries:
            if kind == "adapter":
                patch.multiplier = 1.0
                patch.is_conv = info["is_conv"]
                patch.conv_dim = info["conv_dim"]
                patch.kernel_size = info["kernel_size"]
                patch.in_channels = info["in_channels"]
                patch.out_channels = info["out_channels"]
                patch.kw_dict = self.kw_dict
        self.offloaded = None
        self.original_forward = None

    def inject(self, device):
        # Clones of the model share these layers, so only one can be injected at a time.
        if self.original_forward is not None:
            return
        # LoRA weights live on the compute device only while the model is loaded.
        dtype = self.module.weight.dtype
        if dtype not in (torch.float32, torch.float16, torch.bfloat16):
            dtype = None
        self.offloaded = [patch.weights if kind == "adapter" else patch for _, kind, patch, _ in self.entries]
        self.original_forward = self.module.forward
        for index, (slot, kind, patch, offset) in enumerate(self.entries):
            if kind == "adapter":
                patch.weights = tuple(w.to(device=device, dtype=dtype) if torch.is_tensor(w) else w for w in patch.weights)
            else:
                self.entries[index] = (slot, kind, patch.to(device=device, dtype=dtype), offset)
        self.module.forward = self.forward

    def eject(self):
        if self.original_forward is None:
            return
        self.module.forward = self.original_forward
        self.original_forward = None
        for index, ((slot, kind, patch, offset), offloaded) in enumerate(zip(self.entries, self.offloaded)):
            if kind == "adapter":
                patch.weights = offloaded
            else:
                self.entries[index] = (slot, kind, offloaded, offset)
        self.offloaded = None

    def forward(self, x, *args, **kwargs):
        # Some operations return views; never modify their backing storage.
        out = self.original_forward(x, *args, **kwargs).clone()
        scales = self.state.row_scales(out)
        # Linear outputs keep features last, conv outputs keep channels in dim 1.
        feature_dim = 1 if self.conv_dim else -1
        for slot, kind, patch, offset in self.entries:
            if not self.state.active[slot]:
                continue
            target = out if offset is None else out.narrow(feature_dim, offset[1], offset[2])
            if kind == "adapter":
                delta = patch.h(x, target)
            elif kind == "weight":
                weight = patch.to(dtype=x.dtype)
                delta = F.linear(x, weight) if not self.conv_dim else _CONV_OPS[self.conv_dim](x, weight, **self.kw_dict)
            else:
                delta = patch.to(dtype=out.dtype)
                if self.conv_dim:
                    delta = delta.view(-1, *([1] * self.conv_dim))
            scale = scales[slot].view(-1, *([1] * (target.ndim - 1)))
            # An adapter absent from a row must not contaminate it, even if its
            # delta overflows on that image (NaN * 0 is still NaN).
            target.add_(torch.where(scale != 0, delta * scale, 0))
        return out


def _patch_kind(name, module, param, patch, offset):
    """Classify a loaded LoRA patch, or raise when it has no per-image bypass form."""
    is_layer = isinstance(module, torch.nn.Linear) or get_module_type_info(module)["is_conv"]
    if is_layer and param in ("weight", "bias") and (offset is None or offset[0] == 0):
        if param == "weight" and type(patch) in _DORA_INDEX and patch.weights[_DORA_INDEX[type(patch)]] is None:
            if type(patch) is not LoRAAdapter or patch.weights[5] is None:
                return "adapter"
        if isinstance(patch, tuple) and patch[0] == "diff":
            return "weight" if param == "weight" else "bias"
    raise ValueError(
        f"LoRA '{name}' patches {type(module).__name__} layers with a format that can't differ per image "
        f"in one batch (e.g. DoRA, OFT or norm weights). Put it in the identical leading tags of every prompt to merge it instead."
    )


def add_batch_loras(model, slots, batch_size):
    """
    Return a clone of model that applies LoRAs per batch image in bypass form.

    slots: list of (name, model_patches, ranges, strengths). Patches have already
    been resolved with the combined model/CLIP key map. strengths holds one
    model strength per batch index (0.0 for images without that LoRA); ranges are
    inclusive sampling-step ranges, or None to apply at every step.
    """
    if any(key.startswith(_KEY) or key == "bypass_lora" for key in model.injections):
        raise ValueError("Batch LoRA: use a base model without existing bypass LoRA injections.")
    state = _BatchLoraState([s[3] for s in slots], [s[2] for s in slots], batch_size)
    entries = {}
    for slot, (name, patches, _, _) in enumerate(slots):
        for key, patch in patches.items():
            weight_key, offset = (key, None) if isinstance(key, str) else (key[0], key[1])
            if not isinstance(key, str) and len(key) > 2:
                raise ValueError(f"LoRA '{name}' uses patch functions, which can't differ per image in one batch.")
            module_key, param = weight_key.rsplit(".", 1)
            module = comfy.utils.get_attr(model.model, module_key)
            kind = _patch_kind(name, module, param, patch, offset)
            entries.setdefault(module_key, (module, []))[1].append((slot, kind, patch if kind == "adapter" else patch[1][0], offset))

    layers = [_BatchLoraLayer(module, state, layer_entries) for module, layer_entries in entries.values()]

    def inject(model_patcher):
        try:
            for layer in layers:
                layer.inject(model_patcher.load_device)
        except Exception:
            for layer in reversed(layers):
                layer.eject()
            raise

    def eject(model_patcher):
        for layer in layers:
            layer.eject()

    model = model.clone()
    model.set_attachments(_KEY, state)
    # Patcher clone comparisons check injection keys, not their contents. A new
    # batch needs a distinct key so re-queueing cannot reuse the previous rows.
    key = f"{_KEY}_{uuid.uuid4().hex}"
    model.set_injections(key, [PatcherInjection(inject=inject, eject=eject)])
    model.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.APPLY_MODEL, key, state)
    model.add_wrapper_with_key(comfy.patcher_extension.WrappersMP.OUTER_SAMPLE, key, state.sample)
    return model
