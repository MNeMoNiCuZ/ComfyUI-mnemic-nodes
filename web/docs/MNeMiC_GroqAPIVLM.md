# ✨📷 Groq VLM API

Sends an image plus a prompt to a vision model on Groq's API and returns the
reply — captioning, describing or answering questions about an image.

## Setup

Same as ✨💬 Groq LLM API: put `GROQ_API_KEY=your_key_here` in the pack's
`.env` file and restart ComfyUI.

## Inputs

- **model** — Which vision model to call.
- **preset** — A saved system prompt, or the default entry to use the
  `system_message` field instead.
- **system_message** — Instructions setting the model's role.
- **user_input** — What you want to know about the image.
- **image** — The image to send. Required; without it the node returns a
  `400 Bad Request` instead of calling the API.
- **temperature** — Randomness of the reply.

Advanced:

- **max_tokens**, **top_p**, **seed**, **max_retries**, **stop**, **json_mode**
  — as in the LLM node.

## Outputs

- **api_response** — The model's description or answer.
- **success** — False on any error.
- **status_code** — HTTP status, e.g. `200 OK`.

## How it works

The image is JPEG-encoded, base64'd and sent inline in a single message
alongside the combined system and user text. Large images therefore mean large
requests; downscale first if you hit size limits.

## Presets

From `nodes/groq/DefaultPrompts_VLM.json` and
`nodes/groq/UserPrompts_VLM.json`. Restart ComfyUI after editing.
