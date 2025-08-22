import numpy as np
from PIL import Image, ImageDraw
import random
import math
import colorsys

particles = []
spawner = {"x": 0, "y": 0, "vx": 0, "vy": 0}

# Default multiplier for scale - can be adjusted to tweak visualizer sensitivity
DEFAULT_MULTIPLIER = 5

def visualize(audio_data, frame, framerate, width, height, scale=1.0):
    global particles, spawner
    audio_data = audio_data.squeeze().numpy()
    num_samples = audio_data.shape[0]

    start_sample = int((frame / framerate) * 44100)
    end_sample = int(((frame + 1) / framerate) * 44100)

    if start_sample >= num_samples:
        start_sample = num_samples - 1
    if end_sample > num_samples:
        end_sample = num_samples

    chunk = audio_data[start_sample:end_sample] if start_sample < end_sample else audio_data[max(0, num_samples-100):num_samples]

    # Initialize spawner in center if not set
    if spawner["x"] == 0 and spawner["y"] == 0:
        spawner["x"] = width // 2
        spawner["y"] = height // 2
        spawner["vx"] = random.uniform(2, 4) * random.choice([-1, 1])
        spawner["vy"] = random.uniform(2, 4) * random.choice([-1, 1])

    # Calculate audio metrics
    if len(chunk) > 0:
        avg_amplitude = np.mean(np.abs(chunk)) * scale * DEFAULT_MULTIPLIER

        # Analyze frequency content
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

        # Update spawner position with DVD-like bouncing
        spawner["x"] += spawner["vx"]
        spawner["y"] += spawner["vy"]

        # Bounce off edges like DVD screensaver
        margin = 50
        if spawner["x"] <= margin:
            spawner["x"] = margin
            spawner["vx"] = abs(spawner["vx"])
        elif spawner["x"] >= width - margin:
            spawner["x"] = width - margin
            spawner["vx"] = -abs(spawner["vx"])

        if spawner["y"] <= margin:
            spawner["y"] = margin
            spawner["vy"] = abs(spawner["vy"])
        elif spawner["y"] >= height - margin:
            spawner["y"] = height - margin
            spawner["vy"] = -abs(spawner["vy"])

        # Create particles from spawner with larger spawn area
        spawn_area = 100 + avg_amplitude * 150  # +50% pulsation based on music
        spawn_area = min(spawn_area, min(width, height) * 0.4) # Clamp spawn area

        particles_per_frame = int(avg_amplitude * 25) + 3
        for _ in range(min(particles_per_frame, 12)):
            if avg_amplitude > 0.01:
                # Spawn within the pulsating area around spawner
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, spawn_area)

                x = spawner["x"] + math.cos(angle) * distance
                y = spawner["y"] + math.sin(angle) * distance

                # Velocity based on frequency and spawner movement
                base_speed = (low_freq * 3 + mid_freq * 5 + high_freq * 7) + avg_amplitude * 5
                base_speed = min(base_speed, 20) # Clamp base speed

                # Inherit some velocity from spawner
                vx = math.cos(angle) * base_speed + spawner["vx"] * 0.3
                vy = math.sin(angle) * base_speed + spawner["vy"] * 0.3

                # Coherent color scheme - slower color change
                base_hue = (frame * 0.003 + avg_amplitude * 0.2) % 1.0
                saturation = 0.8
                value = 0.7 + avg_amplitude * 0.3

                rgb_color = colorsys.hsv_to_rgb(base_hue, saturation, value)

                # Size based on frequency content
                if low_freq > 0.5:
                    size = random.uniform(24, 50)  # Bass = largest particles
                elif high_freq > 0.5:
                    size = random.uniform(12, 30)  # Treble = medium particles
                else:
                    size = random.uniform(16, 40)  # Mid = large particles

                particles.append({
                    "x": x,
                    "y": y,
                    "vx": vx,
                    "vy": vy,
                    "base_color": [int(c * 255) for c in rgb_color],
                    "life": random.randint(120, 200),  # 4-6.6 seconds
                    "max_life": 200,
                    "size": size,
                    "color_phase": random.uniform(0, 2 * math.pi),
                    "pulsate_phase": random.uniform(0, 2 * math.pi),
                    "frequency_weights": [low_freq, mid_freq, high_freq],
                    "bounce_count": 0,
                    "max_bounces": random.randint(4, 10)
                })

    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)

    # Update and draw particles
    for p in particles:
        # Update position with audio-reactive velocity
        age_ratio = 1 - (p["life"] / p["max_life"])
        reactivity_factor = 1 - (age_ratio * 0.7)

        # Apply velocity boost based on current audio
        velocity_boost = 0.3 * (low_freq + mid_freq + high_freq) * avg_amplitude * reactivity_factor

        # Extra boost for particles that match current frequency
        frequency_match = sum(w * f for w, f in zip(p["frequency_weights"], [low_freq, mid_freq, high_freq]))
        frequency_boost = 0.2 * frequency_match * reactivity_factor

        # Apply boosts to velocity
        boost_vx = p["vx"] * (velocity_boost + frequency_boost)
        boost_vy = p["vy"] * (velocity_boost + frequency_boost)

        p["x"] += p["vx"] + boost_vx
        p["y"] += p["vy"] + boost_vy

        # Bounce off edges
        if p["x"] <= 0 or p["x"] >= width:
            p["vx"] = -p["vx"] * 0.8
            p["x"] = max(0, min(width, p["x"]))
            p["bounce_count"] += 1

        if p["y"] <= 0 or p["y"] >= height:
            p["vy"] = -p["vy"] * 0.8
            p["y"] = max(0, min(height, p["y"]))
            p["bounce_count"] += 1

        # Fade out over time
        p["life"] -= 1
        life_ratio = p["life"] / p["max_life"]

        if p["life"] > 0 and p["bounce_count"] < p["max_bounces"]:
            # Calculate current properties with subtle pulsation
            if len(chunk) > 0:
                # Dynamic reactivity based on age and current audio
                age_ratio = 1 - life_ratio  # How old the particle is (0 = new, 1 = old)

                # New particles react strongly to current audio, old particles react less
                reactivity_factor = 1 - (age_ratio * 0.7)  # New = 100% reactivity, old = 30% reactivity

                # Strong pulsation for new particles, subtle for old ones
                base_pulsation = 0.08 * math.sin(frame * 0.1 + p["pulsate_phase"])
                audio_reactivity = 0.15 * (low_freq + mid_freq + high_freq) * avg_amplitude * reactivity_factor
                frequency_boost = 0.1 * p["frequency_weights"][0] * low_freq * reactivity_factor  # Extra bass reactivity

                pulsation_factor = 1 + base_pulsation + audio_reactivity + frequency_boost
            else:
                pulsation_factor = 1

            # Color shifting over time - age-based reactivity
            age_ratio = 1 - life_ratio
            reactivity_factor = 1 - (age_ratio * 0.7)

            # New particles shift colors more dramatically based on current audio
            audio_color_shift = 0.15 * (low_freq - high_freq) * avg_amplitude * reactivity_factor
            base_color_shift = 0.05 * math.sin(frame * 0.03 + p["color_phase"]) * reactivity_factor

            current_hue = (colorsys.rgb_to_hsv(*[c/255 for c in p["base_color"]])[0] + audio_color_shift + base_color_shift) % 1.0

            current_rgb = colorsys.hsv_to_rgb(current_hue, 0.8, 0.7 + life_ratio * 0.3)
            current_color = [int(c * 255) for c in current_rgb]

            # Current size with subtle pulsation
            current_size = p["size"] * pulsation_factor * life_ratio
            current_size = min(current_size, 100) # Clamp particle size

            if current_size > 1:
                center = (int(p["x"]), int(p["y"]))

                # Draw particle as a soft, blended shape
                for radius in range(int(current_size), 0, -3):
                    alpha = int(255 * life_ratio * (radius / current_size))
                    particle_color = current_color + [alpha]
                    draw.ellipse(
                        (center[0] - radius, center[1] - radius,
                         center[0] + radius, center[1] + radius),
                        fill=tuple(particle_color)
                    )

    # Remove dead or over-bounced particles
    particles = [p for p in particles if p["life"] > 0 and p["bounce_count"] < p["max_bounces"]]

    # Convert RGBA to RGB
    rgb_image = Image.new("RGB", (width, height), "black")
    rgb_image.paste(image, (0, 0), image)

    image_np = np.array(rgb_image).astype(np.float32) / 255.0
    return image_np
