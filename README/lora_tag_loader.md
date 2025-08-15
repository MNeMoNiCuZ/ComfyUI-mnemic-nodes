## 🏷️ LoRA Loader Prompt Tags

Loads LoRA models using tags in the prompt.

### Syntax and Weights

The basic syntax is `<lora:loraName:strength>`.

-   The default strength is `1.0` if not specified (e.g., `<lora:myLora>`).
-   A strength of `0` is treated as `1.0`.
-   If an invalid strength is provided (e.g., non-numeric text), it will also be treated as `1.0`.

#### CLIP Weight
You can provide a separate weight for the CLIP model.

-   **Syntax**: `<lora:loraName:model_weight:clip_weight>`
-   If the CLIP weight is omitted, it defaults to the model's weight.

### LoRA Matching and Prioritization

When you use a tag like `<lora:myLora>`, the node searches for the best matching LoRA file. If the name is not exact, it uses a scoring system to find the most likely candidate. Here is the order of priority:

1.  **Exact Match:** An exact filename match (e.g., `myLora.safetensors`) is always preferred.
2.  **Numbered Versions:** It intelligently handles numbered versions (e.g., `myLora-1`, `myLora-2`). If you ask for `myLora-2`, it will prioritize that file. If it can't find it, it will look for other numbered versions or the base `myLora` file.
3.  **Prefix Match:** It will look for files that start with your requested name (e.g., `myLoraAndMore.safetensors`).
4.  **Contains Match:** It will look for files that contain your requested name anywhere in the filename.
5.  **Path Priority:** Files located closer to the root of your LoRA folders are given a slight priority boost over files in deep subdirectories.


![image](https://github.com/user-attachments/assets/595fdb36-1442-4c0a-abf4-b1779674c515)

Route the model and clip through the node.

Use the output [STRING] to have the prompt without the `<lora::>`-tags.
