import os
from pathlib import Path

import folder_paths
from comfy_api.latest import io


class GetFilePath(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        input_dir = folder_paths.get_input_directory()
        try:
            files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        except OSError:
            files = []
        return io.Schema(
            node_id="MNeMiC_GetFilePath",
            display_name="📁 Get File Path",
            category="⚡ MNeMiC Nodes",
            description="Gets a file path and returns components of the file path.",
            inputs=[
                io.Combo.Input(
                    "image",
                    options=sorted(files),
                    upload=io.UploadType.image,
                    tooltip="Make sure to select any file type when uploading a non-image file.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="full_file_path", tooltip="The full path to the file"),
                io.String.Output(display_name="file_path_only", tooltip="The path to the file"),
                io.String.Output(display_name="file_name_only", tooltip="The name of the file"),
                io.String.Output(display_name="file_extension_only", tooltip="The extension of the file"),
            ],
        )

    @classmethod
    def execute(cls, image) -> io.NodeOutput:
        try:
            # Handle file upload within the node logic
            uploaded_file_path = cls.upload_file(image)

            # Resolve the full file path using folder_paths
            full_file_path = Path(uploaded_file_path)

            # Check if the file exists
            if not full_file_path.exists():
                print(f"Error: File does not exist: {full_file_path}")
                return io.NodeOutput(None, None, None, None)

            # Extract file components
            file_path_only = str(full_file_path.parent)
            file_name_only = full_file_path.stem  # File name without the extension
            file_extension_only = full_file_path.suffix  # File extension

            # Return all as strings
            return io.NodeOutput(
                str(full_file_path),  # Full file path
                file_path_only,  # Path only
                file_name_only,  # File name without extension
                file_extension_only,  # File extension
            )

        except Exception as e:
            # Handle any unexpected errors
            print(f"Error: Failed to process file path. Details: {str(e)}")
            return io.NodeOutput(None, None, None, None)

    @classmethod
    def upload_file(cls, image):
        try:
            # Define where to save uploaded files (e.g., input directory)
            input_dir = folder_paths.get_input_directory()
            file_path = os.path.join(input_dir, image)

            # Check if file already exists in the directory
            if os.path.exists(file_path):
                print(f"File {image} already exists in {input_dir}. Skipping upload.")
                return file_path

            # Mimic the upload logic
            with open(file_path, "wb") as f:
                # Here, you would write the file content to disk
                f.write(image)  # Assuming `file` contains the file data

            print(f"File uploaded successfully: {file_path}")
            return file_path

        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None
