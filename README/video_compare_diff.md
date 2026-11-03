# 🎞️ Video Compare Diff

Plays two videos or images side by side with their difference:
**A | B | Diff**. Use it to compare two renders, settings, seeds or models frame
by frame. Connect them, or drop files on the node.

## Inputs

- **A** — First video, as an image batch or a VIDEO. A single image works as a
  one-frame video. A VIDEO's sound can be played in the viewer. Used instead of
  **file_a** when connected.
- **B** — Second video, as an image batch or a VIDEO. If its size differs from
  A, it is stretched to A's size for the diff. Used instead of **file_b** when
  connected.
- **file_a** / **file_b** — Video or image files in ComfyUI's temp folder, used
  when A or B is not connected.
- **export_on_run** — Save the diff and/or mask every time the workflow runs,
  as set in the player's export controls. Off by default.
- **filename_prefix** — Where exports go, relative to the output folder, as in
  Save Image. Default `video_compare_diff/compare`.

## How it works

### Dropping files on the node

Drop a video or image file on the **A** or **B** panel, or click an empty panel
to choose one. Drop two files anywhere on the node to fill A and B at once. A
single file dropped on the Diff panel or elsewhere on the node goes to A, or to
B when A already has a file. Then run the workflow.

A still image is a one-frame clip, so two images give a plain image diff. An
animated GIF or WebP plays all its frames at its own frame rate. A and B can mix
kinds: an image against a video is compared with every frame of the video.

Like 🖼️ Load Image Temporarily, the files are uploaded to ComfyUI's temp folder
and selected in **file_a** / **file_b**. The temp folder is cleared when ComfyUI
restarts, so a saved workflow forgets them; drop the files again.

### Comparing

Running the workflow writes both videos' frames to ComfyUI's temp folder as
lossless PNGs, so the diff is exact. The player computes the diff in the
browser, so changing the mode or gain takes effect immediately without running
the workflow again. Each run replaces that node's previous frames; the temp
folder is cleared when ComfyUI restarts.

If one video is shorter, it holds its last frame until the longer one ends.

### Diff modes

| Mode | Shows |
| --- | --- |
| Difference | `\|A − B\|` per channel, times the gain |
| Grayscale | Brightness of `\|A − B\|`, times the gain |
| Heatmap | Largest channel difference as a heatmap: blue is equal, red is very different |
| Signed (B − A) | Grey where equal, brighter where B is brighter, darker where B is darker |
| Threshold over A | Red where any channel differs by more than the threshold (0-255 levels), over a dimmed A |
| Blend 50% | A and B mixed half and half, like onion skinning |

**Swap** (or **S**) puts B on the left and A in the middle, and the diff
treats B as the first video: *Signed* becomes A − B and *Threshold* is drawn
over B. The mode names change to match. A swapped A is stretched to B's size
when their sizes differ.

**Gain** multiplies the difference so small changes become visible. It starts
at 1×, the true difference, and each step doubles it: 1×, 2×, 4× … 64×. At 1× a
difference of 10 levels shows as 10 of 255, which is nearly black; at 16× it
shows as 160. **Threshold** (0-255 levels) marks differences larger than it:
red in *Threshold over A*, and white in the threshold mask. A difference equal
to the threshold is not marked.

### Playback

- The blue **Play** button, a click on a panel, or **Space** plays and pauses.
- The four buttons left of Play jump to the section's first frame, step one
  frame back, step one frame forward, and jump to the section's last frame. The
  arrow keys step too (hold **Shift** for 10), and **Home** / **End** jump.
- Drag the scrub bar right of Play to seek.
- **Loop** repeats playback. Without it, playback stops at the end.
- **[ In** and **Out ]** (or **I** / **O**) set a loop section from the current
  frame. **Shift+drag** on the scrub bar draws a new section, and dragging its
  blue edges moves them. **Clear** goes back to the whole video.
- **Speed** plays slower or faster: 0.1× to 4×. Double-click it for 1×.
- **FPS** is how many frames make one second of the video. Use the slider or
  type a value. **Auto** uses the video's own frame rate, or 24 for image
  batches.

### Sound

A VIDEO input's sound plays along with the frames. It starts **muted**; click
the speaker button or press **M** to unmute, and use the volume slider. When A
and B both have sound, the note button left of the speaker (**A** / **B**) picks
which one plays. Mute and volume can be set before anything with sound is loaded.

### Export

There are two ways to export, with the same result:

- **Export** in the player saves right away, from the frames of the last run,
  without running the workflow again.
- **export_on_run** saves every time the workflow runs, like Save Image.

Both use the player's current settings: diff mode, gain, threshold, Swap and
FPS. When a loop section is set, only the section is exported; otherwise every
frame. Files go to the output folder at **filename_prefix**, numbered like
Save Image, with `_diff` or `_mask` added: `compare_00001_diff.mp4`. A message
shows where they were saved.

The export controls are at the end of the player's control row:

- **Diff / Mask / Diff + mask** — what to save.
  - **Diff** is what the Diff panel shows.
  - **Mask** is a black-and-white mask, whatever the diff mode, of the type
    picked next to it:
    - **Threshold mask** — white where any channel differs by more than the
      threshold, black elsewhere. The red area of *Threshold over A*.
    - **Soft mask** — grayscale: the largest channel difference times the gain.
- **MP4 / PNG** — **MP4** saves one video, with the sound that is playing (A or
  B) when there is one. **PNG** saves lossless frames in a folder, or a single
  PNG when there is only one frame. Use PNG when exact pixel values matter: MP4
  compression changes them slightly.

The player hands its settings to the workflow through a hidden
`player_settings` input. It is only filled in while **export_on_run** is on, so
changing the player never makes the next run redo the node when you are not
exporting.

As in the player, the second video is stretched to the first one's size, and a
shorter video holds its last frame.

Keyboard shortcuts work after clicking the player. All player settings are
saved with the workflow.

## Notes

- Long, large videos take a while to write and load. The thin bar under the
  scrub bar shows loading progress; playback waits for frames that are not
  loaded yet.
- The Diff panel needs WebGL. Without it, A and B still play.
