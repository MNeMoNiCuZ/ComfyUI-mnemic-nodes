# ✨💬 Groq LLM API

Sends a prompt to a text model on Groq's API and returns the reply. Useful for
expanding a short idea into a full prompt, rewriting, or classifying text
inside a workflow.

## Setup

The node reads your API key from the `.env` file in the pack folder, creating a
blank one on first run. Put your key from
[console.groq.com](https://console.groq.com) in it:

```
GROQ_API_KEY=your_key_here
```

Restart ComfyUI after editing it.

## Inputs

- **model** — Which model to call. The list follows Groq's current line-up;
  models they retire stop working and are removed here over time.
- **preset** — A saved system prompt, or the default entry to use the
  `system_message` field instead.
- **system_message** — Instructions setting the model's role. Only used when
  `preset` is the default entry.
- **user_input** — The actual request.
- **temperature** — Randomness. Low is focused and repeatable, high is
  creative.

Advanced:

- **max_tokens** — Length cap on the reply.
- **top_p** — Nucleus sampling cutoff. 1.0 considers every candidate word.
- **seed** — Sent to the API for repeatable replies.
- **max_retries** — Attempts before giving up.
- **stop** — Stop generating when this text appears.
- **json_mode** — Force valid JSON output. The word JSON must also appear in
  your prompt, or the API rejects the request.

## Outputs

- **api_response** — The generated text.
- **success** — False on any error, so you can branch on it.
- **status_code** — HTTP status, e.g. `200 OK`.

## Presets

Presets come from `nodes/groq/DefaultPrompts.json` (shipped) and
`nodes/groq/UserPrompts.json` (yours). Each entry is `{"name": ..., "content":
...}`; the name shows in the dropdown. Restart ComfyUI after editing.

## Notes

This node is not an output node: it only runs when something downstream needs
its result, so an unconnected copy costs you nothing. Turn on
**Settings → ⚡MNeMiC Nodes → Groq LLM → Console Logging** to see the request
and reply; the request timeout is in the same place.
