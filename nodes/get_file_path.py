import os
from pathlib import Path
from aiohttp import web
import folder_paths

class GetFilePath:
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("full_file_path", "file_path_only", "file_name_only", "file_extension_only")
    OUTPUT_TOOLTIPS = ("The full path to the file", "The path to the file", "The name of the file", "The extension of the file")
    FUNCTION = "get_file_path"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Gets a file path and returns components of the file path."
    DOCUMENTATION = "This is documentation"

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "file": (sorted(files), {"file_upload": True, "tooltip": "Place your files in the 'input'-folder inside ComfyUI.\n\nBrowsing functionality is not yet supported. Please send help!"}),
            }
        }

    def get_file_path(self, file):
        try:
            # Handle file upload within the node logic
            uploaded_file_path = self.upload_file(file)

            # Resolve the full file path using folder_paths
            full_file_path = Path(uploaded_file_path)

            # Check if the file exists
            if not full_file_path.exists():
                print(f"Error: File does not exist: {full_file_path}")
                return None, None, None, None

            # Extract file components
            file_path_only = str(full_file_path.parent)
            file_name_only = full_file_path.stem  # File name without the extension
            file_extension_only = full_file_path.suffix  # File extension

            # Return all as strings
            return (
                str(full_file_path),  # Full file path
                file_path_only,  # Path only
                file_name_only,  # File name without extension
                file_extension_only,  # File extension
            )

        except Exception as e:
            # Handle any unexpected errors
            print(f"Error: Failed to process file path. Details: {str(e)}")
            return None, None, None, None

    def upload_file(self, file):
        try:
            # Define where to save uploaded files (e.g., input directory)
            input_dir = folder_paths.get_input_directory()
            file_path = os.path.join(input_dir, file)

            # Check if file already exists in the directory
            if os.path.exists(file_path):
                print(f"File {file} already exists in {input_dir}. Skipping upload.")
                return file_path

            # Mimic the upload logic
            with open(file_path, "wb") as f:
                # Here, you would write the file content to disk
                f.write(file)  # Assuming `file` contains the file data

            print(f"File uploaded successfully: {file_path}")
            return file_path

        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None
