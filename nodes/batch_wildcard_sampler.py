"""
Batch Wildcard Sampler — per-batch-index prompt variation for ComfyUI.

The defining feature: wildcards are resolved independently for every image in the
batch, so a single run produces a different prompt (and therefore a different
image) per batch index.

This is true batching: every prompt is encoded through CLIP, the conditionings
are stacked along the batch dimension (one entry per image), and the whole batch
is sampled in a single sampler call. ComfyUI hands conditioning entry n to latent
n when the conditioning batch matches the latent batch.

Wildcard resolution is delegated to the WildcardProcessor so the full syntax
(file wildcards, glob patterns, inline choices, weighted choices, multiple
selections, ranged selections, variables, and nesting) is supported.

LoRAs can be loaded directly from <lora:name:strength> tags in the prompt — the
same mechanism as the LoRA Loader Prompt Tags node — so no separate loader is
needed. Tags are kept in the resolved prompt (for metadata) and stripped before
the text is sent to CLIP. Differing LoRAs use per-image additive adapters inside
the same model forward pass; each prompt is encoded with its own CLIP patches.
"""

import re
import folder_paths

import torch
import torch.nn.functional as F

import comfy.sample
import comfy.lora
import comfy.lora_convert
import comfy.conds
import comfy.samplers
import comfy.model_management
import comfy.utils

from .wildcard_processor import WildcardProcessor
from .lora_tag_loader import LoraTagLoader, TAG_PATTERN, parse_lora_tag, load_lora_file
from ..utils.batch_wildcard_runtime import set_batch_prompts
from ..utils.settings_utils import is_wildcard_console_log_enabled, is_lora_console_log_enabled

from comfy_api.latest import io


# Matches <lora:name:strength> tags so they can be stripped before CLIP encoding.
_LORA_TAG_RE = re.compile(r"<lora:[^>]+>", re.IGNORECASE)


# Shared wildcard-syntax help, appended to the positive prompt tooltip.
_WILDCARD_SYNTAX_HELP = (
    "File Wildcards:\nUse __filename__ to insert a random line from filename.txt in one of the supported wildcard directories. Lines starting with # are treated as comments and are ignored.\n\n"
    "Inline Choices:\nUse {a|b|c} to randomly choose between a, b, or c.\nExample Input: A photo of a {red|green|blue} car.\nExample Output: A photo of a green car.\n\n"
    "Weighted Choices:\nUse {5::black|green|red} to make black 5 times more likely to be chosen than green or red. Weights are normalized to 100% based on the sum of all weights in the block (e.g. {5::red|4::green|7::blue|black} sums to 17, giving red ~29%, green ~24%, blue ~41%, black ~6%).\n\n"
    "Select Multiple Wildcards:\nUse {2$$a|b|c|d} to output a specific number of items from the result.\nExample Input: My favorite colors are {3$$red|green|blue|yellow|purple}.\nExample Output: My favorite colors are blue, yellow, purple.\n\n"
    "Ranged Select Multiple:\nUse {1-3$$red|green|blue|yellow|purple} to select a random number of 1-3 items within a range.\n\n"
    "Custom Separator:\nUse {1-3$$, $$red|green|blue|yellow|purple} to join the selected items with a custom separator (here, \", \") instead of the default.\n\n"
    "Variables:\nDefine a variable to reuse a value. Can be defined directly, or using a wildcard\nExample Input: ${animal=!__animals__} The ${animal} is friends with the other ${animal}.\nExample Output: The cat is friends with the other cat.\n\n"
    "LoRAs:\nInclude <lora:name:strength> tags to load LoRAs automatically (no separate LoRA loader node needed).\nExample: <lora:mylora:0.75>\nThe best matching LoRA file is found by name. Strength is optional (defaults to 1.0); add a second value for a separate CLIP strength, e.g. <lora:mylora:0.8:0.6>. The tag stays in the resolved prompt for metadata and is removed before the text reaches CLIP."
)


# ---------------------------------------------------------------------------
# Node: Batch Wildcard Upscale Sampler
# ---------------------------------------------------------------------------

class BatchWildcardSampler(io.ComfyNode):
    """
    Resolves a fresh set of wildcards for every image in the batch, encodes each
    prompt, and samples the whole batch at once with one conditioning entry per
    image. Wildcard resolution is delegated to the WildcardProcessor.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_BatchWildcardSampler",
            display_name="🔀 Batch Wildcard Upscale Sampler",
            category="⚡ MNeMiC Nodes",
            description=("Resolves wildcards independently for every image, then samples them together as a true "
                         "batch with per-image prompts and LoRA weights. Leave model and clip disconnected to preview prompts."),
            inputs=[
                io.String.Input(
                    "text",
                    multiline=True,
                    dynamic_prompts=False,
                    tooltip=(
                        "Positive prompt with full wildcard and <lora:...> support.\n\n"
                        "How this node uses it:\n"
                        "- Each image resolves this prompt independently.\n"
                        "- Each image can end up with a different final prompt.\n"
                        "- All images are sampled together as one batch, each with its own prompt.\n\n"
                        "Use the same seed to reproduce the same sequence of resolved prompts.\n\n"
                        + _WILDCARD_SYNTAX_HELP
                    ),
                    placeholder="A photo of a __sample_colors__ {dog|cat|monkey} <lora:mylora:0.75>",
                ),
                io.String.Input(
                    "negative",
                    multiline=True,
                    dynamic_prompts=False,
                    tooltip=(
                        "Negative prompt.\n\n"
                        "Supports the exact same wildcard syntax as the positive prompt.\n\n"
                        "How this node uses it:\n"
                        "- Each image resolves its own negative prompt independently."
                    ),
                    placeholder="negative",
                ),
                io.Int.Input(
                    "seed", default=0, min=0, max=0xffffffffffffffff,
                    tooltip="Base seed for both wildcard resolution and sampling noise.\n\n"
                            "Per-image behavior:\n"
                            "- Image 1 uses seed + 0\n"
                            "- Image 2 uses seed + 1\n"
                            "- Image 3 uses seed + 2\n\n"
                            "Using the same seed and the same prompts reproduces the same batch.",
                ),
                io.Int.Input(
                    "batch_size", default=4, min=1, max=64, step=1,
                    tooltip="How many images to generate.\n\n"
                            "This is a true sampler batch: every image gets its own resolved prompt, and the "
                            "whole batch is sampled (and optionally upscaled) at once. VRAM use grows with the "
                            "batch size.\n\n"
                            "Different LoRA tags and weights use per-image adapters in the same batch; "
                            "see the help page for supported adapter formats.",
                ),
                io.Int.Input("width", default=1024, min=64, max=16384, step=8, tooltip="Width of each generated image, in pixels."),
                io.Int.Input("height", default=1024, min=64, max=16384, step=8, tooltip="Height of each generated image, in pixels."),
                io.Int.Input("steps", default=20, min=1, max=10000, tooltip="Sampling steps for the first pass."),
                io.Float.Input("cfg", default=7.0, min=0.0, max=100.0, step=0.1, round=0.01, tooltip="Classifier-free guidance scale for the first pass. Higher follows the prompt more literally."),
                io.Combo.Input("sampler_name", options=comfy.samplers.KSampler.SAMPLERS, tooltip="Sampler used for the first pass."),
                io.Combo.Input("scheduler", options=comfy.samplers.KSampler.SCHEDULERS, tooltip="Sigma schedule used for the first pass."),
                io.Float.Input("denoise", default=1.0, min=0.0, max=1.0, step=0.01, tooltip="Denoise strength for the first pass. 1.0 generates from pure noise."),
                io.Boolean.Input(
                    "upscale", default=False,
                    tooltip=(
                        "Enable an upscale second pass: after the first sampling, each image's latent is "
                        "upscaled and sampled again at the larger resolution. The upscale settings are in the "
                        "Advanced section."
                    ),
                ),
                # The upscale controls live in the collapsible "Advanced" section (advanced=True),
                # hidden until the node's Advanced toggle is expanded.
                io.Float.Input(
                    "upscale_rate", default=2.0, min=1.0, max=4.0, step=0.05, round=0.01, advanced=True,
                    tooltip=(
                        "Upscale factor. The first-pass latent is upscaled by this much before the second "
                        "pass (e.g. 2.0 doubles width and height). The slider goes up to 4, but larger values can "
                        "be typed in. Only used when 'upscale' is on and this is greater than 1. "
                        "When an upscale model is connected, it runs first (e.g. a 4x ESRGAN), then the result is "
                        "downscaled to the exact target size implied by upscale_rate — so a 4x model with "
                        "upscale_rate=2.0 gives a clean 2x final."
                    ),
                ),
                io.Float.Input(
                    "upscale_denoise", default=0.2, min=0.0, max=1.0, step=0.01, advanced=True,
                    tooltip=(
                        "Denoise strength for the upscale second pass. Lower keeps the first-pass composition but "
                        "leaves upscale artifacts; higher adds detail but can drift from the original image."
                    ),
                ),
                io.Int.Input(
                    "upscale_steps", default=20, min=1, max=10000, advanced=True,
                    tooltip="Steps for the upscale pass.",
                ),
                io.Float.Input(
                    "upscale_cfg", default=4.0, min=0.0, max=100.0, step=0.1, round=0.01, advanced=True,
                    tooltip="CFG for the upscale pass. 0 = use the same cfg as the first pass.",
                ),
                io.Combo.Input(
                    "upscale_sampler_name",
                    options=["(same as first pass)"] + list(comfy.samplers.KSampler.SAMPLERS),
                    advanced=True,
                    tooltip="Sampler for the upscale pass. '(same as first pass)' reuses the first-pass sampler.",
                ),
                io.Combo.Input(
                    "upscale_scheduler",
                    options=["(same as first pass)"] + list(comfy.samplers.KSampler.SCHEDULERS),
                    advanced=True,
                    tooltip="Scheduler for the upscale pass. '(same as first pass)' reuses the first-pass scheduler.",
                ),
                io.Float.Input(
                    "upscale_noise_inject_strength", default=0.0, min=0.0, max=1.0, step=0.01, round=0.01, advanced=True,
                    tooltip=(
                        "Inject additional Gaussian noise into the upscaled latent before the second-pass "
                        "sampler runs. 0.0 = no extra noise (default). The actual noise magnitude is "
                        "strength × σ(scheduler, start_step), so the curve follows the upscale scheduler: "
                        "e.g. karras front-loads its sigmas and injects more noise at low strength values "
                        "than a linear schedule would. This adds variation and can break up VAE-encode "
                        "artifacts before refinement."
                    ),
                ),
                # NOTE: the "hires_debug" input + output were removed from the node. The code is
                # preserved (commented out) at the very bottom of this file under
                # "DISABLED: hi-res debug capture" in case it needs to be re-enabled.
                io.Boolean.Input(
                    "strip_prompt_weights", default=False, advanced=True,
                    tooltip=(
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
                ),
                io.Boolean.Input(
                    "recache_wildcards", default=False, advanced=True,
                    tooltip="Force a reload of all wildcard files from disk. Can be disabled again after you have ran it once.",
                ),
                io.Model.Input("model", optional=True, tooltip="Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."),
                io.Clip.Input("clip", optional=True, tooltip="Optional. Only needed to sample images. Leave disconnected (or leave the latent output unused) to just resolve and preview prompts."),
                io.Vae.Input("vae", optional=True, tooltip="Optional for plain sampling, but REQUIRED for the upscale pass: it decodes the latent to an image, the image is Lanczos-upscaled in pixel space, then re-encoded. Without a VAE the upscale pass is skipped."),
                io.UpscaleModel.Input("upscale_model", optional=True, tooltip="Optional. Connect a 'Load Upscale Model' (e.g. an ESRGAN/4x model) to use AI super-resolution for the hi-res upscale instead of plain Lanczos."),
            ],
            outputs=[
                io.Model.Output(display_name="model", tooltip="Model with shared and per-image LoRAs. Reuse with the same latent batch size and image order."),
                io.Clip.Output(display_name="clip", tooltip="CLIP with shared leading LoRA tags. Per-image CLIP patches are already baked into the conditioning outputs."),
                io.Vae.Output(display_name="vae", tooltip="The VAE input passed through for downstream use, including hi-res workflows."),
                io.Conditioning.Output(display_name="positive", tooltip="The batched positive conditioning: one entry per image, in batch order, matching the latent output."),
                io.Conditioning.Output(display_name="negative", tooltip="The batched negative conditioning: one entry per image, in batch order, matching the latent output."),
                io.Latent.Output(display_name="latent", tooltip="The combined batch of sampled latents (empty when sampling is skipped)."),
                io.String.Output(display_name="prompt", tooltip="The resolved positive prompt for each image, as a list with one entry per batch item."),
            ],
            hidden=[io.Hidden.extra_pnginfo, io.Hidden.unique_id],
        )

    @classmethod
    def execute(cls, text, negative, seed, batch_size, width, height,
                       steps, cfg, sampler_name, scheduler, denoise,
                       upscale=False, upscale_rate=2.0, upscale_denoise=0.37,
                       upscale_steps=20, upscale_cfg=4.0,
                       upscale_sampler_name="(same as first pass)",
                       upscale_scheduler="(same as first pass)",
                       upscale_noise_inject_strength=0.0,
                       recache_wildcards=False,
                       strip_prompt_weights=False,
                       model=None, clip=None, vae=None, upscale_model=None) -> io.NodeOutput:
        extra_pnginfo = cls.hidden.extra_pnginfo
        unique_id = cls.hidden.unique_id

        console_log = is_wildcard_console_log_enabled()

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
            )[0])
            negative_prompts.append(processor.process_wildcards(
                wildcard_string=negative,
                seed=seed + i,
                recache_wildcards=False,
            )[0])

        # --- Print summary ---
        if console_log:
            print(f"\n{'='*60}")
            print(f"  BATCH WILDCARD SAMPLER — {batch_size} variant(s)")
            for i, r in enumerate(positive_prompts):
                print(f"  [{i}] {r}")
            print(f"{'='*60}\n")

        # Publish the per-image prompts so Save Image With Metadata can pick them up.
        set_batch_prompts(positive_prompts, negative_prompts, seed)

        # --- Decide whether to sample ---
        # Sampling needs a model and clip, AND is skipped entirely when the latent
        # output isn't connected to anything (pure prompt-preview use).
        latent_connected = cls._latent_output_connected(extra_pnginfo, unique_id)
        should_sample = model is not None and clip is not None and latent_connected is not False

        if not should_sample:
            if console_log:
                if latent_connected is False:
                    print("  [Batch Wildcard Sampler] Latent output not connected — returning resolved prompts only.\n")
                else:
                    print("  [Batch Wildcard Sampler] No model/clip connected — returning resolved prompts only.\n")
            empty_latent = torch.zeros([batch_size, 4, height // 8, width // 8])
            return io.NodeOutput(model, clip, vae, None, None, {"samples": empty_latent}, positive_prompts)

        if upscale and upscale_rate > 1.0 and vae is None:
            print("  [Batch Wildcard Sampler] No VAE connected; skipping upscale.")

        final_model, final_clip, all_positive, all_negative = cls._prepare_batch(
            model, clip, positive_prompts, negative_prompts, strip_prompt_weights,
        )
        positive = cls._batch_conditioning(all_positive)
        negative_cond = cls._batch_conditioning(all_negative)
        seeds = [(seed + i) % (1 << 64) for i in range(batch_size)]

        latent_image = torch.zeros([batch_size, 4, height // 8, width // 8],
                                   device=comfy.model_management.intermediate_device(),
                                   dtype=comfy.model_management.intermediate_dtype())
        latent_image = comfy.sample.fix_empty_latent_channels(final_model, latent_image, 8)

        # Noise is generated per image from seed + index, so every image starts
        # from the same noise it would get if sampled on its own. The sampler's
        # own seed (used by ancestral/SDE samplers) is the batch's first seed.
        noise = torch.cat([comfy.sample.prepare_noise(latent_image[j:j + 1], s) for j, s in enumerate(seeds)])

        if console_log:
            print(f"  [Batch Wildcard Sampler] Sampling batch of {batch_size}: seeds={seeds}")
        samples = comfy.sample.sample(
            final_model, noise, steps, cfg,
            sampler_name, scheduler,
            positive, negative_cond,
            latent_image,
            denoise=denoise,
            seed=seeds[0],
        )

        # --- Optional upscale second pass ---
        # When upscale is on (and the rate is above 1), upscale the batch's
        # latents and sample them again at the larger resolution. The upscale
        # pass uses its own denoise, and optionally its own steps/cfg/sampler/
        # scheduler (each falls back to the first-pass value when left at its default).
        if upscale and upscale_rate > 1.0 and vae is not None:
            upscale_width = (int(round(width * upscale_rate)) // 8) * 8
            upscale_height = (int(round(height * upscale_rate)) // 8) * 8

            eff_steps = upscale_steps
            eff_cfg = upscale_cfg if upscale_cfg > 0 else cfg
            eff_sampler = sampler_name if upscale_sampler_name == "(same as first pass)" else upscale_sampler_name
            eff_scheduler = scheduler if upscale_scheduler == "(same as first pass)" else upscale_scheduler

            if console_log:
                print(f"  [Batch Wildcard Sampler] Upscale pass, batch of {batch_size}: "
                      f"{width}x{height} -> {upscale_width}x{upscale_height} "
                      f"(rate={upscale_rate}, denoise={upscale_denoise}, steps={eff_steps}, cfg={eff_cfg}, "
                      f"sampler={eff_sampler}, scheduler={eff_scheduler})")

            upscaled = cls._run_upscale(
                samples, upscale_width, upscale_height, vae, upscale_model, final_model,
            )

            # Noise is injected exactly as in the first pass: unit Gaussian noise
            # from prepare_noise(), with the sampler scaling it by the starting
            # sigma implied by upscale_denoise. Same per-image seeds as the first pass.
            upscale_noise = torch.cat([comfy.sample.prepare_noise(upscaled[j:j + 1], s) for j, s in enumerate(seeds)])

            # Build per-step noise injection callback. When strength > 0 the
            # callback fires at every denoising step and adds noise × σ_i ×
            # strength, so injection is heaviest early and tapers to near-zero
            # as the sampler converges. None means no extra noise.
            noise_inject_cb = None
            if upscale_noise_inject_strength > 0.0:
                noise_inject_cb = cls._make_noise_inject_callback(
                    upscale_noise_inject_strength,
                    upscale_denoise, eff_scheduler, eff_steps,
                    final_model, seeds, console_log,
                )

            # The upscale pass uses the SAME batched positive/negative conditioning
            # that drove the first pass. This is intentional: the upscale is a
            # guided hi-res refinement, not an unconditional diffusion step.
            samples = comfy.sample.sample(
                final_model, upscale_noise, eff_steps, eff_cfg,
                eff_sampler, eff_scheduler,
                positive, negative_cond,
                upscaled,
                denoise=upscale_denoise,
                seed=seeds[0],
                callback=noise_inject_cb,
            )

        if console_log:
            print(f"  [Batch Wildcard Sampler] Complete: {batch_size} images in one batch per pass.")

        return io.NodeOutput(final_model, final_clip, vae, positive, negative_cond,
                             {"samples": samples}, positive_prompts)

    @classmethod
    def _prepare_batch(cls, model, clip, positives, negatives, strip_weights):
        """Encode each image with its own CLIP and build one per-image LoRA model."""
        files = folder_paths.get_filename_list("loras")
        log = is_lora_console_log_enabled()
        tags = [re.findall(TAG_PATTERN, prompt) for prompt in positives]
        parsed = [[(tag, spec) for tag in row
                   if (spec := parse_lora_tag(tag, True, files, log)) is not None]
                  for row in tags]
        # Merge the identical leading tags normally, preserving adapter ordering.
        # This also keeps the existing loader path for uniform DoRA/time tags.
        common = 0
        for entries in zip(*parsed):
            if not all(entry[1] == entries[0][1] for entry in entries):
                break
            common += 1
        if common:
            model, clip, _ = LoraTagLoader.execute(
                MODEL=model, CLIP=clip, STRING=" ".join(tag for tag, _ in parsed[0][:common]),
            ).result

        loaded = {}
        key_map = None
        model_keys = None
        slots = {}
        positive_conds, negative_conds = [], []
        for i, row in enumerate(parsed):
            image_clip = clip
            for _, spec in row[common:]:
                name, model_strength, clip_strength, ranges, scheduled, time_options = spec
                if model_strength != 0 and time_options is not None:
                    raise ValueError("Batch Wildcard Sampler: differing video time=/blend= LoRAs are not supported. "
                                     "Use identical leading time tags for all images.")
                if name not in loaded:
                    if key_map is None:
                        key_map = comfy.lora.model_lora_keys_unet(model.model, {})
                        key_map = comfy.lora.model_lora_keys_clip(clip.cond_stage_model, key_map)
                        model_keys = set(model.model.state_dict())
                    # Resolve both targets together once, as the standard loader
                    # does. Separate CLIP-only/model-only parsing reports the
                    # other target's valid keys as "not loaded" on every image.
                    loaded[name] = comfy.lora.load_lora(
                        comfy.lora_convert.convert_lora(load_lora_file(name)), key_map,
                    )
                patches = loaded[name]
                if clip_strength != 0:
                    image_clip = image_clip.clone()
                    image_clip.add_patches(patches, clip_strength)
                if model_strength != 0:
                    key = (name, ranges if scheduled else None)
                    if key not in slots:
                        slots[key] = [0.0] * len(positives)
                    slots[key][i] += model_strength
            pos = re.sub(TAG_PATTERN, "", positives[i])
            neg = _LORA_TAG_RE.sub("", negatives[i])
            if strip_weights:
                pos, neg = cls._strip_weight_syntax(pos), cls._strip_weight_syntax(neg)
            positive_conds.append(cls._encode(image_clip, pos))
            negative_conds.append(cls._encode(image_clip, neg))

        if slots:
            from ..utils.batch_lora import add_batch_loras
            model = add_batch_loras(model, [
                (name, {key: patch for key, patch in loaded[name].items()
                        if (key if isinstance(key, str) else key[0]) in model_keys}, ranges, strengths)
                for (name, ranges), strengths in slots.items()
            ], len(positives))
        # CLIP can represent only the common prefix; per-image CLIP changes are
        # already baked into the returned conditioning tensors.
        from ..utils.batch_anima import enable_anima_batching
        model = enable_anima_batching(model)
        return model, clip, positive_conds, negative_conds

    @staticmethod
    def _make_noise_inject_callback(strength, denoise, scheduler, steps, model_i, seeds, console_log=False):
        """
        Returns a per-step callback for comfy.sample.sample that injects
        scheduler-scaled Gaussian noise at every denoising step.

        At step i the injected magnitude is strength × σ_i, so injection is
        heaviest at the start (large sigma) and tapers to near-zero as the
        sampler converges (sigma → 0). The noise is seeded deterministically
        per image and step (image seed + step) for reproducibility.
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

        if console_log:
            print(f"  [Batch Wildcard Sampler] Upscale noise inject: strength={strength:.3f}, "
                  f"σ_start={active_sigmas[0].item():.4f}, σ_end={active_sigmas[-1].item():.4f}, "
                  f"active_steps={len(active_sigmas) - 1}")

        def callback(step, x0, x, total_steps):
            if step < len(active_sigmas) - 1:
                sigma_i = active_sigmas[step].item()
                gen = torch.Generator(device=x.device)
                noise_i = torch.cat([
                    torch.randn(x[j:j + 1].shape, generator=gen.manual_seed(s + step), device=x.device, dtype=x.dtype)
                    for j, s in enumerate(seeds)
                ])
                x.add_(noise_i, alpha=sigma_i * strength)

        return callback

    @classmethod
    def _run_upscale(cls, samples, upscale_width, upscale_height, vae, upscale_model, model_i):
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
        console_log = is_wildcard_console_log_enabled()

        # 1) Decode latent -> pixels.
        image = vae.decode(samples)  # NHWC (4D) or NTHWC (5D), values 0..1
        if console_log:
            print(f"  [Batch Wildcard Sampler] pixel upscale: latent {tuple(samples.shape)} "
                  f"-> decoded image {tuple(image.shape)}")

        # 2) Flatten any temporal/extra leading axis into the batch so we have a
        #    plain 4D NHWC batch of images.
        if image.ndim == 5:
            image = image.reshape(-1, image.shape[-3], image.shape[-2], image.shape[-1])

        # 3) Upscale in pixel space (Lanczos), or with an upscale model if connected.
        if upscale_model is not None:
            image = cls._upscale_with_model(upscale_model, image)
        image = image.movedim(-1, 1)  # NHWC -> NCHW
        image = comfy.utils.common_upscale(image, upscale_width, upscale_height, "lanczos", "disabled")
        image = image.movedim(1, -1).clamp(0.0, 1.0)  # NCHW -> NHWC

        # 4) Re-encode. Always hand the VAE a 4D NHWC image (same as the native VAE
        #    Encode node); the wrapper adds any temporal axis the VAE needs. A 3D
        #    VAE reads a 4D batch as the frames of one video, so there each image
        #    is encoded on its own.
        if console_log:
            print(f"  [Batch Wildcard Sampler] pixel upscale: encoding image {tuple(image.shape)}")
        if vae.latent_dim == 3:
            upscaled = torch.cat([vae.encode(image[i:i + 1, :, :, :3]) for i in range(image.shape[0])])
        else:
            upscaled = vae.encode(image[:, :, :, :3])
        if console_log:
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
        output is connected to anything.

        The output slot is resolved from the V3 schema so this keeps working if
        outputs are reordered later.

        Returns True/False when it can be determined, or None when the graph
        info is unavailable (e.g. API runs) so the caller can fall back to its
        default behaviour.
        """
        try:
            if not extra_pnginfo or unique_id is None:
                return None

            # Resolve the current latent slot from the declared output order.
            latent_slot = next(i for i, output in enumerate(BatchWildcardSampler.define_schema().outputs)
                               if output.display_name == "latent")

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
                    if str(link[1]) == node_id and link[2] == latent_slot:
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

    @staticmethod
    def _batch_conditioning(conds):
        """
        Stack single-prompt conditionings into one conditioning with one entry
        per batch index, so a single sampler call gives every image its own prompt.

        Prompts encode to different token lengths, so shorter conds are padded to
        the longest. When every length divides the longest (e.g. CLIP's 77-token
        chunks) the cond is repeated, which is how ComfyUI itself pads
        cross-attention conds for batching. Otherwise it is zero-padded, and when
        the text encoder returned an attention mask the padding is masked out for
        models that read it (e.g. Qwen-Image).
        """
        entries = [cond[0] for cond in conds]
        # Anima's IDs/weights are 1D token sequences, not batch-first tensors.
        # Core unconditionally unsqueezes them, so preserve the original prompt
        # inputs for our model-local extra_conds adapter instead of stacking IDs.
        if any("t5xxl_ids" in extra for _, extra in entries):
            from ..utils.batch_anima import PROMPTS_KEY
            prompts = []
            for embedding, extra in entries:
                ids = extra.get("t5xxl_ids")
                weights = extra.get("t5xxl_weights")
                if not torch.is_tensor(ids) or ids.ndim != 1:
                    raise ValueError("Anima batching expects a 1D token ID sequence for each image.")
                if weights is None:
                    weights = torch.ones_like(ids, dtype=embedding.dtype)
                if weights.shape != ids.shape:
                    raise ValueError("Anima token IDs and weights must have matching lengths.")
                prompts.append((embedding, ids, weights))
            # Placeholder is replaced after the diffusion model is loaded.
            # The output MODEL carries the matching preprocessing adapter.
            placeholder = torch.cat([embedding[:, :1] for embedding, _ in entries])
            return [[placeholder, {PROMPTS_KEY: prompts}]]
        max_len = max(cond.shape[1] for cond, _ in entries)
        use_mask = any("attention_mask" in extra for _, extra in entries)
        repeat = not use_mask and all(max_len % cond.shape[1] == 0 for cond, _ in entries)

        tensors = []
        masks = []
        for cond, extra in entries:
            if repeat:
                tensors.append(cond.repeat(1, max_len // cond.shape[1], 1))
                continue
            tensors.append(F.pad(cond, (0, 0, 0, max_len - cond.shape[1])))
            if use_mask:
                mask = extra.get("attention_mask")
                if mask is None:
                    mask = torch.ones(cond.shape[:2], dtype=torch.long, device=cond.device)
                masks.append(F.pad(mask, (0, max_len - mask.shape[1])))

        out = {}
        for key in set().union(*(extra.keys() for _, extra in entries)) - {"attention_mask"}:
            values = [extra.get(key) for _, extra in entries]
            if all(torch.is_tensor(value) and value.ndim > 0 and value.shape[0] == 1
                   for value in values):
                if key in ("conditioning_llama3", "conditioning_byt5small"):
                    # These auxiliary encoders place tokens on the penultimate axis.
                    length = max(value.shape[-2] for value in values)
                    values = [F.pad(value, (0, 0, 0, length - value.shape[-2])) for value in values]
                if not all(value.shape[1:] == values[0].shape[1:] for value in values):
                    raise ValueError(f"Cannot batch conditioning metadata '{key}' with differing shapes.")
                out[key] = torch.cat(values)
            elif all(comfy.conds.is_equal(value, values[0]) for value in values[1:]):
                out[key] = values[0]
            else:
                raise ValueError(f"Cannot batch differing conditioning metadata '{key}'.")
        if use_mask:
            out["attention_mask"] = torch.cat(masks)
        return [[torch.cat(tensors), out]]





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
