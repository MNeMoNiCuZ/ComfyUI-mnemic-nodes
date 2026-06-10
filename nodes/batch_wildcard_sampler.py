"""
Batch Wildcard Sampler — per-batch-index prompt variation for ComfyUI.

The defining feature: wildcards are resolved independently for every image in the
batch, so a single run produces a different prompt (and therefore a different
image) per batch index. Each prompt is encoded through CLIP and sampled on its
own, then the results are combined into one output batch.

This works around ComfyUI's limitation where conditioning tensors must have
batch dim 1 — instead of stacking conditionings, we loop internally: resolve
wildcard -> encode CLIP -> sample with batch_size=1 -> collect.

Wildcard resolution is delegated to the WildcardProcessor so the full syntax
(file wildcards, glob patterns, inline choices, weighted choices, multiple
selections, ranged selections, variables, and nesting) is supported.

LoRAs can be loaded directly from <lora:name:strength> tags in the prompt — the
same mechanism as the LoRA Loader Prompt Tags node — so no separate loader is
needed. Tags are kept in the resolved prompt (for metadata) and stripped before
the text is sent to CLIP.
"""

import re

import torch

import comfy.sample
import comfy.samplers
import comfy.model_management

from .wildcard_processor import WildcardProcessor
from .lora_tag_loader import LoraTagLoader
from ..utils.batch_wildcard_runtime import set_batch_prompts


# Matches <lora:name:strength> tags so they can be stripped before CLIP encoding.
_LORA_TAG_RE = re.compile(r"<lora:[^>]+>", re.IGNORECASE)


# Shared wildcard-syntax help, appended to the positive prompt tooltip.
_WILDCARD_SYNTAX_HELP = (
    "File Wildcards:\nUse __filename__ to insert a random line from filename.txt in one of the supported wildcard directories. Lines starting with # are treated as comments and are ignored.\n\n"
    "Inline Choices:\nUse {a|b|c} to randomly choose between a, b, or c.\nExample Input: A photo of a {red|green|blue} car.\nExample Output: A photo of a green car.\n\n"
    "Weighted Choices:\nUse {5::black|green|red} to make black 5 times more likely to be chosen than green or red.\n\n"
    "Select Multiple Wildcards:\nUse {2$$a|b|c|d} to output a specific number of items from the result.\nExample Input: My favorite colors are {3$$red|green|blue|yellow|purple}.\nExample Output: My favorite colors are blue, yellow, purple.\n\n"
    "Ranged Select Multiple:\nUse {1-3$$red|green|blue|yellow|purple} to select a random number of 1-3 items within a range.\n\n"
    "Variables:\nDefine a variable to reuse a value. Can be defined directly, or using a wildcard\nExample Input: ${animal=!__animals__} The ${animal} is friends with the other ${animal}.\nExample Output: The cat is friends with the other cat.\n\n"
    "LoRAs:\nInclude <lora:name:strength> tags to load LoRAs automatically (no separate LoRA loader node needed).\nExample: <lora:mylora:0.75>\nThe best matching LoRA file is found by name. Strength is optional (defaults to 1.0); add a second value for a separate CLIP strength, e.g. <lora:mylora:0.8:0.6>. The tag stays in the resolved prompt for metadata and is removed before the text reaches CLIP."
)


# ---------------------------------------------------------------------------
# Node: Batch Wildcard Sampler
# ---------------------------------------------------------------------------

class BatchWildcardSampler:
    """
    Resolves a fresh set of wildcards for every image in the batch, then encodes
    and samples each one individually so a single run yields a different prompt
    per image. Wildcard resolution is delegated to the WildcardProcessor.
    """

    CATEGORY = "⚡ MNeMiC Nodes"
    FUNCTION = "generate_batch"
    RETURN_TYPES = ("LATENT", "STRING", "MODEL", "CLIP")
    RETURN_NAMES = ("latent", "resolved_prompts", "model", "clip")
    OUTPUT_TOOLTIPS = (
        "The combined batch of sampled latents (empty when sampling is skipped).",
        "The resolved positive prompt for each image, as a list with one entry per batch item.",
        "The model after LoRA patches from the last batch item have been applied.",
        "The CLIP after LoRA patches from the last batch item have been applied.",
    )
    OUTPUT_NODE = False

    DESCRIPTION = ("Resolves wildcards independently for every image in the batch, so a single run "
                   "produces a different prompt — and a different image — for each batch index. "
                   "LoRAs can be loaded per image via <lora:name:strength> tags in the prompt. "
                   "Connect model and clip to sample, or leave them off to just preview the resolved prompts.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text":          ("STRING", {
                    "multiline": True,
                    "dynamicPrompts": False,
                    "tooltip": (
                        "The positive prompt, with wildcard support. Wildcards are resolved independently for "
                        "each image in the batch, so every image in a single run gets a different result from "
                        "the same prompt.\n\n" + _WILDCARD_SYNTAX_HELP
                    ),
                    "placeholder": "A photo of a __sample_colors__ {dog|cat|monkey} <lora:mylora:0.75>"
                }),
                "negative":      ("STRING", {
                    "multiline": True,
                    "dynamicPrompts": False,
                    "tooltip": (
                        "The negative prompt. Supports the exact same wildcard syntax as the positive prompt "
                        "above, and is likewise resolved independently for each image in the batch."
                    ),
                    "placeholder": "negative"
                }),
                "seed":          ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "tooltip": "The seed for both wildcard resolution and noise generation. Each image uses seed + index, so the same seed and prompt always reproduce the same batch.",
                }),
                "batch_size":    ("INT", {
                    "default": 4, "min": 1, "max": 64, "step": 1,
                    "tooltip": "Number of images to generate. Each image resolves its own wildcards and gets its own prompt.",
                }),
                "width":         ("INT", {"default": 1024, "min": 64, "max": 16384, "step": 8}),
                "height":        ("INT", {"default": 1024, "min": 64, "max": 16384, "step": 8}),
                "steps":         ("INT", {"default": 20, "min": 1, "max": 10000}),
                "cfg":           ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01}),
                "sampler_name":  (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler":     (comfy.samplers.KSampler.SCHEDULERS,),
                "denoise":       ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "recache_wildcards": ("BOOLEAN", {"default": False, "tooltip": "Force a reload of all wildcard files from disk. Can be disabled again after you have ran it once."}),
                "console_log": ("BOOLEAN", {"default": False, "tooltip": "Enable or disable detailed logging of the wildcard processing steps in the console."}),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."}),
                "clip":  ("CLIP", {"tooltip": "Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."}),
                "vae":   ("VAE", {"tooltip": "Optional. Reserved for sampling workflows."}),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    def generate_batch(self, text, negative, seed, batch_size, width, height,
                       steps, cfg, sampler_name, scheduler, denoise,
                       recache_wildcards, console_log,
                       model=None, clip=None, vae=None,
                       extra_pnginfo=None, unique_id=None):

        # --- Resolve positive and negative prompts for each batch index ---
        # A single processor instance is reused so its file caches persist across
        # all indices. Recaching, if requested, is only performed on the first pass.
        processor = WildcardProcessor()
        positive_prompts = []
        negative_prompts = []
        for i in range(batch_size):
            positive_prompts.append(processor.process_wildcards(
                wildcard_string=text,
                seed=seed + i,
                recache_wildcards=(recache_wildcards and i == 0),
                console_log=console_log,
            )[0])
            negative_prompts.append(processor.process_wildcards(
                wildcard_string=negative,
                seed=seed + i,
                recache_wildcards=False,
                console_log=console_log,
            )[0])

        # --- Print summary ---
        print(f"\n{'='*60}")
        print(f"  BATCH WILDCARD SAMPLER — {batch_size} variant(s)")
        for i, r in enumerate(positive_prompts):
            print(f"  [{i}] {r[:100]}{'...' if len(r) > 100 else ''}")
        print(f"{'='*60}\n")

        # Publish the per-image prompts so Save Image With Metadata can pick them up.
        set_batch_prompts(positive_prompts, negative_prompts, seed)

        # --- Decide whether to sample ---
        # Sampling needs a model and clip, AND is skipped entirely when the latent
        # output isn't connected to anything (pure prompt-preview use).
        latent_connected = self._latent_output_connected(extra_pnginfo, unique_id)
        should_sample = model is not None and clip is not None and latent_connected is not False

        if not should_sample:
            if latent_connected is False:
                print("  [Batch Wildcard Sampler] Latent output not connected — returning resolved prompts only.\n")
            else:
                print("  [Batch Wildcard Sampler] No model/clip connected — returning resolved prompts only.\n")
            empty_latent = torch.zeros([batch_size, 4, height // 8, width // 8])
            return ({"samples": empty_latent}, positive_prompts, model, clip)

        # --- Generate each image individually ---
        all_samples = []
        final_model = model
        final_clip = clip

        # Get the latent format from the model
        latent_format = model.get_model_object("latent_format") if hasattr(model, "get_model_object") else None

        # One loader instance, reused across images so its single-LoRA cache persists.
        lora_loader = LoraTagLoader()

        for i in range(batch_size):
            # Apply any <lora:...> tags from this image's positive prompt to fresh
            # clones of the model/clip. load_lora returns the model/clip with the
            # LoRAs applied and the prompt cleaned of its tags for CLIP encoding.
            model_i, clip_i, clean_positive = lora_loader.load_lora(
                model, clip, positive_prompts[i], console_log
            )
            final_model, final_clip = model_i, clip_i
            # The negative prompt is not used to load LoRAs, but strip any tags so
            # they are never sent to CLIP as text.
            clean_negative = _LORA_TAG_RE.sub("", negative_prompts[i])

            # Encode this image's positive and negative prompts through the (LoRA-applied) CLIP
            positive = self._encode(clip_i, clean_positive)
            negative_cond = self._encode(clip_i, clean_negative)

            # Create empty latent for this single image
            if latent_format is not None:
                latent_image = torch.zeros([1, latent_format.latent_channels, height // 8, width // 8], device="cpu")
            else:
                latent_image = torch.zeros([1, 4, height // 8, width // 8], device="cpu")

            latent_image = comfy.sample.fix_empty_latent_channels(model_i, latent_image)

            # Generate noise with unique seed per image
            image_seed = seed + i
            noise = comfy.sample.prepare_noise(latent_image, image_seed)

            # Sample with the (LoRA-applied) model
            print(f"  [Batch Wildcard Sampler] Sampling image {i + 1}/{batch_size}: seed={image_seed}")
            samples = comfy.sample.sample(
                model_i, noise, steps, cfg,
                sampler_name, scheduler,
                positive, negative_cond,
                latent_image,
                denoise=denoise,
                seed=image_seed,
            )

            all_samples.append(samples)

        # --- Combine all results into one batch ---
        combined = torch.cat(all_samples, dim=0)

        print(f"\n  [Batch Wildcard Sampler] Batch complete — {batch_size} images generated.")
        print(f"{'='*60}\n")

        return ({"samples": combined}, positive_prompts, final_model, final_clip)

    @staticmethod
    def _latent_output_connected(extra_pnginfo, unique_id):
        """
        Inspect the workflow graph to determine whether this node's `latent`
        output (slot 0) is connected to anything.

        Returns True/False when it can be determined, or None when the graph
        info is unavailable (e.g. API runs) so the caller can fall back to its
        default behaviour.
        """
        try:
            if not extra_pnginfo or unique_id is None:
                return None

            # EXTRA_PNGINFO is normally {"workflow": {...}}; tolerate a bare workflow too.
            workflow = extra_pnginfo.get("workflow") if isinstance(extra_pnginfo, dict) else None
            if workflow is None and isinstance(extra_pnginfo, dict) and "links" in extra_pnginfo:
                workflow = extra_pnginfo
            if not isinstance(workflow, dict):
                return None

            node_id = str(unique_id)
            links = workflow.get("links", [])

            for link in links:
                # litegraph link: [link_id, origin_id, origin_slot, target_id, target_slot, type]
                if isinstance(link, (list, tuple)) and len(link) >= 3:
                    if str(link[1]) == node_id and link[2] == 0:
                        return True
            return False
        except Exception:
            return None

    @staticmethod
    def _encode(clip, prompt):
        """Encode a single text prompt into a conditioning."""
        tokens = clip.tokenize(prompt)
        output = clip.encode_from_tokens(tokens, return_pooled=True, return_dict=True)
        cond_tensor = output.pop("cond")
        return [[cond_tensor, output]]


NODE_CLASS_MAPPINGS = {
    "BatchWildcardSampler": BatchWildcardSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchWildcardSampler": "🔀 Batch Wildcard Sampler",
}
