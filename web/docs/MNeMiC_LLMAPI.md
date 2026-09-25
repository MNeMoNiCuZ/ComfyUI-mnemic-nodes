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
- **model** — Model name. Empty uses the endpoint's default model. Endpoints
  on this PC or your network without one use the first chat model the
  server lists, skipping embedding models (for Ollama, a model already in
  memory if there is one, else the first installed one alphabetically);
  cloud endpoints without one need a model chosen. Click **🔍 Models** to browse and search what the
  endpoint offers; Ollama models already in memory are marked.
- **preset** — A saved system prompt, or the first entry to use
  `system_message`. Click **📜 Preset** to read the selected one.
- **system_message** — The model's instructions. Ignored while a preset is
  active; in the classic node view it is also greyed out and shows the
  preset's text as a hint (📜 Preset shows it in either view).
- **user_input** — The request. May be empty: the system message (or preset)
  is then sent on its own as the request.
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

**Protocols.** Each endpoint speaks one of these:

| provider     | Used for                                                        |
| ------------ | --------------------------------------------------------------- |
| `openai`     | OpenAI, Gemini, Grok, Groq, OpenRouter, Mistral, DeepSeek, LM Studio, llama.cpp, vLLM, KoboldCpp… |
| `anthropic`  | Claude                                                          |
| `ollama`     | Ollama's native API (for `keep_alive`, `num_ctx`, `think`)      |
| `claude_cli` | The Claude Code CLI on this PC, with your Claude subscription   |
| `codex_cli`  | The Codex CLI on this PC, with your ChatGPT subscription        |

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

## Local subscriptions (Claude Code, Codex)

**Local Claude Code Subscription** and **Local Codex Subscription** run the
CLI installed on this PC instead of calling an API, so they use your Claude or
ChatGPT subscription and need no API key.

- Install the CLI and sign in once in a terminal: run `claude`, or
  `codex login`. If the command isn't on your PATH, set `CLAUDE_CLI` or
  `CODEX_CLI` in `.env` to its full path.
- Claude Code runs as `claude -p` with all tools and MCP servers turned off, so
  it answers as a plain model. Codex runs as `codex exec` (Codex's own `-p` is
  a profile flag, not print mode) with its tool features disabled, in a
  read-only sandbox in an empty temporary folder.
- API-key variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`…) are removed from
  the CLI's environment, so your subscription login is what gets used.
- **model** is optional: empty uses the CLI's default. Claude Code accepts
  aliases like `sonnet`, `opus`, `haiku`, `fable`; 🔍 Models lists them.
- **images** work with both. **reasoning** sets the effort level.
  `temperature`, `top_p`, `seed`, `max_tokens` and `stop` are not supported
  by the CLIs and are ignored.
- Each call starts the CLI fresh, which takes a few seconds. Replies still
  stream onto the node.

## Custom Endpoint - WARNING

The last entry in the endpoint list lets you enter a server's address and key
on the node itself, without editing any file. Pick it and a panel appears with
the protocol (OpenAI-compatible, Anthropic, Ollama), the address and the key;
press **💾 Save**.

**What is kept where.** The address and key are stored on this ComfyUI machine
only, in `nodes/llm/CustomEndpoints.local.json` (git-ignored, plain text). The
workflow keeps just a random id in the `custom_endpoint` input, so a shared
workflow or image never contains the address or key. The key is never sent
back to the browser either: the panel only shows whether one is saved. Leave
the key field empty when saving to keep the saved key.

**Risks — read before using it:**

- The file is plain text: anyone with access to this machine's files can read
  the key, just as with `.env`.
- Anyone who can open this ComfyUI in a browser can use a saved custom endpoint
  in their own workflow, see its address (not its key), and point the server at
  any address they like. Don't leave a key for a paid service in a custom
  endpoint on a ComfyUI that others can reach.
- Your prompts and images go to whatever server you enter. Only use servers
  you trust.
- A workflow shared with someone else won't work for them until they enter
  their own address and key.
- Copies of the node share the same saved endpoint; saving in one changes all.

For anything permanent, prefer a named endpoint in `UserEndpoints.json` with
its key in `.env` (below).

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
| `provider`         | `openai`, `anthropic`, `ollama`, `claude_cli` or `codex_cli`.        |
| `command`          | CLI providers only: the command or its full path; may use `${VAR}`.  |
| `base_url`         | Server address. `${VAR}` and `${VAR:-fallback}` read from `.env`.   |
| `api_key_env`      | Name of the `.env` variable holding the key.                         |
| `api_key_optional` | `true` if the server works without one.                              |
| `default_model`    | Used when the node's model field is empty.                           |
| `models`           | Fallback list for the model browser if the server can't list them.  |
| `headers`          | Extra HTTP headers; values may use `${VAR}`.                         |
| `extra_body`       | Extra JSON merged into every request body.                           |
| `options`          | `max_tokens_param` (e.g. `"max_completion_tokens"` for newer OpenAI models), `ensure_path` (a path such as `"/v1"` added to `base_url` when missing), `model_optional` (an empty model is sent as-is so the server picks), `keep_order` (keep the server's model-list order), `pin_last` (list the endpoint at the end). |
| `enabled`          | `false` hides the endpoint, including a built-in one of that name.   |

An entry with the same name as a built-in replaces it.

## Notes

This node only runs when something downstream uses its output, and reuses its
cached reply while its inputs are unchanged. Change the seed to force a fresh
reply.
