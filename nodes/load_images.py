import os
import json
import asyncio
import base64
from io import BytesIO
import torch
import numpy as np
from PIL import Image

from comfy_api.latest import io


MAX_PATH_OUTPUTS = 32
PATH_FORMAT_LABELS = {
    "path only": "path",
    "path only with trailing separator": "path/",
    "filename without extension": "file",
    "filename only": "file.ext",
    "full file path without extension": "path/file",
    "full file path": "path/file.ext",
    "relative path only": "relative_path",
    "relative path only with trailing separator": "relative_path/",
    "relative file path without extension": "relative_path/file",
    "relative file path": "relative_path/file.ext",
}
LEGACY_PATH_FORMAT_LABELS = {
    "full file path": "full path with ext",
    "full file path without extension": "full path without ext",
    "path only": f"folder path without trailing {os.sep}",
    "path only with trailing separator": f"folder path with trailing {os.sep}",
    "filename only": "filename with ext",
    "filename without extension": "filename without ext",
    "relative file path": "relative path with ext",
    "relative file path without extension": "relative path without ext",
    "relative path only": f"relative folder without trailing {os.sep}",
    "relative path only with trailing separator": f"relative folder with trailing {os.sep}",
}
PATH_FORMATS = list(PATH_FORMAT_LABELS.values())
PATH_FORMAT_ALIASES = dict(PATH_FORMAT_LABELS)
# Normalize saved labels when a workflow moves between Windows and Unix.
for key, label in LEGACY_PATH_FORMAT_LABELS.items():
    PATH_FORMAT_ALIASES[label] = PATH_FORMAT_LABELS[key]
    if "trailing " in label:
        for separator in ("/", "\\"):
            PATH_FORMAT_ALIASES[label[:-1] + separator] = PATH_FORMAT_LABELS[key]
PATH_FORMAT_TOOLTIPS = dict(zip(PATH_FORMATS, [
    "Absolute containing folder, without a final slash. Drive roots keep their required slash.",
    f"Absolute containing folder, ending in {os.sep}.",
    "Filename with the final extension removed, without the folder path.",
    "Filename including its extension, without the folder path.",
    "Absolute folder path and filename, with the final extension removed.",
    "Absolute folder path and filename, including the extension.",
    "Containing folder relative to ComfyUI's input folder, without a final slash. The input folder itself is a dot.",
    f"Containing folder relative to ComfyUI's input folder, ending in {os.sep}.",
    "Folder path and filename relative to ComfyUI's input folder, with the final extension removed.",
    "Folder path and filename relative to ComfyUI's input folder, including the extension.",
]))
PATH_FORMAT_EXAMPLES = [
    "C:/",
    "C:/",
    "image",
    "image.png",
    "C:/image",
    "C:/image.png",
    ".",
    "./",
    "image",
    "image.png",
]
for label, example in zip(PATH_FORMATS, PATH_FORMAT_EXAMPLES):
    PATH_FORMAT_TOOLTIPS[label] += (
        "\nExample: " + example.replace("/", os.sep)
    )


def _find_images(input_path, include_subfolders=False, supported_exts=None):
    if supported_exts is None:
        supported_exts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']
    if not input_path:
        return []
    if not os.path.isabs(input_path):
        from folder_paths import get_input_directory
        input_dir = get_input_directory()
        if not input_dir or not os.path.isdir(input_dir):
            return []
        input_path = os.path.join(input_dir, input_path)
    if os.path.isdir(input_path):
        if include_subfolders:
            return sorted(
                os.path.join(root, filename)
                for root, _, filenames in os.walk(input_path)
                for filename in filenames
                if os.path.splitext(filename)[1].lower() in supported_exts
            )
        return [os.path.join(input_path, name) for name in sorted(os.listdir(input_path))
                if os.path.splitext(name)[1].lower() in supported_exts]
    if os.path.isfile(input_path) and os.path.splitext(input_path)[1].lower() in supported_exts:
        return [input_path]
    return []


def register_load_images_routes():
    from aiohttp import web
    from server import PromptServer

    def thumbnail(input_path, seed, include_subfolders, kind, text_extension, force_reload):
        text = ""
        if kind in ("pair_single", "pair_list"):
            from ..utils.file_utils import find_image_text_pairs, resolve_image_pair_path
            input_path = resolve_image_pair_path(input_path)
            if kind == "pair_list" and not force_reload:
                from . import load_text_image_pairs_list as pairs_module
                cached = pairs_module._CACHED_DATA
                if cached and pairs_module._CACHED_FOLDER_PATH == input_path:
                    batch = cached[4]
                    if len(batch):
                        pixels = batch[seed % len(batch)].cpu().numpy()
                        image = Image.fromarray(np.clip(pixels * 255, 0, 255).astype(np.uint8))
                        image.thumbnail((512, 512))
                        buffer = BytesIO()
                        image.save(buffer, format="PNG")
                        return buffer.getvalue(), cached[1][seed % len(batch)]
            pairs = find_image_text_pairs(input_path, text_extension)
            files = [pair[0] for pair in pairs]
            if pairs:
                text_path = pairs[seed % len(pairs)][1]
                if text_path:
                    with open(text_path, "r", encoding="utf-8") as caption:
                        text = caption.read()
        elif kind in ("metadata_single", "metadata_list"):
            from .metadata_extractor_single import METADATA_IMAGE_EXTENSIONS
            files = _find_images(input_path, supported_exts=METADATA_IMAGE_EXTENSIONS)
        elif kind == "images":
            files = _find_images(input_path, include_subfolders)
        else:
            raise ValueError("Unknown preview source.")
        if not files:
            return None, ""
        with Image.open(files[seed % len(files)]) as source:
            image = source.convert("RGB")
            image.thumbnail((512, 512))
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue(), text

    @PromptServer.instance.routes.get("/mnemic/load-images/preview")
    async def preview(request):
        try:
            body, text = await asyncio.to_thread(
                thumbnail, request.query.get("input_path", ""),
                int(request.query.get("seed", "0")),
                request.query.get("include_subfolders") == "true",
                request.query.get("kind", "images"),
                request.query.get("text_format_extension", "txt"),
                request.query.get("force_reload") == "true",
            )
        except (OSError, ValueError):
            return web.Response(status=400)
        if request.query.get("kind") in ("pair_single", "pair_list"):
            return web.json_response({
                "image": "data:image/png;base64," + base64.b64encode(body).decode("ascii") if body else None,
                "text": text,
            }, headers={"Cache-Control": "no-store"})
        return web.Response(body=body, status=200 if body else 404,
                            content_type="image/png", headers={"Cache-Control": "no-store"})


def _format_path(image_path, path_format):
    label = PATH_FORMAT_ALIASES.get(path_format, path_format)
    path_format = next((key for key, value in PATH_FORMAT_LABELS.items() if value == label), path_format)
    absolute_path = os.path.abspath(image_path)
    if path_format == "full file path":
        return absolute_path
    if path_format == "full file path without extension":
        return os.path.splitext(absolute_path)[0]
    if path_format in ("path only", "path only with trailing separator"):
        result = os.path.dirname(absolute_path)
    elif path_format == "filename only":
        return os.path.basename(absolute_path)
    elif path_format == "filename without extension":
        return os.path.splitext(os.path.basename(absolute_path))[0]
    elif path_format in PATH_FORMAT_LABELS and path_format.startswith("relative "):
        from folder_paths import get_input_directory
        target = os.path.dirname(absolute_path) if path_format.startswith("relative path only") else absolute_path
        try:
            result = os.path.relpath(target, get_input_directory())
        except ValueError as error:
            raise ValueError(
                "Relative formats require the image and ComfyUI's input folder "
                "to be on the same drive. Choose full file path for this image."
            ) from error
        if path_format == "relative file path without extension":
            return os.path.splitext(result)[0]
    else:
        raise ValueError(f"Unknown path/file format: {path_format}")
    # Preserve root separators: C: would mean a drive-relative path, not C:\\.
    return os.path.join(result, "") if path_format.endswith("with trailing separator") else result


def _node_output(image, mask, paths, current_index, total_count):
    # All configurable STRING sockets follow the image, mask and counters.
    padded = paths + [""] * (MAX_PATH_OUTPUTS - len(paths))
    return io.NodeOutput(image, mask, current_index, total_count, *padded)


class LoadImagesFromPath(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoadImagesFromPath",
            display_name="📂 Load Images From Path",
            category="⚡ MNeMiC Nodes",
            description="Loads a single image from a directory, allowing sequential iteration through the folder.",
            inputs=[
                io.Boolean.Input(
                    "include_subfolders",
                    default=False,
                    tooltip="Include images from all subfolders of the selected folder.",
                ),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the image to load, starting at 0. Increments every run by default to step through the folder.",
                ),
                io.String.Input(
                    "input_path",
                    multiline=False,
                    default="",
                    tooltip="Path to a folder containing images or a single image file.",
                ),
                io.Combo.Input(
                    "path_format",
                    display_name="output1",
                    options=PATH_FORMATS,
                    default=PATH_FORMAT_LABELS["full file path"],
                    tooltip=PATH_FORMAT_TOOLTIPS[PATH_FORMAT_LABELS["full file path"]],
                    extra_dict={"format_tooltips": PATH_FORMAT_TOOLTIPS, "format_aliases": PATH_FORMAT_ALIASES},
                ),
                io.String.Input(
                    "extra_path_formats", default="[]", optional=True,
                    tooltip="Formats for additional path/file outputs.",
                    extra_dict={"max_path_outputs": MAX_PATH_OUTPUTS},
                ),
            ],
            outputs=[
                io.Image.Output(display_name="image", tooltip="The image at the selected index."),
                io.Mask.Output(display_name="mask", tooltip="Alpha channel of the image, or fully black if it has none."),
                io.Int.Output(display_name="current_index", tooltip="Index actually loaded: the seed wrapped around the number of files found."),
                io.Int.Output(display_name="total_count", tooltip="How many images were found at the path."),
                *[
                    io.String.Output(display_name=f"output{index}", tooltip="The loaded image's path or filename in this output's selected format.")
                    for index in range(1, MAX_PATH_OUTPUTS + 1)
                ],
            ],
        )

    @classmethod
    def execute(cls, seed: int, input_path: str, path_format: str = "full file path", extra_path_formats: str = "[]", include_subfolders: bool = False) -> io.NodeOutput:
        try:
            extra_formats = json.loads(extra_path_formats)
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid path/file output formats.") from error
        if not isinstance(extra_formats, list) or len(extra_formats) >= MAX_PATH_OUTPUTS:
            raise ValueError(f"Choose up to {MAX_PATH_OUTPUTS} path/file outputs.")
        formats = [path_format, *extra_formats]
        if any(not isinstance(value, str) or PATH_FORMAT_ALIASES.get(value, value) not in PATH_FORMATS for value in formats):
            raise ValueError("Unknown path/file output format.")
        if not input_path:
            raise ValueError("Input path cannot be empty.")

        files_found = _find_images(input_path, include_subfolders)

        if not files_found:
            return _node_output(None, None, [], 0, 0)

        total_count = len(files_found)
        current_index = seed % total_count

        image_path = files_found[current_index]

        path_outputs = [_format_path(image_path, value) for value in formats]

        try:
            with Image.open(image_path) as img:
                img_rgb = img.convert("RGB")
                image_np = np.array(img_rgb).astype(np.float32) / 255.0
                image_tensor = torch.from_numpy(image_np).unsqueeze(0)

                if "A" in img.getbands():
                    mask_np = np.array(img.getchannel("A")).astype(np.float32) / 255.0
                    mask_tensor = torch.from_numpy(mask_np).unsqueeze(0)
                else:
                    mask_tensor = torch.zeros((1, image_tensor.shape[1], image_tensor.shape[2]), dtype=torch.float32)

        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return _node_output(None, None, [], current_index, total_count)

        return _node_output(image_tensor, mask_tensor, path_outputs, current_index, total_count)
