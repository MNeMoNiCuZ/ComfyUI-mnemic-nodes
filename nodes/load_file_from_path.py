import os
import json
import asyncio
import logging
import re
import numpy as np
import torch
from PIL import Image, ImageOps
from aiohttp import web

import folder_paths
from comfy_api.latest import InputImpl, io
from comfy_extras.nodes_audio import load as load_audio

from .load_images import _find_images


MAX_FILE_OUTPUTS = 16
# Output type per row type. The schema declares the outputs as any type; the
# node's JS sets each output's real type from its row.
FILE_TYPES = {
    "image": "IMAGE",
    "mask": "MASK",
    "text": "STRING",
    "audio": "AUDIO",
    "video": "VIDEO",
    "path": "STRING",
}
TYPE_TOOLTIPS = {
    "image": "The file as an image. Animated files give their first frame.",
    "mask": "The image's alpha channel, or fully black if it has none.",
    "text": "The file's text, read as UTF-8.",
    "audio": "The file's audio, for any format ComfyUI can decode.",
    "video": "The file as a video, for any format ComfyUI can decode.",
    "path": "The file's full path, for formats no other type loads.",
}
DEFAULT_FILES = json.dumps([{"extension": "png", "type": "image"}, {"extension": "txt", "type": "text"}])


def _row_extensions(text):
    """'.png, JPG webp' -> ['.png', '.jpg', '.webp']. Commas, spaces and | separate them."""
    return ["." + ext.lstrip(".").lower() for ext in re.split(r"[\s,|]+", text) if ext.lstrip(".")]


def _extension_label(extensions):
    """[".png", ".jpg"] -> "png/jpg" for messages."""
    return "/".join(ext[1:] for ext in extensions)


def _parse_files(files):
    """The rows as (extensions, type) pairs. Raises a clear error for bad rows."""
    try:
        rows = json.loads(files)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid file outputs.") from error
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FILE_OUTPUTS:
        raise ValueError(f"Choose between 1 and {MAX_FILE_OUTPUTS} file outputs.")
    parsed = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.get("type") not in FILE_TYPES or not isinstance(row.get("extension"), str):
            raise ValueError(f"File output {number} is invalid.")
        extensions = _row_extensions(row["extension"])
        if not extensions:
            raise ValueError(f"File output {number} has no extension.")
        parsed.append((extensions, row["type"]))
    return parsed


def _scan(input_path, include_subfolders, rows):
    """Returns (sets, counts, complete).

    sets: every file name with a file for the first row, sorted, as
    (name, files) with one file per row, None where a row has none.
    counts: per row, how many file names have a file for it.
    complete: how many file names have a file for every row.
    """
    if not os.path.isabs(input_path):
        input_path = os.path.join(folder_paths.get_input_directory(), input_path)
    extensions = {ext for row_extensions, _ in rows for ext in row_extensions}
    if os.path.isfile(input_path):
        stem = os.path.splitext(input_path)[0]
        files = [path for path in _find_images(os.path.dirname(input_path), False, extensions)
                 if os.path.splitext(path)[0] == stem]
    else:
        files = _find_images(input_path, include_subfolders, extensions)
    by_stem = {}
    for path in files:
        stem, ext = os.path.splitext(path)
        by_stem.setdefault(stem, {})[ext.lower()] = path
    sets = []
    counts = [0] * len(rows)
    complete = 0
    for stem in sorted(by_stem):
        found = by_stem[stem]
        chosen = [next((found[ext] for ext in row_extensions if ext in found), None) for row_extensions, _ in rows]
        for index, path in enumerate(chosen):
            counts[index] += path is not None
        complete += None not in chosen
        if chosen[0] is not None:
            sets.append((stem, chosen))
    return sets, counts, complete


def register_load_file_routes():
    from server import PromptServer

    @PromptServer.instance.routes.get("/mnemic/load-file/counts")
    async def counts(request):
        """Per-row file counts for the node's extension labels."""
        input_path = request.query.get("input_path", "")
        try:
            extensions = json.loads(request.query.get("extensions", "[]"))
            if not input_path or not isinstance(extensions, list):
                raise ValueError("Missing path or extensions.")
            rows = [(_row_extensions(str(text)), None) for text in extensions[:MAX_FILE_OUTPUTS]]
            _, row_counts, complete = await asyncio.to_thread(
                _scan, input_path, request.query.get("include_subfolders") == "true", rows)
        except (OSError, ValueError):
            return web.Response(status=400)
        return web.json_response({"counts": row_counts, "complete": complete}, headers={"Cache-Control": "no-store"})


def _load_image(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        pixels = torch.from_numpy(np.array(image.convert("RGB")).astype(np.float32) / 255.0).unsqueeze(0)
        if "A" in image.getbands():
            mask = torch.from_numpy(np.array(image.getchannel("A")).astype(np.float32) / 255.0).unsqueeze(0)
        else:
            mask = torch.zeros((1, pixels.shape[1], pixels.shape[2]), dtype=torch.float32)
    return pixels, mask


def _load(path, file_type):
    if file_type in ("image", "mask"):
        return _load_image(path)[0 if file_type == "image" else 1]
    if file_type == "text":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as file:
            return file.read()
    if file_type == "audio":
        waveform, sample_rate = load_audio(path)
        return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
    if file_type == "video":
        return InputImpl.VideoFromFile(path)
    return os.path.abspath(path)


def _empty(file_type, height, width):
    """A stand-in for a missing file, so nodes downstream keep running."""
    if file_type == "image":
        return torch.zeros((1, height, width, 3), dtype=torch.float32)
    if file_type == "mask":
        return torch.zeros((1, height, width), dtype=torch.float32)
    if file_type == "audio":
        return {"waveform": torch.zeros((1, 1, 1), dtype=torch.float32), "sample_rate": 44100}
    if file_type == "video":
        return None
    return ""


class LoadFileFromPath(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoadFileFromPath",
            display_name="📂 Load File From Path",
            category="⚡ MNeMiC Nodes",
            description="Loads a file and its matching files from a folder by seed, such as an image and its caption, each as the type you choose.",
            search_aliases=["load file", "load text image pair", "load audio from path", "load video from path"],
            inputs=[
                io.Boolean.Input(
                    "include_subfolders",
                    default=False,
                    tooltip="Include files from all subfolders of the selected folder.",
                ),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=io.ControlAfterGenerate.increment,
                    tooltip="Index of the file name to load, starting at 0 and wrapping at the count. Increments every run by default.",
                ),
                io.String.Input(
                    "input_path",
                    multiline=False,
                    default="",
                    tooltip="Folder to load from, or one file to load it and its matching files. Relative paths start at ComfyUI's input folder.",
                ),
                io.String.Input(
                    "files", default=DEFAULT_FILES, optional=True,
                    tooltip="The file outputs: an extension and a type per output.",
                    extra_dict={"max_file_outputs": MAX_FILE_OUTPUTS, "file_types": FILE_TYPES, "type_tooltips": TYPE_TOOLTIPS},
                ),
            ],
            outputs=[
                io.String.Output(display_name="name", tooltip="The shared file name, without folder or extension."),
                io.Int.Output(display_name="current_index", tooltip="Index actually loaded: the seed wrapped around the count."),
                io.Int.Output(display_name="total_count", tooltip="How many files the first output found. The seed wraps at this count."),
                *[
                    io.AnyType.Output(display_name=f"output{index}", tooltip="The file for this output, loaded as its chosen type.")
                    for index in range(1, MAX_FILE_OUTPUTS + 1)
                ],
            ],
        )

    @classmethod
    def execute(cls, seed: int, input_path: str, files: str = DEFAULT_FILES, include_subfolders: bool = False) -> io.NodeOutput:
        rows = _parse_files(files)
        if not input_path:
            raise ValueError("Input path cannot be empty.")
        sets, _, _ = _scan(input_path, include_subfolders, rows)
        if not sets:
            logging.warning(f"[Load File From Path] No {_extension_label(rows[0][0])} files in {input_path}. The outputs are empty.")
            stem, current_index, paths = "", 0, [None] * len(rows)
        else:
            current_index = seed % len(sets)
            stem, paths = sets[current_index]

        values = [_load(path, file_type) if path else None for path, (_, file_type) in zip(paths, rows)]
        missing = [_extension_label(extensions) for path, (extensions, _) in zip(paths, rows) if path is None]
        if sets and missing:
            logging.warning(f"[Load File From Path] {os.path.basename(stem)} has no {', '.join(missing)} file. Those outputs are empty.")
        # Missing images and masks take the size of a loaded one, so they can be combined with it.
        size = next(((value.shape[1], value.shape[2]) for value in values if isinstance(value, torch.Tensor)), (64, 64))
        values = [_empty(file_type, *size) if path is None else value for value, path, (_, file_type) in zip(values, paths, rows)]
        values += [None] * (MAX_FILE_OUTPUTS - len(values))
        return io.NodeOutput(os.path.basename(stem), current_index, len(sets), *values)
