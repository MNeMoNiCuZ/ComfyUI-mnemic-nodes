import os
import importlib.util
import numpy as np
import torch
from PIL import Image
import comfy.utils
import imageio
from tqdm import tqdm

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
visualizers_dir = os.path.join(current_dir, "audio_visualizers")

# Get a list of available visualizer scripts
def get_visualizer_scripts():
    if not os.path.exists(visualizers_dir):
        return []
    return [f for f in os.listdir(visualizers_dir) if f.endswith(".py") and f != "__init__.py"]

class VideoData:
    def __init__(self, video_tensor, framerate):
        self.video = video_tensor
        self.framerate = framerate

    def get_dimensions(self):
        return self.video.shape[2], self.video.shape[1]

    def save_to(self, filename, format=None, codec=None, **kwargs):
        # Extract metadata from kwargs if present, but don't pass it to imageio
        metadata = kwargs.pop('metadata', None)
        if metadata is not None:
            # Metadata is extracted but not used by imageio writer
            pass

        # Try to infer format from filename extension
        if format == 'auto' or format is None:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext:
                format = file_ext[1:]
            else:
                format = 'mp4'
                if not filename.endswith('.mp4'):
                    filename += '.mp4'

        # Set a default codec if none is provided or if it's 'auto'
        if codec is None or codec == 'auto':
            if format == 'mp4':
                codec = 'libx264'
            elif format == 'webm':
                codec = 'libvpx-vp9'
            else:
                codec = 'libx264'  # Default fallback

        # Debug: Imageio writer configuration
        # fps={self.framerate}, format={format}, codec={codec}, kwargs={list(kwargs.keys())}

        try:
            writer = imageio.get_writer(filename, fps=self.framerate, format=format, codec=codec, **kwargs)
        except Exception as e:
            print(f"Error creating video writer: {e}")
            raise

        # Notify user that video encoding is starting
        total_frames = self.video.shape[0]
        print(f"🎬 Encoding {total_frames} frames into video")
        save_progress = tqdm(total=total_frames, desc=f"💾 Saving {os.path.basename(filename)}", unit="frame")

        for i, frame in enumerate(self.video):
            writer.append_data((frame.numpy() * 255).astype(np.uint8))
            save_progress.update(1)

        writer.close()
        save_progress.close()
        print(f"✅ Video saved successfully: {os.path.basename(filename)}")

class AudioVisualizer:
    """A node to create audio visualizations from an audio file."""
    def __init__(self):
        self.visualizers = {}
        self.load_visualizer_scripts()

    def load_visualizer_scripts(self):
        self.visualizers = {}
        for script_name in get_visualizer_scripts():
            try:
                spec = importlib.util.spec_from_file_location("visualizer", os.path.join(visualizers_dir, script_name))
                visualizer_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(visualizer_module)
                self.visualizers[script_name] = visualizer_module
            except Exception as e:
                print(f"Error loading visualizer script {script_name}: {e}")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "output_type": (["image", "image_batch", "video"], {"default": "video", "tooltip": "Choose the output type:\n\n'image' for a single frame. Use this option with the INCREMENT seed type and set the Batch Count to the number of frames you want to generate. Use this option to process each frame one at a time.\n\n 'image_batch' for all frames as separate images. Use this option together with the VHS Video Combine node, or for whenever you want each frame output at the same time. The audio can be added to this output node. WARNING: If this is output to a Preview Image node, keep in mind the total number of frames you will be generating! It can  make ComfyUI freeze or stutter.\n\n 'video' for an animated video file. Use this with the 'Save Video' native ComfyUI node to save as video."}),
                "visualizer_script": (get_visualizer_scripts(), {"tooltip": "Select the visualizer script to use for creating the audio visualization. Each script creates different visual patterns based on the audio waveform. You can also create your own visualizers and place them in /nodes/audio_visualizers/"}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "step": 0.1, "tooltip": "Scale factor that adjusts the visualizer's sensitivity to the audio amplitude. Higher values make the visualization more responsive to quieter sounds."}),
                "stereo_to_mono": (["mean", "left", "right"], {"tooltip": "Convert stereo audio to mono by taking the mean of both channels, using only the left channel, or using only the right channel."}),
                "framerate": ("INT", {"default": 30, "min": 1, "max": 240, "tooltip": "The framerate (frames per second) for video output. Higher values create smoother motion but increase processing time."}),
                "audio": ("AUDIO", {"tooltip": "The audio file to visualize. This contains the waveform and sample rate data."}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 64, "tooltip": "The width of the output in pixels. Larger values provide higher resolution but use more memory."}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 64, "tooltip": "The height of the output in pixels. Larger values provide higher resolution but use more memory."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Set to 0 and use 'Control After Generate: Increment' to cycle through frames for the image output.\n\nThis is not really used as a seed, but as a hack to get the incrementing node behavior and a starting frame."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "VIDEO")
    RETURN_NAMES = ("image", "image_batch", "video")
    OUTPUT_TOOLTIPS = (
        "Single frame image output. Set Seed to 0 and Control After Generate to Increment to cycle through frames. Connect to image processing nodes.",
        "Batch of all frames as separate images. Can be connected to the VHS Video Combine node for saving with audio. Make sure framerates match",
        "Animated video output. Can be connected to Save Video node for saving as video file."
    )
    FUNCTION = "visualize"
    CATEGORY = "⚡ MNeMiC Nodes"

    def visualize(self, output_type, visualizer_script, scale, stereo_to_mono, framerate, audio, width, height, seed):
        if not self.visualizers:
            self.load_visualizer_scripts()

        if visualizer_script not in self.visualizers:
            raise ValueError(f"Visualizer script {visualizer_script} not found.")

        visualizer_module = self.visualizers[visualizer_script]

        # audio is a dict with 'waveform' and 'sample_rate'
        audio_data = audio['waveform']
        sample_rate = audio['sample_rate']

        # If stereo, convert to mono
        if audio_data.shape[1] == 2:
            if stereo_to_mono == "mean":
                audio_data = torch.mean(audio_data, dim=1, keepdim=True)
            elif stereo_to_mono == "left":
                audio_data = audio_data[:, 0, :].unsqueeze(1)
            elif stereo_to_mono == "right":
                audio_data = audio_data[:, 1, :].unsqueeze(1)

        num_samples = audio_data.shape[2]
        duration_in_seconds = num_samples / sample_rate
        total_frames = int(duration_in_seconds * framerate)

        if output_type == "video":
            frames = []
            pbar = comfy.utils.ProgressBar(total_frames)

            # Use tqdm for progress bar
            progress_bar = tqdm(total=total_frames, desc=f"🎵 Audio Visualizer: {visualizer_script}", unit="frame")

            for i in range(total_frames):
                try:
                    # The visualizer script is expected to have a 'visualize' function
                    frame_np = visualizer_module.visualize(audio_data, i, framerate, width, height, scale)
                    frame_tensor = torch.from_numpy(frame_np).unsqueeze(0)
                    frames.append(frame_tensor)
                    pbar.update(1)
                    progress_bar.update(1)
                except Exception as e:
                    progress_bar.write(f"Error in visualizer script {visualizer_script}: {e}")
                    # Create a black frame as a fallback
                    black_frame_np = np.zeros((height, width, 3), dtype=np.float32)
                    black_frame_tensor = torch.from_numpy(black_frame_np).unsqueeze(0)
                    frames.append(black_frame_tensor)

            progress_bar.close()

            if not frames:
                # Create a black frame if there are no frames
                black_frame_np = np.zeros((height, width, 3), dtype=np.float32)
                black_frame_tensor = torch.from_numpy(black_frame_np).unsqueeze(0)
                frames.append(black_frame_tensor)

            video = torch.cat(frames, dim=0)
            return (None, None, VideoData(video, framerate))
        elif output_type == "image":
            # Use the seed as the frame number
            frame_number = seed % total_frames if total_frames > 0 else 0
            print(f"🎵 Audio Visualizer: {visualizer_script} > frame {frame_number + 1}/{total_frames}")
            try:
                frame_np = visualizer_module.visualize(audio_data, frame_number, framerate, width, height, scale)
                image = torch.from_numpy(frame_np).unsqueeze(0)
            except Exception as e:
                print(f"Error in visualizer script {visualizer_script}: {e}")
                # Create a black frame as a fallback
                black_frame_np = np.zeros((height, width, 3), dtype=np.float32)
                image = torch.from_numpy(black_frame_np).unsqueeze(0)
            return (image, None, None)
        elif output_type == "image_batch":
            frames = []
            pbar = comfy.utils.ProgressBar(total_frames)

            # Use tqdm for progress bar
            progress_bar = tqdm(total=total_frames, desc=f"🎵 Audio Visualizer: {visualizer_script}", unit="frame")

            for i in range(total_frames):
                try:
                    # The visualizer script is expected to have a 'visualize' function
                    frame_np = visualizer_module.visualize(audio_data, i, framerate, width, height, scale)
                    frame_tensor = torch.from_numpy(frame_np).unsqueeze(0)
                    frames.append(frame_tensor)
                    pbar.update(1)
                    progress_bar.update(1)
                except Exception as e:
                    progress_bar.write(f"Error in visualizer script {visualizer_script}: {e}")
                    # Create a black frame as a fallback
                    black_frame_np = np.zeros((height, width, 3), dtype=np.float32)
                    black_frame_tensor = torch.from_numpy(black_frame_np).unsqueeze(0)
                    frames.append(black_frame_tensor)

            progress_bar.close()

            if not frames:
                # Create a black frame if there are no frames
                black_frame_np = np.zeros((height, width, 3), dtype=np.float32)
                black_frame_tensor = torch.from_numpy(black_frame_np).unsqueeze(0)
                frames.append(black_frame_tensor)

            image_batch = torch.cat(frames, dim=0)
            return (None, image_batch, None)

NODE_CLASS_MAPPINGS = {
    "AudioVisualizer": AudioVisualizer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioVisualizer": "Audio Visualizer"
}