# 💾 Save Video (MNeMiC)

Saves a video like ComfyUI's Save Video, with date codes in the file name and the final prompt text stored in the file.

## Inputs
- `video`: The video to save.
- `filename_prefix`: Supports `strftime`, `%date:yyyy-MM-dd%` and `%Node.widget%`. Default `%Y-%m-%d/%Y-%m-%d - %H.%M.%S`, changeable in Settings for new nodes.
- `format`: Same containers and codecs as the native Save Video.
- `positive_prompt`, `negative_prompt` (optional): Final prompt text, for example from a wildcard processor or LLM node.

## Metadata
- `prompt` and `workflow` tags as JSON, same as the native Save Video.
- `final_prompt` tag as JSON: `{"positive": "...", "negative": "..."}`, with only the connected inputs.
