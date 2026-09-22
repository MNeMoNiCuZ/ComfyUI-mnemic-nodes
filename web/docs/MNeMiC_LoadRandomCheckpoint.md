# 🎲 Load Random Checkpoint

Loads a checkpoint from a list you define, cycling or shuffling through it as
the seed changes. Built for batch runs that should sweep several models.

## Inputs

- **checkpoints** — One entry per line. Each can be:
  - a name, fuzzy-matched against your checkpoint files (`realvis`)
  - a path relative to the checkpoints folder (`SDXL/Realistic/`)
  - an absolute path (`C:/models/foo.safetensors`)
  - a folder, which adds every `.ckpt` / `.safetensors` inside it

  Blank lines are ignored.
- **seed** — Drives the selection. Set its control to **increment** to walk the
  list.
- **repeat_count** — How many consecutive seeds share one checkpoint. With `3`,
  seeds 0-2 use model A and seeds 3-5 use model B.
- **shuffle** — Off: the pool is walked so nothing repeats until every entry
  has been used. On: each pick is independent, so the same model can come up
  twice in a row.

## Outputs

- **model** / **clip** / **vae** — From the selected checkpoint.
- **path** — Full path of the file that was loaded.

## How it works

The pool is built once per unique input list and cached, then ordered using the
seed. Within one `repeat_count` window the same file is reused rather than
reloaded. Name matching prefers substring hits and falls back to fuzzy
similarity; ties keep every equally-good match in the pool.

Turn on **Settings → ⚡MNeMiC Nodes → Load Random Checkpoint → Console
Logging** to see the pool, the index and the match scores.
