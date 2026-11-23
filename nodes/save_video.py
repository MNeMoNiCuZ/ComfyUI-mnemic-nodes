import os

import folder_paths
from comfy.cli_args import args
from comfy_extras.nodes_video import SaveVideo as NativeSaveVideo

from comfy_api.latest import Input, Types, io, ui

from ..utils.date_templates import resolve_filename_template

DEFAULT_FILENAME_PREFIX = "%Y-%m-%d/%Y-%m-%d - %H.%M.%S"


def _native_format_input():
    # Same format and codec choices as the native Save Video, kept in sync with it.
    return next(i for i in NativeSaveVideo.define_schema().inputs if i.id == "format")


class SaveVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_SaveVideo",
            display_name="💾 Save Video (MNeMiC)",
            category="⚡ MNeMiC Nodes",
            description="Saves a video to the output folder like the native Save Video, with date codes in the file name and the final prompt text stored in the file.",
            search_aliases=["save video", "export video", "video combine"],
            inputs=[
                io.Video.Input("video", tooltip="The video to save."),
                io.String.Input(
                    "filename_prefix",
                    default=DEFAULT_FILENAME_PREFIX,
                    tooltip="Path and name inside the output folder. Accepts strftime codes like %Y-%m-%d and %H.%M.%S, %date:yyyy-MM-dd% and %Node.widget% values. A / makes subfolders. The default for new nodes is set in Settings.",
                ),
                _native_format_input(),
                io.String.Input(
                    "positive_prompt",
                    force_input=True,
                    optional=True,
                    tooltip="Final positive prompt text, for example a wildcard processor or LLM output. Stored in the file's final_prompt tag.",
                ),
                io.String.Input(
                    "negative_prompt",
                    force_input=True,
                    optional=True,
                    tooltip="Final negative prompt text. Stored in the file's final_prompt tag.",
                ),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            is_output_node=True,
            outputs=[io.Video.Output("video", tooltip="The input video, unchanged.")],
        )

    @classmethod
    def execute(cls, video: Input.Video, filename_prefix: str, format: io.DynamicCombo.Type, positive_prompt: str | None = None, negative_prompt: str | None = None) -> io.NodeOutput:
        format_name = format["format"]
        codec = format.get("codec") or {"codec": "prores" if format_name == "mov" else "auto"}
        codec_name = codec["codec"]
        if format_name == "auto":
            format_name = {"av1": "webm", "prores": "mov"}.get(codec_name, "mp4")
        encoding = codec.get("encoding") or {}
        width, height = video.get_dimensions()
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            resolve_filename_template(filename_prefix),
            folder_paths.get_output_directory(),
            width,
            height,
        )
        metadata = None
        if not args.disable_metadata:
            metadata = {}
            if cls.hidden.extra_pnginfo is not None:
                metadata.update(cls.hidden.extra_pnginfo)
            if cls.hidden.prompt is not None:
                metadata["prompt"] = cls.hidden.prompt
            final_prompt = {}
            if positive_prompt is not None:
                final_prompt["positive"] = positive_prompt
            if negative_prompt is not None:
                final_prompt["negative"] = negative_prompt
            if final_prompt:
                metadata["final_prompt"] = final_prompt
            metadata = metadata or None
        file = f"{filename}_{counter:05}_.{Types.VideoContainer.get_extension(format_name)}"
        video.save_to(
            os.path.join(full_output_folder, file),
            format=Types.VideoContainer(format_name),
            codec=Types.VideoCodec(codec_name),
            metadata=metadata,
            crf=encoding.get("crf"),
        )
        return io.NodeOutput(video, ui=ui.PreviewVideo([ui.SavedResult(file, subfolder, io.FolderType.output)]))
