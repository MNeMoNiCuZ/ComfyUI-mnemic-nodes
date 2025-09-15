# 🎲 Load Random Checkpoint

A checkpoint loader that allows for random or sequential selection from a list of models, with fuzzy name matching and repeat control.

<img width="1649" height="438" alt="Load Random Checkpoint Node" src="https://github.com/user-attachments/assets/example-screenshot.png" />

Note: Make sure to set the `control after generate` to `increment` 

## Inputs

-   `checkpoints`: A list of checkpoint identifiers, one per line. The node will create a pool of models based on these identifiers. Supported formats include:
    -   **Names**: Fuzzy-matched against checkpoint files in your ComfyUI checkpoints folder. Example: (`dreamshaper`).
    -   **Relative Paths**: Resolved from the ComfyUI checkpoints folder. Example: (`sdxl/general/dreamshaper`).
    -   **Absolute Paths**: A direct path to a model file (`C:/ComfyUI/models/checkpoints/model.safetensors`).
    -   **Directory Paths**: Adds all `.ckpt` and `.safetensors` files found within the specified directory. Both relative and absolute paths work. Relative paths start from the `ComfyUI/models/checkpoints/` folder.
-   `seed`: Controls which checkpoint is selected from the pool. Its behavior is modified by `repeat_count`.
-   `control after generate`: This *_MUST_* be set to `increment` for the `repeat_count` to work.
-   `repeat_count`: The number of consecutive seeds that will use the same checkpoint. For example, if set to `3`, seeds `0`, `1`, and `2` will all load the same checkpoint before a new one is selected for seed `3`.
-   `shuffle`: Determines the selection mode.
    -   `False` (Sequential): Iterates through the checkpoint pool in a predictable, shuffled order. Each avaialble checkpoint must be used before the pool resets.
    -   `True` (Shuffle): Selects a checkpoint from the pool at random for each new index. The same checkpoint could be used several times in a row, regardless of how many times it has been randomly selected before.

## Outputs

-   `model`: The loaded checkpoint model (MODEL).
-   `clip`: The CLIP model from the checkpoint (CLIP).
-   `vae`: The VAE model from the checkpoint (VAE).
-   `path`: The full file path of the selected checkpoint file (STRING).
