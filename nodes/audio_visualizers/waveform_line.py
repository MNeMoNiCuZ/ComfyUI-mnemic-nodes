import numpy as np
from PIL import Image, ImageDraw
import colorsys
import math

waves = []
last_wave_spawn_time = 0

# Default multiplier for scale - can be adjusted to tweak visualizer sensitivity
DEFAULT_MULTIPLIER = 5

def visualize(audio_data, frame, framerate, width, height, scale=1.0):
    global waves, last_wave_spawn_time
    audio_data = audio_data.squeeze().numpy()
    num_samples = audio_data.shape[0]

    start_sample = int((frame / framerate) * 44100)
    end_sample = int(((frame + 1) / framerate) * 44100)

    if start_sample >= num_samples:
        start_sample = num_samples - 1
    if end_sample > num_samples:
        end_sample = num_samples

    chunk = audio_data[start_sample:end_sample] if start_sample < end_sample else audio_data[max(0, num_samples-100):num_samples]

    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)

    center_y = height // 2
    max_amplitude = height * 0.4

    current_time = frame / framerate
    spawn_interval = 1 / (3.0 * scale * DEFAULT_MULTIPLIER) # Higher scale = more frequent waves
    if current_time - last_wave_spawn_time > spawn_interval:
        if len(chunk) > 0:
            avg_amplitude = np.mean(np.abs(chunk))
            if avg_amplitude > 0.005:
                last_wave_spawn_time = current_time
                
                points = []
                num_points = 100
                for i in range(num_points + 1):
                    x = width * (i / num_points)
                    
                    chunk_index = int(len(chunk) * (i / num_points))
                    sample = chunk[chunk_index] if chunk_index < len(chunk) else 0
                    
                    y = center_y + sample * max_amplitude
                    y = max(0, min(height - 1, y)) # Clamp y to canvas boundaries
                    points.append((x, y))

                hue = (current_time * 0.1) % 1.0
                color = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
                color = tuple(int(c * 255) for c in color)

                waves.append({
                    "points": points,
                    "life": framerate * 2, # 2 seconds life
                    "max_life": framerate * 2,
                    "color": color,
                })

    # Update and draw waves
    for wave in waves:
        wave["life"] -= 1
        life_ratio = wave["life"] / wave["max_life"]
        
        if life_ratio > 0:
            alpha = int(180 * life_ratio)
            current_color = wave["color"] + (alpha,)
            
            # Animate wave - e.g., expand vertically
            animated_points = []
            for x, y in wave["points"]:
                new_y = center_y + (y - center_y) * (1 + (1 - life_ratio) * 0.5)
                animated_points.append((x, new_y))

            draw.line(animated_points, fill=current_color, width=8)

    waves = [w for w in waves if w["life"] > 0]

    rgb_image = Image.new("RGB", (width, height), "black")
    rgb_image.paste(image, (0, 0), image)

    image_np = np.array(rgb_image).astype(np.float32) / 255.0
    return image_np
