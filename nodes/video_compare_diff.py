import asyncio
import glob
import json
import os
import re
import shutil
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

from aiohttp import web
import folder_paths
import node_helpers
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

from comfy_api.latest import Input, InputImpl, Types, io

TEMP_SUBFOLDER = "mnemic_video_diff"
DEFAULT_FPS = 24.0
EXPORT_FOLDER = "video_compare_diff"

# The diff modes in the order of MODES in web/js/video_compare_diff.js.
DIFF_MODES = ["Difference", "Grayscale", "Heatmap", "Signed", "Threshold", "Blend"]
# The player's export settings, as sent in player_settings or by its Export button.
# start/end are a loop section in frames (None for the whole video); fps None uses the video's own rate.
EXPORT_DEFAULTS = {
    "mode": 0, "gain": 1.0, "threshold": 8, "swapped": False, "start": None, "end": None,
    "fps": None, "audio": None, "exports": "diff", "format": "mp4", "mask": "threshold",
}
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
# The diff shader's Turbo colormap approximation: per channel, coefficients of x^0 … x^5.
TURBO = np.array([
    [0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943],
    [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604],
    [0.10667330, 12.64194608, -60.58204836, 110.36276771, -89.90310912, 27.34824973],
], dtype=np.float32)


def _temp_media():
    """Video and image files in ComfyUI's temp folder, for the file pickers. Empty first, for no file."""
    # The temp folder does not exist until ComfyUI first writes to it, and a
    # failure here would take down the whole extension: schemas are built at load time.
    temp_dir = folder_paths.get_temp_directory()
    try:
        files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
    except OSError:
        files = []
    return [""] + sorted(folder_paths.filter_files_content_types(files, ["video", "image"]))


def _temp_file_path(name):
    """The path of a file chosen from the temp folder, refusing anything outside it."""
    temp_dir = folder_paths.get_temp_directory()
    path = folder_paths.get_annotated_filepath(name, default_dir=temp_dir)
    if not folder_paths.is_within_directory(temp_dir, path) or not os.path.isfile(path):
        raise ValueError(f"Temporary file not found: {name!r}. The temp folder is cleared when ComfyUI restarts; drop the file on the node again.")
    return path


def _load_image_file(path):
    """A still image as one frame, or an animated GIF/WebP as all its frames, with the animation's frame rate."""
    image = node_helpers.pillow(Image.open, path)
    frames = []
    for frame in ImageSequence.Iterator(image):
        frame = node_helpers.pillow(ImageOps.exif_transpose, frame)
        if frame.mode == "I":
            frame = frame.point(lambda i: i * (1 / 255))
        array = np.array(frame.convert("RGB"))
        # Frames must share a size to form a batch; Load Image skips the odd ones out too.
        if frames and array.shape != frames[0].shape:
            continue
        frames.append(array)
    duration = image.info.get("duration")
    rate = 1000.0 / duration if len(frames) > 1 and duration else None
    return torch.from_numpy(np.stack(frames).astype(np.float32) / 255.0), rate, None


def _video_parts(value):
    """The frames of an IMAGE or VIDEO input, and the video's frame rate and audio (None for an image batch)."""
    if isinstance(value, Input.Video):
        components = value.get_components()
        return components.images, float(components.frame_rate), components.audio
    return value, None, None


def _source(video, file, letter):
    """The connected input, or else the chosen temp file."""
    if video is not None:
        return _video_parts(video)
    if file:
        path = _temp_file_path(file)
        if folder_paths.filter_files_content_types([path], ["image"]):
            return _load_image_file(path)
        return _video_parts(InputImpl.VideoFromFile(path))
    raise ValueError(f"Video Compare Diff has no {letter}: connect a video or image to {letter}, or drop a file on the {letter} panel.")


def _save_audio(audio, path):
    """Write the first clip of an AUDIO as a 16-bit WAV for the player."""
    waveform = np.clip(audio["waveform"][0].float().cpu().numpy(), -1.0, 1.0)
    samples = np.ascontiguousarray((waveform * 32767).round().astype(np.int16).T)
    with wave.open(path, "wb") as file:
        file.setnchannels(samples.shape[1])
        file.setsampwidth(2)
        file.setframerate(int(audio["sample_rate"]))
        file.writeframes(samples.tobytes())


def _save_frames(pool, frames, folder, prefix):
    """Write every frame as a lossless PNG named <prefix>_00000.png, so the diff is exact."""
    def save(index):
        array = np.clip(255.0 * frames[index].cpu().numpy(), 0, 255).astype(np.uint8)
        Image.fromarray(array).save(os.path.join(folder, f"{prefix}_{index:05d}.png"), compress_level=1)
    list(pool.map(save, range(frames.shape[0])))


class VideoCompareDiff(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        files = _temp_media()
        return io.Schema(
            node_id="MNeMiC_VideoCompareDiff",
            display_name="🎞️ Video Compare Diff",
            category="⚡ MNeMiC Nodes",
            description="Plays two videos or images side by side with their difference, with several diff modes, scrubbing and loop sections. Connect them or drop files on it.",
            search_aliases=["video diff", "compare video", "video comparison", "image diff", "compare image", "difference", "a/b compare"],
            inputs=[
                io.MultiType.Input(
                    "video_a",
                    types=[io.Image, io.Video],
                    display_name="A",
                    optional=True,
                    tooltip="First video, as an image batch or a VIDEO. A VIDEO's sound can be played in the viewer. Overrides file_a.",
                ),
                io.MultiType.Input(
                    "video_b",
                    types=[io.Image, io.Video],
                    display_name="B",
                    optional=True,
                    tooltip="Second video, as an image batch or a VIDEO. A different size is stretched to A's size for the diff. Overrides file_b.",
                ),
                io.Combo.Input(
                    "file_a",
                    options=files,
                    default="",
                    tooltip="Video or image file for A when nothing is connected. Drop one on the A panel to upload it to ComfyUI's temp folder, which is cleared on restart.",
                ),
                io.Combo.Input(
                    "file_b",
                    options=files,
                    default="",
                    tooltip="Video or image file for B when nothing is connected. Drop one on the B panel to upload it to ComfyUI's temp folder, which is cleared on restart.",
                ),
                io.Boolean.Input(
                    "export_on_run",
                    default=False,
                    tooltip="Save the diff and/or mask every time the workflow runs, as set in the player's Export controls.",
                ),
                io.String.Input(
                    "filename_prefix",
                    default=f"{EXPORT_FOLDER}/compare",
                    tooltip="Where exports are saved, relative to the output folder, as in Save Image. Each export adds a number and _diff or _mask.",
                ),
                io.String.Input(
                    "player_settings",
                    default="",
                    tooltip="The player's diff and export settings, kept up to date by the player. Empty while export_on_run is off.",
                ),
            ],
            hidden=[io.Hidden.unique_id],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, file_a, file_b, export_on_run, filename_prefix, player_settings, video_a=None, video_b=None) -> io.NodeOutput:
        frames_a, rate_a, audio_a = _source(video_a, file_a, "A")
        frames_b, rate_b, audio_b = _source(video_b, file_b, "B")

        # Each run replaces this node's previous frames, so temp does not fill up with old runs.
        root = os.path.join(folder_paths.get_temp_directory(), TEMP_SUBFOLDER)
        node_key = re.sub(r"[^A-Za-z0-9]", "_", str(cls.hidden.unique_id))
        if os.path.isdir(root):
            for name in os.listdir(root):
                if name.startswith(f"{node_key}-"):
                    shutil.rmtree(os.path.join(root, name), ignore_errors=True)
        run_folder = f"{node_key}-{uuid.uuid4().hex[:12]}"
        folder = os.path.join(root, run_folder)
        os.makedirs(folder)

        with ThreadPoolExecutor() as pool:
            _save_frames(pool, frames_a, folder, "a")
            _save_frames(pool, frames_b, folder, "b")
        for name, audio in (("a", audio_a), ("b", audio_b)):
            if audio is not None:
                _save_audio(audio, os.path.join(folder, f"{name}.wav"))

        result = {
            "subfolder": f"{TEMP_SUBFOLDER}/{run_folder}",
            "frames_a": frames_a.shape[0],
            "frames_b": frames_b.shape[0],
            "fps": rate_a or rate_b or DEFAULT_FPS,
            "audio_a": audio_a is not None,
            "audio_b": audio_b is not None,
            "exported": [],
        }
        if export_on_run:
            try:
                settings = json.loads(player_settings) if player_settings else {}
            except json.JSONDecodeError as error:
                raise ValueError(f"Video Compare Diff: player_settings is not valid JSON: {error}") from None
            result["exported"] = _export(folder, _export_options(settings), filename_prefix, result["fps"])
        return io.NodeOutput(ui={"mnm_video_diff": [result]})

    @classmethod
    def fingerprint_inputs(cls, file_a="", file_b="", **kwargs):
        # A file dropped again under the same name must re-run.
        return [os.path.getmtime(_temp_file_path(name)) if name else None for name in (file_a, file_b)]

    @classmethod
    def validate_inputs(cls, file_a="", file_b=""):
        # Uploaded files are newer than the option list, so check the folder instead.
        for name in (file_a, file_b):
            if name:
                try:
                    _temp_file_path(name)
                except ValueError as e:
                    return str(e)
        return True


def _run_folder(subfolder):
    """The temp folder of one run of the node, refusing any other path."""
    temp_dir = folder_paths.get_temp_directory()
    folder = os.path.normpath(os.path.join(temp_dir, subfolder))
    if os.path.dirname(folder) != os.path.normpath(os.path.join(temp_dir, TEMP_SUBFOLDER)) or not os.path.isdir(folder):
        raise ValueError("These frames are gone. Run the workflow again, then export.")
    return folder


def _load_frame(folder, prefix, index, size=None):
    """One of a run's frames as RGB floats, stretched to `size` (width, height) when given."""
    with Image.open(os.path.join(folder, f"{prefix}_{index:05d}.png")) as image:
        image = image.convert("RGB")
        if size and image.size != size:
            image = image.resize(size, Image.Resampling.NEAREST)
        return np.asarray(image, dtype=np.float32) / 255.0


def _render(first, second, kind, options):
    """One exported frame: the diff as the player's Diff panel draws it, or the mask."""
    d = np.abs(first - second)
    largest = d.max(axis=-1)
    # Compare whole 0-255 levels, so a difference equal to the threshold is never marked.
    marked = np.rint(largest * 255.0) > options["threshold"]
    gain = options["gain"]
    if kind == "mask":
        if options["mask"] == "soft":
            return np.clip(largest * gain, 0.0, 1.0)
        return marked.astype(np.float32)
    mode = options["mode"]
    if mode == "Difference":
        color = d * gain
    elif mode == "Grayscale":
        color = np.repeat((d @ LUMA)[..., None] * gain, 3, axis=-1)
    elif mode == "Heatmap":
        x = np.clip(largest * gain, 0.0, 1.0)[..., None, None]
        color = (x ** np.arange(6, dtype=np.float32) * TURBO).sum(axis=-1)
    elif mode == "Signed":
        color = 0.5 + (second - first) * gain * 0.5
    elif mode == "Threshold":
        color = np.where(marked[..., None], np.array([1.0, 0.15, 0.15], dtype=np.float32), (first @ LUMA)[..., None] * 0.5)
    else:
        color = (first + second) * 0.5
    return np.clip(color, 0.0, 1.0)


def _to_image(array):
    """A rendered frame as an 8-bit image: RGB for a diff, grayscale for a mask."""
    return Image.fromarray(np.clip(array * 255.0 + 0.5, 0, 255).astype(np.uint8))


def _read_audio(path, start, duration):
    """A stretch of the player's WAV, in seconds, as an AUDIO; None when it has no samples there."""
    with wave.open(path, "rb") as file:
        rate, channels = file.getframerate(), file.getnchannels()
        file.setpos(min(int(start * rate), file.getnframes()))
        samples = np.frombuffer(file.readframes(int(duration * rate)), dtype=np.int16).reshape(-1, channels)
    if not len(samples):
        return None
    return {"waveform": torch.from_numpy(samples.T.astype(np.float32) / 32767.0)[None], "sample_rate": rate}


def _export_options(data):
    """The player's diff and export settings, checked. Missing ones use the player's defaults."""
    options = {**EXPORT_DEFAULTS, **data}

    def choice(key, allowed):
        if options[key] not in allowed:
            raise ValueError(f"Video Compare Diff: unknown {key} {options[key]!r}.")
        return options[key]

    mode = int(options["mode"])
    fps = None if options["fps"] is None else float(options["fps"])
    if not 0 <= mode < len(DIFF_MODES) or (fps is not None and not fps > 0):
        raise ValueError("Video Compare Diff: invalid diff mode or frame rate.")
    return {
        "mode": DIFF_MODES[mode],
        "gain": float(options["gain"]),
        "threshold": int(options["threshold"]),
        "swapped": bool(options["swapped"]),
        "start": None if options["start"] is None else int(options["start"]),
        "end": None if options["end"] is None else int(options["end"]),
        "fps": fps,
        "audio": choice("audio", ("a", "b", None)),
        "exports": choice("exports", ("diff", "mask", "both")),
        "format": choice("format", ("mp4", "png")),
        "mask": choice("mask", ("threshold", "soft")),
    }


def _export(folder, options, filename_prefix, video_fps):
    """Save the diff and/or mask of a run's frames under the output folder. Returns the saved paths relative to it."""
    counts = {prefix: len(glob.glob(os.path.join(glob.escape(folder), f"{prefix}_*.png"))) for prefix in "ab"}
    if not all(counts.values()):
        raise ValueError("These frames are gone. Run the workflow again, then export.")
    # The left video is the first one in the diff, as in the player.
    first, second = ("b", "a") if options["swapped"] else ("a", "b")
    last = max(counts.values()) - 1
    start = min(max(options["start"] or 0, 0), last)
    end = last if options["end"] is None else min(max(options["end"], start), last)
    fps = options["fps"] or video_fps

    def frame(index, kind):
        # A shorter video holds its last frame, and the second is stretched to the first's size.
        image = _load_frame(folder, first, min(index, counts[first] - 1))
        other = _load_frame(folder, second, min(index, counts[second] - 1), (image.shape[1], image.shape[0]))
        return _render(image, other, kind, options)

    # The sound that plays in the player: the chosen video's, else the other one's.
    audio_path = None
    for name in (options["audio"], "a", "b"):
        if name and os.path.isfile(os.path.join(folder, f"{name}.wav")):
            audio_path = os.path.join(folder, f"{name}.wav")
            break

    full_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, folder_paths.get_output_directory())
    saved = []
    for kind in (("diff", "mask") if options["exports"] == "both" else (options["exports"],)):
        name = f"{filename}_{counter:05}_{kind}"
        if options["format"] == "png":
            if start == end:
                _to_image(frame(start, kind)).save(os.path.join(full_folder, f"{name}.png"))
                saved.append(os.path.join(subfolder, f"{name}.png"))
                continue
            os.makedirs(os.path.join(full_folder, name))
            for index in range(start, end + 1):
                _to_image(frame(index, kind)).save(os.path.join(full_folder, name, f"frame_{index - start:05d}.png"))
            saved.append(os.path.join(subfolder, name, ""))
            continue

        first_frame = frame(start, kind)
        images = np.empty((end - start + 1, *first_frame.shape[:2], 3), dtype=np.float32)
        for offset, index in enumerate(range(start, end + 1)):
            rendered = first_frame if offset == 0 else frame(index, kind)
            images[offset] = rendered[..., None] if rendered.ndim == 2 else rendered
        audio = _read_audio(audio_path, start / fps, len(images) / fps) if audio_path else None
        components = Types.VideoComponents(images=torch.from_numpy(images), frame_rate=Fraction(fps).limit_denominator(1000), audio=audio)
        InputImpl.VideoFromComponents(components).save_to(os.path.join(full_folder, f"{name}.mp4"))
        saved.append(os.path.join(subfolder, f"{name}.mp4"))
    return saved


def register_video_compare_diff_routes():
    from server import PromptServer

    @PromptServer.instance.routes.post("/mnemic/video-compare-diff/export")
    async def export(request):
        """Export the frames the player shows right away, with its current settings."""
        try:
            data = await request.json()
            folder = _run_folder(str(data["subfolder"]))
            paths = await asyncio.to_thread(_export, folder, _export_options(data["settings"]),
                                            str(data["filename_prefix"]), DEFAULT_FPS)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return web.json_response({"error": str(error)}, status=400)
        return web.json_response({"paths": paths})
