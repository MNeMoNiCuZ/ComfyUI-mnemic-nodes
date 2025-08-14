## 🖼️ Download Image from URL

This node downloads an image from an URL and lets you use it.

It also outputs the Width/Height of the image.

* By default, it will save the image to the /input directory.
  * Clear the `save_path` line to prevent saving the image (it will still be saved in the TEMP-folder).
* If you enter a name in the `save_file_name_override` section, the file will be saved with this name.
  * You can enter or ignore the file extension.
  * If you enter one, it will rename the file to the chosen extension without converting the image.
* Supported image formats: JPG, JPEG, PNG, WEBP.
* Does not support saving with transparency.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/16401f43-5f7b-4590-908f-a71bbefc467b)

> [!IMPORTANT]
> #### 2024-09-14 - Version 1.2.0
> This node was renamed in the code to match the functionality. This may break existing nodes.
