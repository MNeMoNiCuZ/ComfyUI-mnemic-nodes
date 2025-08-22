import numpy as np
from PIL import Image, ImageDraw
import librosa
import math

bars = []

def visualize(audio_data, frame, framerate, width, height, scale=1.0):
    global bars
    audio_data = audio_data.squeeze().numpy()

    # Get current audio chunk for amplitude
    num_samples = audio_data.shape[0]
    start_sample = int((frame / framerate) * 44100)
    end_sample = int(((frame + 1) / framerate) * 44100)

    if start_sample >= num_samples:
        start_sample = num_samples - 1
    if end_sample > num_samples:
        end_sample = num_samples

    chunk = audio_data[start_sample:end_sample] if start_sample < end_sample else audio_data[max(0, num_samples-100):num_samples]

    # Create bars based on actual audio samples
    if len(chunk) > 0:
        # Divide chunk into segments for bars
        num_bars = min(20, len(chunk) // 8)  # Limit bar count
        samples_per_bar = len(chunk) // num_bars if num_bars > 0 else 1

        for i in range(num_bars):
            start_idx = i * samples_per_bar
            end_idx = min((i + 1) * samples_per_bar, len(chunk))

            if start_idx < len(chunk):
                bar_chunk = chunk[start_idx:end_idx]
                amplitude = np.mean(np.abs(bar_chunk)) * scale

                # Only create bar if amplitude is significant
                if amplitude > 0.01:
                    bar_x = i * (width // num_bars) + 5
                    bar_height = int(amplitude * height * 0.6)
                    bar_height = min(bar_height, height) # Clamp bar height

                    # Color based on amplitude
                    intensity = min(1.0, amplitude * 3)
                    if intensity < 0.3:
                        color = (int(255 * intensity), int(100 * intensity), int(100 * intensity))
                    elif intensity < 0.7:
                        color = (int(100 * intensity), int(255 * intensity), int(100 * intensity))
                    else:
                        color = (int(100 * intensity), int(100 * intensity), int(255 * intensity))

                    bars.append({
                        "x": bar_x,
                        "y": height,
                        "target_height": bar_height,
                        "current_height": 0,
                        "color": color,
                        "width": max(4, width // num_bars - 10),
                        "life": 60,  # Frames to live
                        "alpha": 255,
                        "velocity": 0
                    })

    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)

    # Update and draw bars
    for bar in bars:
        # Smooth height changes
        height_diff = bar["target_height"] - bar["current_height"]
        bar["velocity"] += height_diff * 0.1
        bar["velocity"] *= 0.8  # Damping
        bar["current_height"] += bar["velocity"]

        # Fade out over time
        bar["life"] -= 1
        bar["alpha"] = max(0, int(255 * (bar["life"] / 60)))

        # Ensure bar doesn't go below 0
        bar["current_height"] = max(0, bar["current_height"])

        # Draw the bar if it has height and is visible
        if bar["current_height"] > 2 and bar["alpha"] > 0:
            bar_top = int(height - bar["current_height"])
            bar_bottom = height

            # Create color with alpha
            r, g, b = bar["color"]
            bar_color = (r, g, b, bar["alpha"])

            # Main bar
            draw.rectangle((bar["x"], bar_top, bar["x"] + bar["width"], bar_bottom), fill=bar_color)

            # Add glow effect
            glow_alpha = bar["alpha"] // 4
            glow_color = (r, g, b, glow_alpha)
            glow_width = bar["width"] + 6
            draw.rectangle((bar["x"] - 3, bar_top - 3, bar["x"] + glow_width - 3, bar_bottom + 3), fill=glow_color)

            # Add top highlight
            highlight_alpha = min(255, bar["alpha"] + 50)
            highlight_color = (min(255, r + 50), min(255, g + 50), min(255, b + 50), highlight_alpha)
            highlight_height = min(5, bar["current_height"] // 4)
            if highlight_height > 0:
                draw.rectangle((bar["x"], bar_top, bar["x"] + bar["width"], bar_top + highlight_height), fill=highlight_color)

    # Remove dead bars
    bars = [bar for bar in bars if bar["life"] > 0 and bar["alpha"] > 0]

    # Convert RGBA to RGB
    rgb_image = Image.new("RGB", (width, height), "black")
    rgb_image.paste(image, (0, 0), image)

    image_np = np.array(rgb_image).astype(np.float32) / 255.0
    return image_np
