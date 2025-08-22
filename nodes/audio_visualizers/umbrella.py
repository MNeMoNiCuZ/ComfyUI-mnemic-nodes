import numpy as np
from PIL import Image, ImageDraw
import math
import colorsys

spike_waves = []
rotation_angle = 0

def visualize(audio_data, frame, framerate, width, height, scale=1.0):
    global spike_waves, rotation_angle
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

    center_x, center_y = width // 2, height // 2

    # Smooth rotation
    rotation_angle += 0.02
    if rotation_angle > 2 * math.pi:
        rotation_angle -= 2 * math.pi

    if len(chunk) > 1:
        # Calculate audio metrics
        avg_amplitude = np.mean(np.abs(chunk)) * scale

        # Analyze frequency content - simplified for performance
        if len(chunk) > 10:
            fft_data = np.fft.fft(chunk)
            freq_magnitude = np.abs(fft_data[:len(fft_data)//2])
            band_size = len(freq_magnitude) // 4
            bass = np.mean(freq_magnitude[:band_size])
            low_mid = np.mean(freq_magnitude[band_size:2*band_size])
            high_mid = np.mean(freq_magnitude[2*band_size:3*band_size])
            treble = np.mean(freq_magnitude[3*band_size:])

            freq_sum = bass + low_mid + high_mid + treble
            if freq_sum > 0:
                bass /= freq_sum
                low_mid /= freq_sum
                high_mid /= freq_sum
                treble /= freq_sum
        else:
            bass = low_mid = high_mid = treble = 0.25

        # Create spikes with optimized performance
        if avg_amplitude > 0.01:
            num_spikes = max(8, int(avg_amplitude * 15) + 6)  # Back to reasonable number

            for i in range(num_spikes):
                angle = (i / num_spikes) * 2 * math.pi + rotation_angle

                # Each spike gets influenced by different frequency bands
                freq_influence = [bass, low_mid, high_mid, treble][i % 4]

                # Spike length based on amplitude and frequency - larger spikes
                base_length = 60 + avg_amplitude * 200  # Increased for larger spikes
                spike_length = int(base_length * (1 + freq_influence * 2.5))

                # Calculate spike points - larger and stationary
                inner_radius = 15 + avg_amplitude * 70  # Larger minimum
                outer_radius = inner_radius + spike_length * 1.3  # Longer spikes

                inner_x = center_x + int(inner_radius * math.cos(angle))
                inner_y = center_y + int(inner_radius * math.sin(angle))
                outer_x = center_x + int(outer_radius * math.cos(angle))
                outer_y = center_y + int(outer_radius * math.sin(angle))

                # Create spike as a triangle
                spike_width = math.pi / num_spikes * 1.5  # Wider spikes for overlap

                left_angle = angle - spike_width * 0.5
                right_angle = angle + spike_width * 0.5

                left_x = center_x + int(outer_radius * math.cos(left_angle))
                left_y = center_y + int(outer_radius * math.sin(left_angle))
                right_x = center_x + int(outer_radius * math.cos(right_angle))
                right_y = center_y + int(outer_radius * math.sin(right_angle))

                # Clamp points to canvas boundaries
                inner_x = max(0, min(width - 1, inner_x))
                inner_y = max(0, min(height - 1, inner_y))
                left_x = max(0, min(width - 1, left_x))
                left_y = max(0, min(height - 1, left_y))
                right_x = max(0, min(width - 1, right_x))
                right_y = max(0, min(height - 1, right_y))

                spike_points = [(inner_x, inner_y), (left_x, left_y), (right_x, right_y)]

                # Smoother color transitions
                base_hue = (frame * 0.01 + i * 0.1) % 1.0

                # Different frequency bands get different color ranges
                if i % 4 == 0:  # Bass - Warm colors
                    hue = (base_hue + 0.0) % 1.0
                    saturation = 0.7 + freq_influence * 0.3
                elif i % 4 == 1:  # Low mid - Cool colors
                    hue = (base_hue + 0.3) % 1.0
                    saturation = 0.6 + freq_influence * 0.4
                elif i % 4 == 2:  # High mid - Bright colors
                    hue = (base_hue + 0.5) % 1.0
                    saturation = 0.8 + freq_influence * 0.2
                else:  # Treble - Vibrant colors
                    hue = (base_hue + 0.7) % 1.0
                    saturation = 0.9 + freq_influence * 0.1

                value = 0.6 + freq_influence * 0.4 + avg_amplitude * 0.3

                rgb_color = colorsys.hsv_to_rgb(hue, saturation, value)
                color = tuple(int(c * 255) for c in rgb_color)

                # Add this spike to the waves - longer life, no bouncing
                spike_waves.append({
                    "points": spike_points,
                    "center_point": (inner_x, inner_y),
                    "color": color,
                    "life": 80,  # Longer life for fade out effect
                    "alpha": 180,  # Lower starting alpha for transparency
                    "angle": angle,
                    "frequency_influence": freq_influence,
                    "spawn_position": (inner_x, inner_y, outer_x, outer_y)  # Store spawn position
                })

    # Update and draw all spike waves - no bouncing, just fade out
    if len(spike_waves) > 60:  # Reasonable limit
        spike_waves = spike_waves[-60:]

    for spike in spike_waves:
        spike["life"] -= 1
        # Fade alpha over time - longer fade
        spike["alpha"] = max(0, int(220 * (spike["life"] / 80)))

        if spike["alpha"] > 0:
            # Draw the spike with current alpha - keep at spawn position
            current_color = spike["color"] + (spike["alpha"],)

            # Simple filled triangle
            draw.polygon(spike["points"], fill=current_color)

            # Simple outline
            outline_alpha = spike["alpha"] * 2 // 3
            outline_color = spike["color"] + (outline_alpha,)
            draw.polygon(spike["points"], outline=outline_color, width=2)

            # Glow for high intensity spikes
            if spike["frequency_influence"] > 0.4 and spike["alpha"] > 100:
                glow_color = tuple(int(c * 0.5) for c in spike["color"]) + (spike["alpha"] // 3,)
                draw.polygon(spike["points"], outline=glow_color, width=3)

    # Remove dead spikes
    spike_waves = [spike for spike in spike_waves if spike["life"] > 0 and spike["alpha"] > 0]

    # Convert RGBA to RGB
    rgb_image = Image.new("RGB", (width, height), "black")
    rgb_image.paste(image, (0, 0), image)

    image_np = np.array(rgb_image).astype(np.float32) / 255.0
    return image_np