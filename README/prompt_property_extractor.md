# ⚙️ Prompt Property Extractor

The **Prompt Property Extractor** node is a tool designed to parse a string (like a prompt) and extract various workflow properties such as model checkpoints, VAEs, LoRAs, sampler settings, and even generate latent tensors. It allows you to define a large part of your workflow within a single text block, making it a useful tool for randomizing more parts of your generations than just a wildcard.

<img width="1856" height="1115" alt="image" src="https://github.com/user-attachments/assets/74958287-97dd-4a07-a355-f26c6767a1cc" />


## Inputs

The node accepts a primary input string and a set of default values for all supported properties. If a property is found in the input string, it will override the default value.

-   **`input_string`**: The main text string to parse for properties.
-   **`model`, `clip`, `vae`**: Default model, CLIP, and VAE to use if not specified in the string.
-   **`cfg`, `steps`, `sampler`, etc.**: Default values for all standard sampler and image properties.

### Model Loading Priority

It is important to understand which model/CLIP/VAE is used when multiple sources are available (Input pins vs. Tags).

**Priority Order (Highest to Lowest):**

1.  **Specific Tag**: `<clip:name>` or `<vae:name>` always takes the highest priority.
2.  **Checkpoint Tag**: If a `<checkpoint:name>` tag is present:
    *   **Model**: Always loaded from the checkpoint.
    *   **CLIP**: Loaded from checkpoint **IF** `load_clip_from_checkpoint` is **True**.
    *   **VAE**: Loaded from checkpoint **IF** `load_vae_from_checkpoint` is **True**.
3.  **Input Pin**: The `model`, `clip`, and `vae` inputs are used if they are not overridden by the above.

**Examples:**
*   **`load_clip_from_checkpoint = True` + Input CLIP + `<checkpoint>` tag**: The Checkpoint's CLIP is used (Input is ignored).
*   **`load_clip_from_checkpoint = False` + Input CLIP + `<checkpoint>` tag**: The Input CLIP is used.
*   **`load_clip_from_checkpoint = True` + Input CLIP + (NO `<checkpoint>` tag)**: The Input CLIP is used (Setting is ignored).

## Outputs

The node outputs all the properties it can extract, which can be connected to other nodes in your workflow.

-   **`MODEL`, `CLIP`, `VAE`**: The final models after applying any specified checkpoints or LoRAs.
-   **`positive`, `negative` (CONDITIONING)**: The positive and negative conditioning (CLIP encoding).
-   **`latent`**: A latent tensor generated based on the resolved width and height (batch size 1).
-   **`seed`, `steps`, `cfg`, `sampler`, `denoise`**: The final values for these properties.
-   **`start_step`, `end_step`**: The final start and end steps for KSampler.
-   **`positive`, `negative` (STRING)**: The positive and negative prompt strings.
-   **`other_tags`**: A string containing any tags that were not recognized by the parser.
-   **`resolved_string`**: The input string with all wildcards resolved but **keeping all tags**.
-   **`width`, `height`**: The final image dimensions.

Note: The `<res>` or `<resolution>` tags will strictly override the `<width>` and `<height>` tags, regardless of where they appear in the input string.

## Supported Tags

The node recognizes tags in the format `<tag:value>` or `<tag:value1:value2>`. Many tags have alternatives for convenience.

| Tag Format | Alternatives | Description |
| :--- | :--- | :--- |
| `<checkpoint:name>` | `<model:name>`, `<ckpt:name>` | Loads the checkpoint that best matches `name`. |
| `<vae:name>` | | Loads the VAE that best matches `name`. |
| `<clip:name>` | | Loads the CLIP that best matches `name`. |
| `<lora:name:weight>` | `<lora:name:m_wt:c_wt>` | Finds LoRA matching `name`. Optional weights: `weight` (both), or `m_wt` (model) & `c_wt` (CLIP). Default 1.0. |
| `<cfg:value>` | | Sets the CFG scale (e.g., `<cfg:7.5>`). |
| `<steps:value>` | `<step:value>` | Sets the number of steps (e.g., `<steps:25>`). |
| `<sampler:name>` | `<sampler_name:name>` | Sets the sampler (e.g., `<sampler:euler_ancestral>`). |
| `<scheduler:name>` | | Sets the scheduler (e.g., `<scheduler:karras>`). *(Note: Currently disabled in node outputs)* |
| `<seed:value>` | | Sets the seed. |
| `<width:value>` | | Sets the image width. |
| `<height:value>` | | Sets the image height. |
| `<resolution:WxH>` | `<res:WxH>` | Sets both width and height (e.g., `<res:1024x768>` or `<res:1024:768>`). Overrides width/height tags. |
| `<denoise:value>` | | Sets the denoise value. |
| `<start_step:value>` | `<start:value>`, `<start_at_step:value>` | Sets the KSampler start step. |
| `<end_step:value>` | `<end:value>`, `<end_at_step:value>` | Sets the KSampler end step. |
| `<neg:value>` | `<negative:value>` | Sets the negative prompt content. |
| `_any other tag_` | | Any other tag is passed to `other_tags` (e.g., `<custom:value>`). |

**Escape Sequences:**
- Use `\>` to include a literal `>` character in tag values (e.g., `<neg:(cat:1.5)\>, ugly>`)
- Use `\\` to include a literal `\` character in tag values

## Example Usage

**Input String:**

```
A beautiful painting of a majestic __color__ castle
<ckpt:dreamshaper>
<lora:add_detail:0.5>
<lora:lcm:1.0:0.0>
<cfg:7>
<steps:30>
<sampler:dpmpp_2m>
<res:1024x1024>
<seed:12345>
<neg:bad quality, blurry>
```

**Order of operation:**

1.  The node reads the `input_string`.
2.  It resolves any wildcards (e.g., `__color__` -> `blue`).
3.  It finds the checkpoint name/path inconclusive, and loads the closest match `<ckpt:dreamshaper_8.safetensors>` and loads that model.
4.  If VAE / CLIP are to be loaded from the checkpoint, it will load them (See **Model Loading Priority** above).
5.  It finds `<lora:add_detail:0.5>` and applies it at 50% weight (Model & CLIP).
6.  It finds `<lora:lcm:1.0:0.0>` and applies it with 1.0 Model weight and 0.0 CLIP weight.
7.  It parses `<cfg:7>`, `<steps:30>`, `<sampler:dpmpp_2m>`, `<seed:12345>`, etc.
8.  It extracts `<neg:bad quality, blurry>` as the negative prompt.
9.  It sees `<res:1024x1024>` and sets the width/height to 1024, overriding any `<width>` or `<height>` tags.
10. It creates a 1024x1024 latent tensor.
11. It outputs the positive prompt `"A beautiful painting of a majestic blue castle"` and the negative prompt `"bad quality, blurry"`.
12. Any connected outputs will use these values instead of the default input values from this node.
