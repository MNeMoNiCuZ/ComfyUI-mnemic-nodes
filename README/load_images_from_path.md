# 🖼️ Load Images From Path

A lightweight image loader that supports single image loading and directory iteration. Perfect for workflows that need to process individual images or cycle through image collections.

<img width="1645" height="525" alt="Load Images From Path Node" src="https://github.com/user-attachments/assets/example-screenshot2.png" />

## ✨ Features

- **Flexible Path Support**: Load single images or iterate through directories
- **Automatic Format Detection**: Supports PNG, JPG, JPEG, WEBP, BMP, GIF
- **Alpha Channel Handling**: Automatically extracts alpha channels as masks
- **Sequential Iteration**: Use seed to cycle through images in a directory
- **Relative Path Support**: Works with ComfyUI's input directory

## ⚙️ Inputs

### Core Parameters
- **`seed`**: The index of the image to load. Set 'Control After Generate' to 'Increment' in workflow options to cycle through images sequentially.

- **`input_path`**: Path to a folder containing images or a single image file.
  - **Single File**: `path/to/image.png`
  - **Directory**: `path/to/image_folder/` (will iterate through all supported images)
  - **Relative Path**: Works from ComfyUI's input directory
  - **Empty Path**: Uses ComfyUI's input directory as fallback

## 📤 Outputs

- **`image`**: The loaded image tensor (RGB format)
- **`mask`**: Alpha channel as mask tensor (solid black if no alpha channel)
- **`image_path`**: Full absolute path to the loaded image file
- **`current_index`**: Zero-based index of current image in the collection
- **`total_count`**: Total number of images found in the directory

## 🎯 How It Works

### Single Image Loading
```
input_path: my_images/photo.png
seed: 0 (ignored for single images)
```
Loads the specific image file.

### Directory Iteration
```
input_path: my_images/
seed: 0 → loads first image
seed: 1 → loads second image
seed: 2 → loads third image
etc.
```

### Automatic Wrapping
```
total_count: 5 images
seed: 5 → wraps to image 0 (5 % 5 = 0)
seed: 6 → wraps to image 1 (6 % 5 = 1)
```

## 📝 Usage Examples

### Basic Single Image
```
input_path: portrait.png
```
Loads a single image from ComfyUI's input directory.

### Directory Cycling
```
input_path: training_set/
seed: increment (workflow setting)
```
Cycles through all images in `training_set` folder sequentially.

### Batch Processing
```
input_path: batch_01/
```
Combined with seed increment for processing entire directories.

### Mask Extraction
```
input_path: transparent_image.png
```
Automatically extracts alpha channel as separate mask output.

## 🔧 Advanced Features

### Supported Formats
- PNG (with transparency support)
- JPG/JPEG
- WEBP
- BMP
- GIF

### Alpha Channel Processing
- **With Alpha**: Extracts alpha as separate mask tensor
- **Without Alpha**: Generates solid black mask
- **RGBA Images**: RGB channels become image, A channel becomes mask

### Path Resolution
1. Checks if path is absolute
2. If relative, prepends ComfyUI's input directory
3. Validates file/directory exists
4. Filters for supported image formats

### Error Handling
- Invalid paths: Returns empty tensors with count=0
- Unsupported formats: Skipped during directory scanning
- Corrupt images: Returns empty tensors for that index

## 🚀 Workflow Integration

### Sequential Processing
Perfect for batch workflows:
1. Set `input_path` to image directory
2. Set workflow to increment seed
3. Each run processes next image in sequence

### Training Data Loading
Use for loading training/validation images:
1. Directory contains dataset images
2. Sequential loading ensures consistent ordering
3. Mask output for transparency handling

### Animation Frames
Load animation frames or time-lapse sequences:
1. Numbered images in directory (frame001.png, frame002.png, etc.)
2. Sequential loading maintains frame order
3. Use with video generation nodes

## 🐛 Troubleshooting

### No Images Found
- Check path exists and is accessible
- Verify images have supported extensions
- Check file permissions

### Wrong Image Loading
- Verify seed values are sequential for directory iteration
- Check total_count output to confirm images found
- Ensure directory contains only image files

### Mask Issues
- Check if source image has alpha channel
- PNG format best for transparency
- JPG format has no alpha channel

## 📊 Performance Notes

- **Single Image**: Fast loading (~0.1-0.5 seconds)
- **Directory Scan**: Minimal overhead for small directories
- **Memory Usage**: Standard image tensor size
- **CPU Usage**: PIL image processing (lightweight)

## 🔗 Related Nodes

- **Load Image Advanced**: More metadata extraction features
- **Load Text-Image Pairs**: For paired text/image datasets
- **Metadata Extractor**: For batch metadata processing