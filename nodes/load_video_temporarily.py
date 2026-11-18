import os

import folder_paths

from comfy_api.latest import InputImpl, io, ui

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
            ],
            outputs=[
                io.Video.Output(display_name="video", tooltip="The loaded video, for Save Video, Get Video Components and other video nodes."),
            ],
        )

    @classmethod
    def execute(cls, video) -> io.NodeOutput:
        if not video:
            raise ValueError("Select a video.")
        video_path = temp_file_path(video)
        name, _ = folder_paths.annotated_filepath(video)
        subfolder, _, filename = name.replace("\\", "/").rpartition("/")
        preview = ui.PreviewVideo([ui.SavedResult(filename, subfolder, io.FolderType.temp)])
        return io.NodeOutput(InputImpl.VideoFromFile(video_path), ui=preview)

    @classmethod
    def fingerprint_inputs(cls, video):
        if not video:
            return None
        # Hashing large videos is slow; the modification time is enough.
        return os.path.getmtime(temp_file_path(video))

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
