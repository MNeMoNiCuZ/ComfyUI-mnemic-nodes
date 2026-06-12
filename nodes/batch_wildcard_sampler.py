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
import comfy.utils

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
# Node: Batch Wildcard Upscale Sampler
# ---------------------------------------------------------------------------

class BatchWildcardSampler:
    """
    Resolves a fresh set of wildcards for every image in the batch, then encodes
    and samples each one individually so a single run yields a different prompt
    per image. Wildcard resolution is delegated to the WildcardProcessor.
    """

    CATEGORY = "⚡ MNeMiC Nodes"
    FUNCTION = "generate_batch"
    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "CONDITIONING", "LATENT", "STRING")
    RETURN_NAMES = ("model", "clip", "positive", "negative", "latent", "prompt")
    OUTPUT_TOOLTIPS = (
        "The model after LoRA patches from the last batch item have been applied.",
        "The CLIP after LoRA patches from the last batch item have been applied.",
        "The positive conditioning encoded from the last batch item's prompt.",
        "The negative conditioning encoded from the last batch item's prompt.",
        "The combined batch of sampled latents (empty when sampling is skipped).",
        "The resolved positive prompt for each image, as a list with one entry per batch item.",
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
                "upscale":       ("BOOLEAN", {
                    "default": False,
                    "tooltip": (
                        "Enable an upscale second pass: after the first sampling, each image's latent is "
                        "upscaled and sampled again at the larger resolution. The upscale settings are in the "
                        "Advanced section."
                    ),
                }),
                # The upscale controls live in the collapsible "Advanced" section ("advanced": True),
                # hidden until the node's Advanced toggle is expanded.
                "upscale_rate":  ("FLOAT", {
                    "default": 2.0, "min": 1.0, "max": 4.0, "step": 0.05, "round": 0.01, "advanced": True,
                    "tooltip": (
                        "Upscale factor. The first-pass latent is upscaled by this much before the second "
                        "pass (e.g. 2.0 doubles width and height). The slider goes up to 4, but larger values can "
                        "be typed in. Only used when 'upscale' is on and this is greater than 1. "
                        "When an upscale model is connected, it runs first (e.g. a 4x ESRGAN), then the result is "
                        "downscaled to the exact target size implied by upscale_rate — so a 4x model with "
                        "upscale_rate=2.0 gives a clean 2x final."
                    ),
                }),
                "upscale_denoise": ("FLOAT", {
                    "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01, "advanced": True,
                    "tooltip": (
                        "Denoise strength for the upscale second pass. Lower keeps the first-pass composition but "
                        "leaves upscale artifacts; higher adds detail but can drift from the original image."
                    ),
                }),
                "upscale_steps": ("INT", {
                    "default": 20, "min": 1, "max": 10000, "advanced": True,
                    "tooltip": "Steps for the upscale pass.",
                }),
                "upscale_cfg":   ("FLOAT", {
                    "default": 4.0, "min": 0.0, "max": 100.0, "step": 0.1, "round": 0.01, "advanced": True,
                    "tooltip": "CFG for the upscale pass. 0 = use the same cfg as the first pass.",
                }),
                "upscale_sampler_name": (["(same as first pass)"] + list(comfy.samplers.KSampler.SAMPLERS), {
                    "advanced": True,
                    "tooltip": "Sampler for the upscale pass. '(same as first pass)' reuses the first-pass sampler.",
                }),
                "upscale_scheduler": (["(same as first pass)"] + list(comfy.samplers.KSampler.SCHEDULERS), {
                    "advanced": True,
                    "tooltip": "Scheduler for the upscale pass. '(same as first pass)' reuses the first-pass scheduler.",
                }),
                "upscale_noise_inject_strength": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01, "round": 0.01, "advanced": True,
                    "tooltip": (
                        "Inject additional Gaussian noise into the upscaled latent before the second-pass "
                        "sampler runs. 0.0 = no extra noise (default). The actual noise magnitude is "
                        "strength × σ(scheduler, start_step), so the curve follows the upscale scheduler: "
                        "e.g. karras front-loads its sigmas and injects more noise at low strength values "
                        "than a linear schedule would. This adds variation and can break up VAE-encode "
                        "artifacts before refinement."
                    ),
                }),
                # NOTE: the "hires_debug" input + output were removed from the node. The code is
                # preserved (commented out) at the very bottom of this file under
                # "DISABLED: hi-res debug capture" in case it needs to be re-enabled.
                "strip_prompt_weights": ("BOOLEAN", {
                    "default": False, "advanced": True,
                    "tooltip": (
                        "Strip per-token weight syntax from prompts before encoding. Removes patterns like "
                        "(word:1.3) — used for emphasis in older CLIP models — leaving just the text "
                        "(e.g. 'word').\n\n"
                        "Modern LLM-based text encoders such as T5 (used in FLUX, SD3, and other newer "
                        "models) process prompts as natural language and do not support "
                        "ComfyUI/A1111-style prompt weighting. Feeding them weighted syntax causes the "
                        "encoder to interpret the parentheses and colons as literal characters, which can "
                        "degrade prompt adherence. Enable this when your model uses an LLM-based text "
                        "encoder."
                    ),
                }),
                "recache_wildcards": ("BOOLEAN", {
                    "default": False, "advanced": True,
                    "tooltip": "Force a reload of all wildcard files from disk. Can be disabled again after you have ran it once.",
                }),
                "console_log": ("BOOLEAN", {
                    "default": False, "advanced": True,
                    "tooltip": "Enable or disable detailed logging of the wildcard processing steps in the console.",
                }),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."}),
                "clip":  ("CLIP", {"tooltip": "Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."}),
                "vae":   ("VAE", {"tooltip": "Optional for plain sampling, but REQUIRED for the upscale pass: it decodes the latent to an image, the image is Lanczos-upscaled in pixel space, then re-encoded. Without a VAE the upscale pass is skipped."}),
                "upscale_model": ("UPSCALE_MODEL", {"tooltip": "Optional. Connect a 'Load Upscale Model' (e.g. an ESRGAN/4x model) to use AI super-resolution for the hi-res upscale instead of plain Lanczos."}),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    def generate_batch(self, text, negative, seed, batch_size, width, height,
                       steps, cfg, sampler_name, scheduler, denoise,
                       upscale=False, upscale_rate=2.0, upscale_denoise=0.37,
                       upscale_steps=20, upscale_cfg=4.0,
                       upscale_sampler_name="(same as first pass)",
                       upscale_scheduler="(same as first pass)",
                       upscale_noise_inject_strength=0.0,
                       recache_wildcards=False, console_log=False,
                       strip_prompt_weights=False,
                       model=None, clip=None, vae=None, upscale_model=None,
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
            return (model, clip, None, None, {"samples": empty_latent}, positive_prompts)

        # --- Generate each image individually ---
        all_samples = []
        final_model = model
        final_clip = clip
        final_positive = None
        final_negative = None

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

            if strip_prompt_weights:
                clean_positive = self._strip_weight_syntax(clean_positive)
                clean_negative = self._strip_weight_syntax(clean_negative)

            # Encode this image's positive and negative prompts through the (LoRA-applied) CLIP
            positive = self._encode(clip_i, clean_positive)
            negative_cond = self._encode(clip_i, clean_negative)
            # Exposed on the outputs (from the last batch item, like model/clip).
            final_positive, final_negative = positive, negative_cond

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

            # --- Optional upscale second pass ---
            # When upscale is on (and the rate is above 1), upscale this image's
            # latent and sample it again at the larger resolution. The upscale pass
            # uses its own denoise, and optionally its own steps/cfg/sampler/scheduler
            # (each falls back to the first-pass value when left at its default).
            if upscale and upscale_rate > 1.0 and vae is None:
                print("  [Batch Wildcard Sampler] upscale is on but no VAE is connected — "
                      "the upscale pass needs a VAE to upscale in pixel space. Skipping the upscale pass.")

            if upscale and upscale_rate > 1.0 and vae is not None:
                upscale_width = (int(round(width * upscale_rate)) // 8) * 8
                upscale_height = (int(round(height * upscale_rate)) // 8) * 8

                eff_steps = upscale_steps
                eff_cfg = upscale_cfg if upscale_cfg > 0 else cfg
                eff_sampler = sampler_name if upscale_sampler_name == "(same as first pass)" else upscale_sampler_name
                eff_scheduler = scheduler if upscale_scheduler == "(same as first pass)" else upscale_scheduler

                print(f"  [Batch Wildcard Sampler] Upscale pass {i + 1}/{batch_size}: "
                      f"{width}x{height} -> {upscale_width}x{upscale_height} "
                      f"(rate={upscale_rate}, denoise={upscale_denoise}, steps={eff_steps}, cfg={eff_cfg}, "
                      f"sampler={eff_sampler}, scheduler={eff_scheduler})")

                upscaled = self._run_upscale(
                    samples, upscale_width, upscale_height, vae, upscale_model, model_i,
                )

                # Noise is injected exactly as in the first pass: unit Gaussian noise
                # from prepare_noise(), with the sampler scaling it by the starting
                # sigma implied by upscale_denoise. Same seed as the first pass.
                upscale_noise = comfy.sample.prepare_noise(upscaled, image_seed)

                # Build per-step noise injection callback. When strength > 0 the
                # callback fires at every denoising step and adds noise × σ_i ×
                # strength, so injection is heaviest early and tapers to near-zero
                # as the sampler converges. None means no extra noise.
                noise_inject_cb = None
                if upscale_noise_inject_strength > 0.0:
                    noise_inject_cb = self._make_noise_inject_callback(
                        upscale_noise_inject_strength,
                        upscale_denoise, eff_scheduler, eff_steps,
                        model_i, image_seed,
                    )

                # The upscale pass uses the SAME positive/negative conditioning that
                # was encoded from this image's resolved prompt above — identical to
                # what drove the first pass. This is intentional: the upscale is a
                # guided hi-res refinement, not an unconditional diffusion step.
                samples = comfy.sample.sample(
                    model_i, upscale_noise, eff_steps, eff_cfg,
                    eff_sampler, eff_scheduler,
                    positive, negative_cond,
                    upscaled,
                    denoise=upscale_denoise,
                    seed=image_seed,
                    callback=noise_inject_cb,
                )

            all_samples.append(samples)

            # --- Clean model state between batch items ---
            # When this item loaded a LoRA, load_lora returned a *clone* of the
            # base model that shares the same underlying weights. ComfyUI patches
            # those shared weights in place and keeps the model resident, so the
            # next item's clone can end up patching on top of weights that were
            # never cleanly reverted — they drift into NaNs and the image decodes
            # as pure black (randomly, depending on VRAM/offload timing). Fully
            # unloading here forces the next item to re-patch from clean base
            # weights. Only done when a clone was actually created, so the
            # no-LoRA path keeps reusing the same model with no reload cost.
            if model_i is not model or clip_i is not clip:
                comfy.model_management.unload_all_models()

        # --- Combine all results into one batch ---
        combined = torch.cat(all_samples, dim=0)

        print(f"\n  [Batch Wildcard Sampler] Batch complete — {batch_size} images generated.")
        print(f"{'='*60}\n")

        return (final_model, final_clip, final_positive, final_negative,
                {"samples": combined}, positive_prompts)

    @staticmethod
    def _make_noise_inject_callback(strength, denoise, scheduler, steps, model_i, seed):
        """
        Returns a per-step callback for comfy.sample.sample that injects
        scheduler-scaled Gaussian noise at every denoising step.

        At step i the injected magnitude is strength × σ_i, so injection is
        heaviest at the start (large sigma) and tapers to near-zero as the
        sampler converges (sigma → 0). The noise is seeded deterministically
        per step (seed + step) for reproducibility.
        """
        model_sampling = model_i.get_model_object("model_sampling")
        device = comfy.model_management.get_torch_device()
        try:
            sigmas = comfy.samplers.calculate_sigmas(model_sampling, scheduler, steps, device)
        except TypeError:
            sigmas = comfy.samplers.calculate_sigmas(model_sampling, scheduler, steps)

        # Slice to the steps actually taken given the denoise level so that
        # callback step 0 aligns with the sampler's first real sigma.
        n = len(sigmas)
        start_idx = max(0, min(int(n * (1.0 - denoise)), n - 2))
        active_sigmas = sigmas[start_idx:]

        print(f"  [Batch Wildcard Sampler] Upscale noise inject: strength={strength:.3f}, "
              f"σ_start={active_sigmas[0].item():.4f}, σ_end={active_sigmas[-1].item():.4f}, "
              f"active_steps={len(active_sigmas) - 1}")

        def callback(step, x0, x, total_steps):
            if step < len(active_sigmas) - 1:
                sigma_i = active_sigmas[step].item()
                gen = torch.Generator(device=x.device)
                gen.manual_seed(seed + step)
                noise_i = torch.randn(x.shape, generator=gen, device=x.device, dtype=x.dtype)
                x.add_(noise_i * (sigma_i * strength))

        return callback

    def _run_upscale(self, samples, upscale_width, upscale_height, vae, upscale_model, model_i):
        """
        Enlarge the first-pass latent for the upscale second pass, entirely in
        PIXEL space: decode the latent to an image, Lanczos-resize it (exactly like
        the native "Upscale Image" node), then re-encode. This preserves the
        picture, so a low upscale denoise is enough. No latent-space upscaling.

        Works for ordinary image VAEs (decode -> 4D [B,H,W,C]) and for image VAEs
        that are internally 3D, such as Qwen-Image / Wan (decode -> 5D
        [B,T,H,W,C]). The image is always reduced to a flat 4D batch of NHWC frames
        before encoding, so the VAE wrapper does its own correct 4D -> native-rank
        conversion (feeding it a hand-built 5D tensor bypasses that and breaks).
        """
        # 1) Decode latent -> pixels.
        image = vae.decode(samples)  # NHWC (4D) or NTHWC (5D), values 0..1
        print(f"  [Batch Wildcard Sampler] pixel upscale: latent {tuple(samples.shape)} "
              f"-> decoded image {tuple(image.shape)}")

        # 2) Flatten any temporal/extra leading axis into the batch so we have a
        #    plain 4D NHWC batch of images.
        if image.ndim == 5:
            image = image.reshape(-1, image.shape[-3], image.shape[-2], image.shape[-1])

        # 3) Upscale in pixel space (Lanczos), or with an upscale model if connected.
        if upscale_model is not None:
            image = self._upscale_with_model(upscale_model, image)
        image = image.movedim(-1, 1)  # NHWC -> NCHW
        image = comfy.utils.common_upscale(image, upscale_width, upscale_height, "lanczos", "disabled")
        image = image.movedim(1, -1).clamp(0.0, 1.0)  # NCHW -> NHWC

        # 4) Re-encode. Always hand the VAE a 4D NHWC image (same as the native VAE
        #    Encode node); the wrapper adds any temporal axis the VAE needs.
        print(f"  [Batch Wildcard Sampler] pixel upscale: encoding image {tuple(image.shape)}")
        upscaled = vae.encode(image[:, :, :, :3])
        print(f"  [Batch Wildcard Sampler] pixel upscale: encoded latent {tuple(upscaled.shape)}")

        # 5) Match the first-pass latent's rank (3D image VAEs hand back a 5D latent
        #    with a temporal axis of 1) so the second sampling pass sees the same
        #    latent shape as the first.
        if samples.ndim == 4 and upscaled.ndim == 5 and upscaled.shape[2] == 1:
            upscaled = upscaled[:, :, 0]

        return comfy.sample.fix_empty_latent_channels(model_i, upscaled)

    @staticmethod
    def _upscale_with_model(upscale_model, image):
        """Run an UPSCALE_MODEL (e.g. ESRGAN) over a pixel image (NHWC, 0..1)."""
        device = comfy.model_management.get_torch_device()
        upscale_model.to(device)
        in_img = image.movedim(-1, -3).to(device)  # NHWC -> NCHW
        try:
            upscaled = comfy.utils.tiled_scale(
                in_img, lambda a: upscale_model(a),
                tile_x=512, tile_y=512, overlap=32,
                upscale_amount=upscale_model.scale,
            )
        finally:
            upscale_model.to("cpu")
        return torch.clamp(upscaled.movedim(-3, -1), min=0.0, max=1.0)  # NCHW -> NHWC

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
                    if str(link[1]) == node_id and link[2] == 4:
                        return True
            return False
        except Exception:
            return None

    @staticmethod
    def _strip_weight_syntax(text):
        """
        Remove (word:number) prompt-weight syntax, leaving only the inner text.
        Handles nested weights by iterating until no more matches remain.
        Only targets the exact pattern (text:number) — does not touch {|} or other syntax.
        """
        # Matches (any text without parens or colons : a number) e.g. (hair ribbon:0.9)
        _weight_re = re.compile(r"\(([^():]+):\d+(?:\.\d+)?\)")
        while True:
            replaced = _weight_re.sub(r"\1", text)
            if replaced == text:
                break
            text = replaced
        return text

    @staticmethod
    def _encode(clip, prompt):
        """Encode a single text prompt into a conditioning."""
        tokens = clip.tokenize(prompt)
        output = clip.encode_from_tokens(tokens, return_pooled=True, return_dict=True)
        cond_tensor = output.pop("cond")
        return [[cond_tensor, output]]


NODE_CLASS_MAPPINGS = {
    "🔀 Batch Wildcard Upscale Sampler": BatchWildcardSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "🔀 Batch Wildcard Upscale Sampler": "🔀 Batch Wildcard Upscale Sampler",
}


# ===========================================================================
# DISABLED: hi-res debug capture
# ---------------------------------------------------------------------------
# This feature added a "hires_debug" boolean input and a "hires_debug" LATENT
# output. When enabled it captured the upscaled latent plus the denoised x0
# prediction at every hi-res step, so the batch could be VAE-decoded to watch
# the second pass evolve. It was removed from the live node but kept here for
# easy re-enabling. NOT executed — this is reference only.
#
# To re-enable, restore these pieces:
#
# 1) INPUT_TYPES (advanced section, next to the other hires_* widgets):
#
#     "hires_debug":   ("BOOLEAN", {
#         "default": False, "advanced": True,
#         "tooltip": (
#             "Debug only. When on, the 'hires_debug' output is filled with the "
#             "upscaled latent plus the denoised prediction at every hi-res step."
#         ),
#     }),
#
# 2) RETURN_TYPES / RETURN_NAMES / OUTPUT_TOOLTIPS: append one more output:
#
#     RETURN_TYPES = (..., "LATENT")
#     RETURN_NAMES = (..., "hires_debug")
#     OUTPUT_TOOLTIPS = (..., "Debug only: upscaled latent + per-step x0.")
#
# 3) generate_batch signature: add  hires_debug=False  (before recache_wildcards).
#
# 4) In the no-sample early return, append a placeholder debug latent:
#
#     return ({"samples": empty_latent}, positive_prompts, model, clip, None, None,
#             {"samples": torch.zeros([1, 4, height // 8, width // 8])})
#
# 5) Before the per-item loop, init the capture list:
#
#     hires_debug_samples = []  # Filled per hi-res step when hires_debug is on.
#
# 6) Inside the hi-res pass, just before the second comfy.sample.sample call,
#    build the callback and pass it as  callback=debug_callback :
#
#     debug_callback = None
#     if hires_debug:
#         # Force float32 on CPU so frames from different dtypes (VAE-encoded
#         # latent vs. model x0) concatenate cleanly into one debug batch.
#         hires_debug_samples.append(upscaled.detach().float().cpu())
#
#         def debug_callback(step, x0, x, total_steps):
#             hires_debug_samples.append(x0.detach().float().cpu())
#
#     samples = comfy.sample.sample(
#         model_i, hires_noise, eff_steps, eff_cfg,
#         eff_sampler, eff_scheduler,
#         positive, negative_cond,
#         upscaled,
#         denoise=hires_denoise,
#         seed=image_seed,
#         callback=debug_callback,
#     )
#
# 7) After the loop (just after `combined = torch.cat(...)`), assemble the batch
#    and append it to the return tuple:
#
#     if hires_debug_samples:
#         hires_debug_latent = {"samples": torch.cat(hires_debug_samples, dim=0)}
#     else:
#         hires_debug_latent = {"samples": torch.zeros([1, combined.shape[1], height // 8, width // 8])}
#
#     return ({"samples": combined}, positive_prompts, final_model, final_clip,
#             final_positive, final_negative, hires_debug_latent)
# ===========================================================================
