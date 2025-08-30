# 🖼️ Load Image Advanced

This node is an enhanced version of the standard image loader. It loads an image, extracts its positive prompt from metadata, provides the alpha channel as a mask, and outputs the image's dimensions.

---

### Node Reference

![Image of Load Image Advanced node](https://via.placeholder.com/800x400.png?text=Load+Image+Advanced+Node)

---

### Outputs

-   `image`: The loaded image tensor.
-   `mask`: The alpha channel of the image as a mask.
-   `image_path`: The full file path of the loaded image.
-   `positive_prompt`: The positive prompt extracted from the image's metadata.
-   `width`: The width of the image in pixels.
-   `height`: The height of the image in pixels.

This node is perfect for quickly reloading a generated image and its prompt to continue working on it or to analyze its properties, and for using its dimensions to drive other parts of your workflow.