import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import folder_paths
from comfy_api.latest import io

from .video_compare_diff import _save_frames, _video_parts


class ImageCompare(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        template = io.Autogrow.TemplateNames(
            io.MultiType.Input("media", types=[io.Image, io.Video], optional=True),
            names=[f"source_{i}" for i in range(1, 101)],
            min=2,
        )
        return io.Schema(
            node_id="MNeMiC_ImageCompare",
            display_name="Image Compare",
            category="⚡ MNeMiC Nodes",
            description="Compare images or video frames with a draggable split.",
            inputs=[io.Autogrow.Input("sources", template=template, optional=True)],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, sources=None):
        sources = {name: value for name, value in (sources or {}).items() if value is not None}
        if not sources:
            return io.NodeOutput(ui={"comparison": [dict(sources=[])]})
        folder = tempfile.mkdtemp(prefix="mnemic_compare_", dir=folder_paths.get_temp_directory())
        entries = []
        with ThreadPoolExecutor() as pool:
            for name, value in sorted(sources.items(), key=lambda item: int(item[0].split("_")[-1])):
                frames, fps, _ = _video_parts(value)
                if len(frames):
                    _save_frames(pool, frames, folder, name)
                    entries.append(dict(name=name, count=len(frames), fps=fps))
        return io.NodeOutput(ui={"comparison": [dict(folder=os.path.basename(folder), sources=entries)]})
