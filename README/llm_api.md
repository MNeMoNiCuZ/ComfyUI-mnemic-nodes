# ✨🧠 Universal LLM API

One node for every language model: ChatGPT, Claude, Gemini, Grok, Groq,
OpenRouter, Mistral, DeepSeek, and local servers like Ollama and LM Studio,
either on your own PC or elsewhere on your network. It shares its prompt
presets with the Groq nodes.

### Features

- **12 endpoints built in**, and any number of your own in
  `nodes/llm/UserEndpoints.json`.
- **Nothing secret in your workflows.** Keys and private addresses live in
  `.env`. A shared workflow or image only contains the endpoint name and the
  model name.
- **Status panel on the node** showing where the endpoint runs (🖥 this PC,
  🏠 network, ☁ cloud), whether its key is set, and what is missing if not.
- **🔍 Model browser**: a searchable list of the models the endpoint offers,
  with context size, parameter count and quantization, and which Ollama models
  are already in memory.
- **⚡ Connection test** and **📜 preset viewer**.
- **Live streaming preview** of the reply, with a collapsible 💭 thinking
  section, token counts and speed.
- **Vision**: connect images and every image in the batch is sent.
- **Reasoning control**: one setting maps to `reasoning_effort` (OpenAI-style),
  `think` (Ollama) or Claude's extended thinking.
- **Self-correcting requests**: parameters a model refuses (e.g. `temperature`
  on OpenAI reasoning models) are dropped and the call retried automatically.
- **Retries** with backoff on rate limits and server errors, and Cancel stops a
  streaming request mid-reply.
- **VRAM friendly for local models**: unload the Ollama model after replying,
  or free ComfyUI's models before the call.

### Setup

1. Start ComfyUI once. A `.env` file is created in this pack's folder from
   `.env.example`.
2. Fill in the keys and addresses you use, e.g.:
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   OLLAMA_NETWORK_URL=http://192.168.1.50:11434
   ```
3. Pick the endpoint on the node. Its status panel turns green when it is
   ready.

Ollama and LM Studio running on the same PC need no setup.

The full reference, covering every input, adding endpoints and every config
field, is in the node's help panel (the **?** on the node), or
[here](../web/docs/MNeMiC_LLMAPI.md).
