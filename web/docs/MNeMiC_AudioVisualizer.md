# 🎵📊 Audio Visualizer

Turns audio into animated frames — waveforms, particles and geometric patterns
— driven by the waveform amplitude.

## Inputs

- **output_type** — How the frames come out:
  - `image` — one frame per run. Set the seed's control to **increment** and
    use Batch Count to step through frames.
  - `image_batch` — every frame at once, as a batch. Pair with a video-combine
    node to add audio. Careful with long clips: a Preview Image node on a
    thousand frames will choke the UI.
  - `video` — an encoded video, for ComfyUI's Save Video node.
- **visualizer_script** — Which visualizer to run. Each gives a different look.
- **audio** — The audio to visualise.
- **scale** — Sensitivity to amplitude. Higher makes quiet passages move more.
- **stereo_to_mono** — `mean` averages the channels, or use just `left` /
  `right`.
- **framerate** — Frames per second for the video output.
- **width** / **height** — Frame size in pixels.
- **seed** — Starting frame for the `image` output. **Setting it to 0 resets
  the visualizer's internal state**, which is what you want at the start of an
  animation.

## Outputs

- **image** — Single frame.
- **image_batch** — All frames.
- **video** — Encoded video.

Only the output matching `output_type` is populated; the others are empty.

## Writing your own visualizer

Drop a Python file in `nodes/audio_visualizers/` and it appears in the
dropdown. Scripts are loaded fresh whenever the seed is 0, so you can edit one
and re-run without restarting ComfyUI. Any global state a script keeps between
frames is cleared at the same moment.
