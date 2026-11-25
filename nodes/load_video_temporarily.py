import os
from fractions import Fraction

import folder_paths

from comfy_api.latest import InputImpl, Types, io, ui

from .load_image_temporarily import temp_file_path, temp_files


class LoadVideoTemporarily(io.ComfyNode):
    """
    Loads a video and stores it in ComfyUI /temp-folder instead of the /input folder.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        files = temp_files(["video"])
        return io.Schema(
            node_id="MNeMiC_LoadVideoTemporarily",
            display_name="🎞️ Load Video Temporarily",
            category="⚡ MNeMiC Nodes",
            description="Loads a video and stores it in ComfyUI /temp-folder instead of the /input folder.",
            has_intermediate_output=True,
            inputs=[
                io.Combo.Input(
                    "video",
                    options=files,
                    upload=io.UploadType.video,
                    image_folder=io.FolderType.temp,
                    tooltip="Video to load from ComfyUI's temp folder. Uploads through this node go to temp instead of input, so they are cleared when ComfyUI restarts.",
                ),
                io.Float.Input("framerate", default=0.0, min=0.0, max=240.0, step=0.01, tooltip="0 uses the source frame rate. A positive value drops or repeats frames to keep the original timing."),
            ],
            outputs=[
                io.Video.Output(display_name="video", tooltip="The loaded video, for Save Video, Get Video Components and other video nodes."),
                io.Image.Output(display_name="images", tooltip="Video frames in playback order at the selected frame rate."),
                io.Audio.Output(display_name="audio", tooltip="The source audio track, if present."),
            ],
        )

    @classmethod
    def execute(cls, video, framerate=0.0) -> io.NodeOutput:
        if not video:
            raise ValueError("Select a video.")
        video_path = temp_file_path(video)
        name, _ = folder_paths.annotated_filepath(video)
        subfolder, _, filename = name.replace("\\", "/").rpartition("/")
        preview = ui.PreviewVideo([ui.SavedResult(filename, subfolder, io.FolderType.temp)])
        loaded = InputImpl.VideoFromFile(video_path)
        components = loaded.get_components()
        images = components.images
        if framerate:
            target_rate = Fraction(str(framerate))
            if target_rate != components.frame_rate:
                ratio = components.frame_rate / target_rate
                count = max(1, round(len(images) / ratio))
                indices = [(i * ratio.numerator) // ratio.denominator for i in range(count)]
                images = images[indices]
                loaded = InputImpl.VideoFromComponents(Types.VideoComponents(
                    images=images, frame_rate=target_rate, audio=components.audio,
                ))
        return io.NodeOutput(loaded, images, components.audio, ui=preview)

    @classmethod
    def fingerprint_inputs(cls, video, framerate=0.0):
        if not video:
            return None
        # Hashing large videos is slow; the modification time is enough.
        return os.path.getmtime(temp_file_path(video)), framerate

    @classmethod
    def validate_inputs(cls, video):
        # An empty selection may belong to an unused lazy branch.
        if not video:
            return True
        try:
            temp_file_path(video)
        except ValueError as e:
            return str(e)
        return True
