# ✨🧠 Universal LLM API

Sends a prompt, and optionally images, to any language model and returns the
reply. One node covers cloud APIs (ChatGPT, Claude, Gemini, Grok, Groq,
OpenRouter, Mistral, DeepSeek) and local servers (Ollama and LM Studio on this
PC, Ollama or any OpenAI-compatible server on your network). Presets are
shared with the Groq nodes.

## Setup

Keys and private addresses go in the `.env` file in the pack root, never in the
node. It is created from `.env.example` on first run; fill in only what you
use:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_NETWORK_URL=http://192.168.1.50:11434
```

Edits apply on the next run, no restart needed. Ollama and LM Studio on this
PC work with no setup at all.

The panel at the bottom of the node shows whether the selected endpoint is
ready: where it runs (🖥 this PC, 🏠 network, ☁ cloud), whether its key is set,
and what is missing if not.

## Inputs

- **endpoint** — Which server to call. The list comes from
  `nodes/llm/DefaultEndpoints.json` and your `nodes/llm/UserEndpoints.json`.
- **model** — Model name. Empty uses the endpoint's default (for Ollama, the
  first installed model). Click **🔍 Models** to browse and search what the
  endpoint offers; Ollama models already in memory are marked.
- **preset** — A saved system prompt, or the first entry to use
  `system_message`. Click **📜 Preset** to read the selected one.
- **system_message** — The model's instructions. Greyed out while a preset is
  active.
- **user_input** — The request.
- **images** — Optional. Every image in the batch is sent, for vision models.
- **temperature** — Randomness. Dropped automatically for models that refuse
  anything but their default.

Advanced:

- **reasoning** — Thinking effort for reasoning models: `none` turns it off
  where supported, `low`/`medium`/`high` ask for more. Sent as
  `reasoning_effort` (OpenAI-style), `think` (Ollama), or on Claude as
  adaptive thinking with that effort level (older Claude models such as Haiku
  4.5 get a 2k/8k/24k-token thinking budget instead). Where Claude can't turn
  thinking off (Opus 5.5, Fable), `none` asks for the lowest effort.
- **max_tokens** — Reply length cap. 0 leaves it to the server (Claude gets
  16000). Thinking counts against it on current Claude models.
- **top_p** — Nucleus sampling. 1.0 is off and not sent.
- **seed** — Sent for repeatable replies where supported. Fixed by default, so
  an unchanged node reuses its cached reply instead of paying for a new one.
- **stop** — Stop sequences, separated by `|`.
- **json_mode** — Ask for valid JSON; code fences are stripped from the reply.
- **unload_model_after** — Ollama: free the model's VRAM right after replying.
- **context_length** — Ollama: context window (`num_ctx`). 0 is the model's
  default.
- **free_comfy_vram** — Unload ComfyUI's own models before the call, for a
  local LLM sharing the GPU.
- **max_retries** — Extra attempts on connection errors, rate limits (429) and
  server errors (5xx), with backoff that honours `Retry-After`.
- **raise_on_error** — On: a failed call stops the workflow with a clear
  message. Off: returns an empty reply and `success = false` for branching.

## Outputs

- **response** — The reply, with any `<think>` reasoning removed.
- **thinking** — The reasoning, if the model produced any.
- **success** — False only when the call failed and `raise_on_error` is off.
- **status** — `200 OK`, plus any parameters the endpoint rejected, or the
  error message.

## How it works

**Nothing secret is saved in the workflow.** A workflow, or an image made
with it, stores only the endpoint's *name* and the model name. The URL, the key
and any headers are looked up on the backend at run time from the endpoint
config and `.env`. Keys never reach the browser, and any key a server echoes
back in an error message is masked before it is shown or returned.

**Protocols.** Each endpoint speaks one of three protocols:

| provider    | Used for                                                        |
| ----------- | --------------------------------------------------------------- |
| `openai`    | OpenAI, Gemini, Grok, Groq, OpenRouter, Mistral, DeepSeek, LM Studio, llama.cpp, vLLM, KoboldCpp… |
| `anthropic` | Claude                                                          |
| `ollama`    | Ollama's native API (for `keep_alive`, `num_ctx`, `think`)      |

**Parameters that don't fit.** Models differ in what they accept: OpenAI's
reasoning models refuse `temperature`, some servers don't know `seed`. For
Claude the node already knows which models dropped `temperature`/`top_p`
(Sonnet 5, Opus 4.7 and later, Fable) and doesn't send them. When an endpoint rejects a
parameter by name, the node drops it (or renames `max_tokens` ↔
`max_completion_tokens`) and retries, then reports what it changed in
`status`.

**Live preview.** Replies stream onto the node as they are written, with
reasoning in a collapsible 💭 section, then show token counts and speed.
Cancelling the queue stops a streaming request. Turn it off under
**Settings → ⚡MNeMiC Nodes → Universal LLM API** if an endpoint can't stream.
The console log and the request timeout (default 300 s) are there too.

## Adding your own endpoints

Edit `nodes/llm/UserEndpoints.json` (created on first run, git-ignored), then
press **R** in ComfyUI to refresh node definitions:

```json
{
    "endpoints": [
        {
            "name": "Office vLLM",
            "provider": "openai",
            "base_url": "${OFFICE_VLLM_URL}",
            "api_key_env": "OFFICE_VLLM_KEY",
            "default_model": "Qwen/Qwen3-32B"
        },
        {"name": "Mistral", "enabled": false}
    ]
}
```

and in `.env`:

```
OFFICE_VLLM_URL=http://10.0.0.20:8000/v1
OFFICE_VLLM_KEY=...
```

| Field              | Meaning                                                              |
| ------------------ | -------------------------------------------------------------------- |
| `name`             | What the dropdown shows and the workflow saves. Keep it stable.      |
| `provider`         | `openai`, `anthropic` or `ollama`.                                   |
| `base_url`         | Server address. `${VAR}` and `${VAR:-fallback}` read from `.env`.   |
| `api_key_env`      | Name of the `.env` variable holding the key.                         |
| `api_key_optional` | `true` if the server works without one.                              |
| `default_model`    | Used when the node's model field is empty.                           |
| `models`           | Fallback list for the model browser if the server can't list them.  |
| `headers`          | Extra HTTP headers; values may use `${VAR}`.                         |
| `extra_body`       | Extra JSON merged into every request body.                           |
| `options`          | `{"max_tokens_param": "max_completion_tokens"}` for newer OpenAI models. |
| `enabled`          | `false` hides the endpoint, including a built-in one of that name.   |

An entry with the same name as a built-in replaces it.

## Notes

This node only runs when something downstream uses its output, and reuses its
cached reply while its inputs are unchanged. Change the seed to force a fresh
reply.
