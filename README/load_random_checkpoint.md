# 🎲 Load Random Checkpoint

A sophisticated checkpoint loader with fuzzy name matching, repeat control, and batch processing capabilities. Perfect for workflows requiring consistent model selection across multiple generations.

<img width="1649" height="438" alt="Load Random Checkpoint Node" src="https://github.com/user-attachments/assets/example-screenshot.png" />

## ✨ Features

- **Intelligent Name Matching**: Fuzzy matching against checkpoint filenames with smart scoring
- **Flexible Input Types**: Supports checkpoint names, file paths, directories, and absolute paths
- **Repeat Control**: Groups consecutive seeds to use the same checkpoint
- **Caching System**: Efficient caching prevents redundant checkpoint loading
- **Batch Processing Ready**: Designed for workflows requiring consistent model selection

## ⚙️ Inputs

### Core Selection
- **`checkpoints`**: Enter checkpoint names, file paths, or directory paths - one per line.
  - **Names** (e.g., 'model_one'): Fuzzy-matched against checkpoint files
  - **Relative paths** (e.g., '../loras/character'): Work from checkpoints folder
  - **Absolute paths** (e.g., 'C:/path/to/model.ckpt'): Used directly
  - **Directory paths**: Add all .ckpt/.safetensors files within them
  - Empty lines are ignored

- **`seed`**: Controls checkpoint selection. Works with repeat_count:
  - `repeat_count=1`: Each seed gives different checkpoint
  - `repeat_count=3`: Seeds 0,1,2 → same checkpoint, seeds 3,4,5 → same different checkpoint
  - Set 'Control After Generate' to 'Increment' for sequential testing

- **`repeat_count`**: How many consecutive seeds use the same checkpoint
  - `1` = Each seed picks a different checkpoint
  - `3` = Seeds 0,1,2 all use checkpoint A, seeds 3,4,5 all use checkpoint B
  - Higher values = more repeats before changing

- **`shuffle`**: Selection mode
  - `False` (Sequential): Predictable iteration through shuffled pool
  - `True` (Shuffle): Truly random selection from pool (less predictable)

## 📤 Outputs

- **`model`**: The loaded checkpoint model, ready for inference
- **`clip`**: CLIP model for text encoding (if available in checkpoint)
- **`vae`**: VAE model for image decoding (if available in checkpoint)
- **`ckpt_path`**: Full path to the selected checkpoint file

## 🎯 How It Works

### Fuzzy Name Matching
When you enter a name like "perfection amateur", the node:
1. Searches all checkpoint files in your checkpoints folder
2. Scores each file based on similarity to your input
3. Returns the best matches (multiple if they have equal scores)

### Repeat Functionality
The `repeat_count` feature groups consecutive seeds:
```
Seeds 0,1,2 (repeat_count=3) → Checkpoint A
Seeds 3,4,5 (repeat_count=3) → Checkpoint B
Seeds 6,7,8 (repeat_count=3) → Checkpoint C
```

### Caching System
- First run on a checkpoint list: Loads and caches the model
- Subsequent runs with same inputs: Uses cached model instantly
- Input changes: Rebuilds pool and updates cache

## 📝 Usage Examples

### Basic Fuzzy Matching
```
checkpoints: perfection amateur
```
Matches: `Perfection_ILXL_Amateur_1.0.safetensors`, `Perfection_ILXL_Amateur_2.0.safetensors`, etc.

### Multiple Checkpoints
```
checkpoints: realism
           sdxl_base
           ../custom_models/my_model.ckpt
```
Randomly selects from the three options.

### Directory Loading
```
checkpoints: ../my_models/
```
Loads all checkpoints from the `my_models` directory.

### Repeat Control
```
repeat_count: 5
seed: increment (in workflow settings)
```
Each group of 5 consecutive seeds uses the same checkpoint.

## 🔧 Advanced Features

### Multiple Input Types
Mix different input types in one list:
```
checkpoints: sdxl_base
           ../fine_tuned/my_model.ckpt
           C:/models/special_checkpoint.safetensors
```

### Smart Scoring
The fuzzy matching uses multiple factors:
- Exact name matches get highest priority
- Partial matches are scored by similarity
- Directory depth affects priority (shallower paths preferred)

### Performance Optimization
- Caching prevents redundant model loads
- Pool is shuffled once per input change
- Efficient fuzzy matching algorithm

## 🚀 Workflow Integration

### Batch Processing
Use with repeat_count > 1 for consistent results across a batch:
1. Set `repeat_count` to desired batch size
2. Use incrementing seeds
3. Each batch gets the same checkpoint

### Model Testing
Quickly test different checkpoints:
1. List multiple checkpoint names
2. Set `shuffle=true`
3. Increment seed to try different combinations

### Consistent Generation
For reproducible results:
1. Set specific seed
2. Set `repeat_count` to number of images needed
3. All images use the same checkpoint

## 🐛 Troubleshooting

### No Checkpoints Found
- Check file paths are correct
- Ensure files have .ckpt or .safetensors extensions
- Verify directory permissions

### Unexpected Matches
- Fuzzy matching prioritizes exact matches
- Check for typos in checkpoint names
- Use absolute paths for precise control

### Repeat Not Working
- Ensure `repeat_count` > 1
- Check that consecutive seeds are actually consecutive
- Verify `shuffle=false` for predictable results

## 📊 Performance Notes

- First load: ~2-8 seconds (depends on model size)
- Cached loads: < 0.1 seconds
- Memory usage: Standard for loaded model + small pool cache
- CPU usage: Minimal (fuzzy matching is fast)