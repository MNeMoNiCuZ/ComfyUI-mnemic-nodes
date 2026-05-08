"""
Source reference:
https://github.com/KChronoKnight/Chrono-Save-for-Civitai
Adapted into ComfyUI-mnemic-nodes for the "Image Save With Metadata" node.
"""

import json
from typing import Any, cast

import piexif
import piexif.helper
from PIL.Image import Image
from PIL.PngImagePlugin import PngInfo


def save_image(
    image: Image,
    filepath: str,
    extension: str,
    quality_jpeg_or_webp: int,
    lossless_webp: bool,
    optimize_png: bool,
    a111_params: str,
    prompt: dict[str, Any] | None,
    extra_pnginfo: dict[str, Any] | None,
    embed_workflow: bool,
) -> None:
    if extension == "png":
        metadata = PngInfo()
        if a111_params:
            metadata.add_text("parameters", a111_params)

        if embed_workflow:
            if extra_pnginfo is not None:
                for k, v in extra_pnginfo.items():
                    metadata.add_text(k, json.dumps(v, separators=(",", ":")))
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt, separators=(",", ":")))

        image.save(filepath, pnginfo=metadata, optimize=optimize_png)
    else:
        image.save(filepath, optimize=True, quality=quality_jpeg_or_webp, lossless=lossless_webp)

        pnginfo_json = {}
        prompt_json = {}
        if embed_workflow:
            if extra_pnginfo is not None:
                pnginfo_json = {piexif.ImageIFD.Make - i: f"{k}:{json.dumps(v, separators=(',', ':'))}" for i, (k, v) in enumerate(extra_pnginfo.items())}
            if prompt is not None:
                prompt_json = {piexif.ImageIFD.Model: f"prompt:{json.dumps(prompt, separators=(',', ':'))}"}

        def get_exif_bytes() -> bytes:
            exif_dict = (
                {"0th": pnginfo_json | prompt_json} if pnginfo_json or prompt_json else {}
            ) | (
                {"Exif": {piexif.ExifIFD.UserComment: cast(bytes, piexif.helper.UserComment.dump(a111_params, encoding="unicode"))}}
                if a111_params
                else {}
            )
            return cast(bytes, piexif.dump(exif_dict))

        exif_bytes = get_exif_bytes()

        if extension in ("jpg", "jpeg"):
            max_exif_size = 65535
            if len(exif_bytes) > max_exif_size and embed_workflow:
                print("ComfyUI-Image-Saver: Error: Workflow is too large, removing client request prompt.")
                prompt_json = {}
                exif_bytes = get_exif_bytes()
                if len(exif_bytes) > max_exif_size:
                    print("ComfyUI-Image-Saver: Error: Workflow is still too large, cannot embed workflow!")
                    pnginfo_json = {}
                    exif_bytes = get_exif_bytes()
            if len(exif_bytes) > max_exif_size:
                print("ComfyUI-Image-Saver: Error: Metadata exceeds maximum size for JPEG. Cannot save metadata.")
                return

        piexif.insert(exif_bytes, filepath)
