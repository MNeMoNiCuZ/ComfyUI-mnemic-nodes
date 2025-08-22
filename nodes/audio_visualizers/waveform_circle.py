import numpy as np
from PIL import Image, ImageDraw
import math
import colorsys
import random

waveform_rings = []

# Default multiplier for scale - can be adjusted to tweak visualizer sensitivity
DEFAULT_MULTIPLIER = 2.5

def visualize(audio_data, frame, framerate, width, height, scale=1.0):
    global waveform_rings
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

    # Ensure center is always calculated correctly
    center_x = int(width / 2)
    center_y = int(height / 2)

    # Dynamic radius based on audio intensity
    if len(chunk) > 0:
        avg_amplitude = np.mean(np.abs(chunk)) * scale * DEFAULT_MULTIPLIER
        base_radius = int(min(center_x, center_y) * (0.15 + avg_amplitude * 0.75))  # 15% to 90%
        base_radius = min(base_radius, int(min(center_x, center_y) * 0.9)) # Clamp base_radius
    else:
        base_radius = int(min(center_x, center_y) * 0.3)

    if len(chunk) > 1:
        # Calculate overall statistics
        avg_amplitude = np.mean(np.abs(chunk)) * scale * DEFAULT_MULTIPLIER

        # Calculate frequency-based pulsation
        if len(chunk) > 10:
            fft_data = np.fft.fft(chunk)
            freq_magnitude = np.abs(fft_data[:len(fft_data)//2])
            low_freq = np.mean(freq_magnitude[:len(freq_magnitude)//4])
            mid_freq = np.mean(freq_magnitude[len(freq_magnitude)//4:len(freq_magnitude)//2])
            high_freq = np.mean(freq_magnitude[len(freq_magnitude)//2:])

            freq_sum = low_freq + mid_freq + high_freq
            if freq_sum > 0:
                low_freq /= freq_sum
                mid_freq /= freq_sum
                high_freq /= freq_sum
        else:
            low_freq = mid_freq = high_freq = 1/3

        # Pulsation based on frequency intensity (smoothed)
        pulsation_factor = 1 + (low_freq * 0.5 + mid_freq * 0.3 + high_freq * 0.7) * avg_amplitude * 2

        # Create new waveform ring based on current audio
        if avg_amplitude > 0.01:
            points = []
            samples_per_segment = max(1, len(chunk) // 120)

            for i in range(0, len(chunk), samples_per_segment):
                angle = (i / len(chunk)) * 2 * math.pi
                sample = chunk[i] if i < len(chunk) else 0

                # Direct audio response with frequency-based pulsation
                radius_variation = int(sample * 80 * pulsation_factor)
                current_radius = base_radius + radius_variation

                # Ensure it stays within bounds - use center_x, center_y consistently
                max_allowed_radius = int(min(center_x, center_y) * 0.95)
                current_radius = min(current_radius, max_allowed_radius)

                # Calculate position using the same center values
                x = int(center_x + current_radius * math.cos(angle))
                y = int(center_y + current_radius * math.sin(angle))

                # Ensure coordinates are within bounds
                x = max(0, min(width - 1, x))
                y = max(0, min(height - 1, y))

                points.append((x, y))

            # Add this ring to the global list
            waveform_rings.append({
                "points": points,
                "life": 60,  # Back to longer persistence
                "alpha": 255,
                "color_hue": (frame % 100) / 100.0,
                "pulsation": pulsation_factor,
                "center_x": center_x,  # Store center for consistent drawing
                "center_y": center_y
            })

    # Update and draw all rings
    for ring in waveform_rings:
        ring["life"] -= 1
        ring["alpha"] = max(0, int(255 * (ring["life"] / 60)))

        if ring["alpha"] > 0 and len(ring["points"]) > 2:
            # Color based on audio and pulsation
            intensity = ring["pulsation"] * 0.3 + 0.5
            rgb_color = colorsys.hsv_to_rgb(ring["color_hue"], 0.7 + intensity * 0.3, 0.6 + intensity * 0.4)
            color = tuple(int(c * 255) for c in rgb_color) + (ring["alpha"],)

            # Draw the ring with connecting lines
            for i in range(len(ring["points"])):
                p1 = ring["points"][i]
                p2 = ring["points"][(i + 1) % len(ring["points"])]

                draw.line([p1, p2], fill=color, width=3)

            # Add glow
            if ring["alpha"] > 100:
                glow_color = tuple(int(c * 0.4) for c in color[:3]) + (ring["alpha"] // 6,)
                for point in ring["points"][::3]:
                    draw.ellipse((point[0] - 2, point[1] - 2, point[0] + 2, point[1] + 2), fill=glow_color)

    # Remove dead rings
    waveform_rings = [ring for ring in waveform_rings if ring["life"] > 0 and ring["alpha"] > 0]

    # Add center glow that reacts to current audio
    if len(chunk) > 0:
        avg_amplitude = np.mean(np.abs(chunk)) * scale * DEFAULT_MULTIPLIER
        glow_radius = int(10 + avg_amplitude * 40)
        glow_radius = min(glow_radius, int(min(center_x, center_y) * 0.5)) # Clamp glow_radius
        glow_color = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.5, 0.5, 0.8)) + (150,)
        draw.ellipse((center_x - glow_radius, center_y - glow_radius,
                     center_x + glow_radius, center_y + glow_radius), fill=glow_color)

    # Convert RGBA to RGB
    rgb_image = Image.new("RGB", (width, height), "black")
    rgb_image.paste(image, (0, 0), image)

    image_np = np.array(rgb_image).astype(np.float32) / 255.0
    return image_np
