"""Model-local compatibility for native weight hooks on quantized operations."""

from functools import lru_cache
import logging

import torch

import comfy.hooks
import comfy.lora
import comfy.model_management
import comfy.model_patcher
import comfy.utils
from comfy.quant_ops import QuantizedTensor


class _QuantizedHookSupport:
    def pin_weight_to_device(self, key):
        # Native hooks require a regular patcher. When a later pass loads a
        # different model branch, that patcher may offload many CPU weights.
        # Pinning is optional; retrying a refused registration on every weight
        # can flood the log and repeatedly synchronize CUDA during the switch.
        if getattr(self, "_mnemic_pin_unavailable", False) or key in self.pinned:
            return
        weight, _, _ = comfy.model_patcher.get_key_weight(self.model, key)
        management = comfy.model_management
        if (management.MAX_PINNED_MEMORY <= 0
                or type(weight).__name__ not in management.PINNING_ALLOWED_TYPES
                or not management.is_device_cpu(weight.device)
                or weight.is_pinned()
                or not weight.is_contiguous()
                or weight.data_ptr() == 0):
            return
        if management.pin_memory(weight):
            self.pinned.add(key)
        else:
            # This also covers an exhausted pin budget. Keep existing pinned
            # weights tracked so the native unpin path can release them later.
            # A fresh patcher clone can attempt pinning again.
            self._mnemic_pin_unavailable = True
            logging.warning(
                "LoraTagLoader: CPU weight pinning unavailable for this hook-enabled model; "
                "using unpinned CPU offload for subsequent weights. GPU sampling remains enabled. "
                "CPU/GPU transfers may be slower.")

    def get_key_patches(self, filter_prefix=None):
        # Quantized state_dict() expands a weight into serialized data, scales,
        # and comfy_quant metadata. These are not all attributes of the module.
        # Hooks need resident parameters/buffers, including the QuantizedTensor
        # itself, rather than its serialized pieces.
        with self.use_ejected():
            keys = dict(self.model.named_parameters(remove_duplicate=False))
            keys.update(dict(self.model.named_buffers(remove_duplicate=False)))
            patches = {}
            for key in keys:
                if filter_prefix is not None and not key.startswith(filter_prefix):
                    continue
                weight, _, convert = comfy.model_patcher.get_key_weight(self.model, key)
                if not isinstance(weight, torch.Tensor):
                    continue
                backup = self.backup.get(key)
                hook_backup = self.hook_backup.get(key)
                if backup is not None:
                    weight = backup.weight
                if hook_backup is not None:
                    weight = hook_backup[0]
                if convert is None:
                    convert = lambda value, **kwargs: value
                patches[key] = [(weight, convert)] + self.patches.get(key, [])
            return patches

    def _backup_hook_weight(self, key, weight, memory_counter):
        if key not in self.hook_backup:
            device = self.offload_device
            if self.hook_mode == comfy.hooks.EnumHookMode.MaxSpeed and memory_counter.use(weight):
                device = weight.device
            self.hook_backup[key] = (weight.to(device=device, copy=True), weight.device)

    def patch_hook_weight_to_device(self, hooks, combined_patches, key,
                                    original_weights, memory_counter):
        weight, set_func, convert = comfy.model_patcher.get_key_weight(self.model, key)
        if not isinstance(weight, QuantizedTensor) and set_func is None:
            return super().patch_hook_weight_to_device(
                hooks, combined_patches, key, original_weights, memory_counter)
        if key not in combined_patches:
            return
        self._backup_hook_weight(key, weight, memory_counter)
        # Dequantize before casting: a QuantizedTensor's dtype describes its
        # logical compute type, not the packed storage. Work on a fresh tensor.
        if convert is not None:
            temporary = convert(weight, inplace=False)
        elif isinstance(weight, QuantizedTensor):
            temporary = weight.dequantize()
        else:
            temporary = weight
        temporary = comfy.model_management.cast_to_device(temporary, weight.device, torch.float32, copy=True)
        patched = comfy.lora.calculate_weight(combined_patches[key], temporary, key,
                                              original_weights=original_weights)
        del original_weights[key]
        # The native hook path requests inplace_update=True, which quantized
        # Linear.set_weight explicitly rejects. Obtain a requantized result and
        # replace the parameter; cache the packed result with its new scales.
        if set_func is None:
            raise TypeError(f"Quantized LoRA hook requires a weight setter: {key}")
        stored = set_func(patched, inplace_update=False, return_weight=True,
                          seed=comfy.utils.string_to_seed(key))
        comfy.utils.set_attr_param(self.model, key, stored)
        if self.hook_mode == comfy.hooks.EnumHookMode.MaxSpeed:
            device = weight.device if memory_counter.use(stored) else self.offload_device
            # Unpatching copies the base weight into the resident parameter.
            # A cache sharing that parameter's storage would become base too.
            self.cached_hook_patches.setdefault(hooks, {})[key] = (stored.to(device=device, copy=True), weight.device)

    # Native cache application/unpatching can now use QuantizedTensor.copy_,
    # which restores both packed data and layout parameters (including scales).
    # Keeping packed tensors in the cache is essential: float predictions of
    # the patched weights cannot be copied back into a QuantizedTensor.


@lru_cache(maxsize=None)
def _compatible_patcher_type(base):
    # ModelPatcher.clone constructs self.__class__, so support follows clones
    # without changing global ComfyUI classes or rebinding instance methods.
    return type(f"MnemicQuantized{base.__name__}", (_QuantizedHookSupport, base), {})


def enable_quantized_hooks(model):
    if isinstance(model, _QuantizedHookSupport):
        return
    if any(isinstance(getattr(module, "weight", None), QuantizedTensor)
           or callable(getattr(module, "set_weight", None))
           for module in model.model.modules()):
        model.__class__ = _compatible_patcher_type(type(model))
