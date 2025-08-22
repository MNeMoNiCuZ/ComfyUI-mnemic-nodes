# 🎵 Audio Visualizer

A powerful ComfyUI node that creates stunning audio visualizations from audio files. Transform your music and sound into beautiful visual patterns using customizable visualizer scripts.

## ✨ Features

- **Output Types**: Single images, image batches, or animated videos
- **Flexible Audio Processing**: Support for stereo-to-mono conversion
- **Multiple Visualizer Options**: Choose from pre-built visualizers or create custom ones
- **Custom Visualizer Scripts**: Create your own visualization patterns

## 🎯 Output Types

The node supports three different output types, each serving different use cases:

### 🖼️ Image (Single Frame)
- **Purpose**: Generate a single frame from the audio at a specific point, use as an input source for image generation
- **Best For**: Previewing specific moments, testing visualizers, or batch processing individual frames
- **Usage Tip**: Set Seed to 0 and use `Control After Generate: Increment` to cycle through frames automatically
- **Connection**: Connect to image processing nodes or Preview Image

### 📚 Image Batch (All Frames)
- **Purpose**: Generate all frames as separate images simultaneously, use if your next node requires images in a batch, like VHS Video Combine
- **Best For**: Creating image sequences or connecting to video processing nodes
- **Usage Tip**: Use with `VHS Video Combine` node or when you need all frames at once
- **Warning**: Large audio files can create many frames - monitor your system's memory usage
- **Connection**: Connect to VHS Video Combine node (with audio as optional input)

### 🎬 Video (Animated)
- **Purpose**: Create smooth animated video files
- **Best For**: Final output videos, music videos, or any animated visualization
- **Usage Tip**: Connect directly to ComfyUI's native Save Video node
- **Connection**: Connect to Save Video node for file output

## ⚙️ Inputs

- **output_type**: Choose the output type - `image` for single frame, `image_batch` for all frames as images, or `video` for animated video
- **visualizer_script**: Select the visualizer script to use for creating the audio visualization
- **scale**: Scale factor that adjusts the visualizer's sensitivity to the audio amplitude
- **stereo_to_mono**: Convert stereo audio to mono by taking the mean of both channels, using only the left channel, or using only the right channel
- **framerate**: The framerate (frames per second) for video output
- **audio**: The audio file to visualize
- **width**: The width of the output in pixels
- **height**: The height of the output in pixels
- **seed**: Random seed used to determine which frame to output when using 'image' mode

## 🎨 Creating Custom Visualizer Scripts

The Audio Visualizer supports custom visualization scripts located in `/nodes/audio_visualizers/`. Each script must implement a `visualize` function with this signature:

```python
def visualize(audio_data, frame_number, framerate, width, height, scale):
    """
    Create a single frame visualization

    Parameters:
    - audio_data: Torch tensor containing audio waveform data
    - frame_number: Current frame being rendered (0-based)
    - framerate: Target framerate for the output
    - width: Output frame width in pixels
    - height: Output frame height in pixels
    - scale: Sensitivity scale factor (0.1+)

    Returns:
    - numpy array: RGB image data (height, width, 3) with values 0.0-1.0
    """
    # Your visualization logic here
    # Process audio_data to create visual patterns
    # Return numpy array with shape (height, width, 3)
    pass
```

### Script Requirements
- Must be a `.py` file in the `audio_visualizers` directory
- Must contain a `visualize` function with the exact signature above
- Should handle audio processing and frame generation
- Return numpy arrays with proper dimensions and value ranges

### Audio Data Structure
The `audio_data` parameter is a torch tensor with shape `(batch_size, channels, samples)`:
- **batch_size**: Usually 1 (single audio file)
- **channels**: 1 for mono, 2 for stereo (after conversion)
- **samples**: Total number of audio samples

### Example Script Structure
```python
import numpy as np
import torch

def visualize(audio_data, frame_number, framerate, width, height, scale):
    # Create empty RGB frame
    frame = np.zeros((height, width, 3), dtype=np.float32)

    # Get audio samples for current frame
    total_frames = int(audio_data.shape[2] / (audio_data.shape[2] / (framerate * duration)))
    samples_per_frame = audio_data.shape[2] // total_frames
    start_sample = frame_number * samples_per_frame
    end_sample = start_sample + samples_per_frame

    # Extract audio chunk for this frame
    audio_chunk = audio_data[0, 0, start_sample:end_sample]

    # Apply scale factor
    audio_chunk = audio_chunk * scale

    # Your visualization algorithm here
    # Example: Simple waveform visualization
    for x in range(width):
        if x < len(audio_chunk):
            y = int(height // 2 + audio_chunk[x] * height // 4)
            if 0 <= y < height:
                frame[y, x] = [1.0, 1.0, 1.0]  # White pixel

    return frame
```

## 📁 Existing Visualizer Scripts

The package includes several pre-built visualizer scripts:

### 🎵 Waveform Line (`waveform_line.py`)
- **Description**: Classic audio waveform visualization
- **Visual Style**: Horizontal waveform centered on screen

### 📊 Waveform Circular (`waveform_circular.py`)
- **Description**: Audio waveform arranged in a circle
- **Visual Style**: Circular waveform with center clearing

### 🎯 Umbrella (`umbrella.py`)
- **Description**: Circular bars visualization extending from the middle
- **Visual Style**: Vertical bars representing amplitude

### 🎨 Bouncing Bars (`bouncing_bars.py`)
- **Description**: Animated bars that bounce to the beat
- **Visual Style**: Dynamic bars with motion effects

### ✨ Particles (`particles.py`)
- **Description**: Particle-based visualization
- **Visual Style**: Moving particles responding to audio

## Performance Optimization
- Lower resolution reduces processing time and memory usage
- Use image mode for testing before committing to full video renders
- Umbrella is much slower than the other ones
