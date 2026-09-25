"""Wire protocols for the Universal LLM node.

Three protocols cover practically every LLM server:

- `openai`    — the OpenAI chat-completions shape. OpenAI, Groq, xAI, Gemini,
                OpenRouter, Mistral, DeepSeek, LM Studio, llama.cpp, vLLM…
- `anthropic` — Anthropic's Messages API.
- `ollama`    — Ollama's native API, for `keep_alive`, `num_ctx` and `think`,
                which its OpenAI shim does not expose.

Each adapter turns a ChatRequest into (url, headers, body), and turns the
reply — whole or streamed — back into text. `run_chat` does the HTTP around it:
retries, backoff, live streaming, interrupts, and dropping parameters an
endpoint rejects.
"""

import base64
import json
import re
import time
from dataclasses import dataclass, field
from io import BytesIO

import requests

from .env_manager import redact

RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504, 529}
MAX_IMAGE_SIDE = 2048
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_DEFAULT_MAX_TOKENS = 4096
ANTHROPIC_THINKING_BUDGET = {"minimal": 1024, "low": 2048, "medium": 8192, "high": 24576}

# Parameters an endpoint may reject, in the order they are given up. When a
# 400/422 names one of these, it is dropped (or renamed) and the call retried.
_ADJUSTABLE = {
    "openai": ["stream_options", "reasoning_effort", "seed", "top_p", "temperature", "stop",
               "response_format", "max_tokens", "max_completion_tokens"],
    "anthropic": ["top_p", "temperature", "thinking", "stop_sequences"],
    "ollama": ["think", "format"],
}
_RENAMES = {"max_tokens": "max_completion_tokens", "max_completion_tokens": "max_tokens"}


class LLMError(Exception):
    def __init__(self, message, status="error"):
        super().__init__(message)
        self.status = status


@dataclass
class ChatRequest:
    model: str
    system: str = ""
    user: str = ""
    images: list = field(default_factory=list)      # PIL images
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int = 0
    seed: int | None = None
    stop: list = field(default_factory=list)
    json_mode: bool = False
    reasoning: str = "default"                      # default | none | minimal | low | medium | high
    keep_alive: str | None = None                   # Ollama only
    context_length: int = 0                         # Ollama only
    stream: bool = True


@dataclass
class ChatResult:
    text: str = ""
    thinking: str = ""
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str = ""
    seconds: float = 0.0
    adjustments: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def encode_images(images):
    """PIL images → list of (mime, base64). Large images are scaled down."""
    encoded = []
    for image in images:
        image = image.convert("RGB")
        if max(image.size) > MAX_IMAGE_SIDE:
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        encoded.append(("image/jpeg", base64.b64encode(buffer.getvalue()).decode("ascii")))
    return encoded


_THINK_BLOCK = re.compile(r"<(think|thinking|reasoning)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN_ONLY = re.compile(r"^\s*<(think|thinking|reasoning)>(.*)$", re.DOTALL | re.IGNORECASE)
_THINK_CLOSE_ONLY = re.compile(r"^(.*?)</(think|thinking|reasoning)>", re.DOTALL | re.IGNORECASE)


def split_thinking(text):
    """Move inline <think>…</think> reasoning out of the reply.

    Returns (reply, thinking). Also handles templates that put the opening
    tag in the prompt (reply starts mid-thought and only has `</think>`), and
    replies cut off mid-thought (only `<think>`).
    """
    if not text:
        return text, ""
    thoughts = [m.group(2).strip() for m in _THINK_BLOCK.finditer(text)]
    text = _THINK_BLOCK.sub("", text)
    match = _THINK_CLOSE_ONLY.match(text)
    if match and "<" + match.group(2) not in match.group(1).lower():
        thoughts.insert(0, match.group(1).strip())
        text = text[match.end():]
    match = _THINK_OPEN_ONLY.match(text)
    if match:
        thoughts.append(match.group(2).strip())
        text = ""
    return text.strip(), "\n\n".join(t for t in thoughts if t)


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def strip_code_fence(text):
    match = _FENCE.match(text or "")
    return match.group(1) if match else text


def _json_instruction(system, user):
    """OpenAI-style JSON mode requires the word 'JSON' in the prompt."""
    if "json" in (system + user).lower():
        return system
    note = "Respond only with valid JSON."
    return f"{system}\n\n{note}".strip()


def _error_text(response):
    try:
        data = response.json()
    except ValueError:
        return response.text.strip()[:2000]
    if isinstance(data, dict):
        err = data.get("error", data)
        if isinstance(err, dict):
            return str(err.get("message") or err.get("error") or json.dumps(err))[:2000]
        return str(err)[:2000]
    return json.dumps(data)[:2000]


def _iter_sse(response):
    """Yield (event, data) from a Server-Sent Events stream."""
    event, data_lines = None, []
    for raw in response.iter_lines(decode_unicode=False):
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line == "":
            if data_lines:
                yield event, "\n".join(data_lines)
            event, data_lines = None, []
            continue
        if line.startswith(":"):
            continue
        key, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if key == "event":
            event = value
        elif key == "data":
            data_lines.append(value)
    if data_lines:
        yield event, "\n".join(data_lines)


# --------------------------------------------------------------------------
# Adapters
# --------------------------------------------------------------------------

class OpenAIAdapter:
    name = "openai"

    def headers(self, ep):
        headers = {"Content-Type": "application/json"}
        if ep.api_key:
            headers["Authorization"] = f"Bearer {ep.api_key}"
        return headers | ep.headers

    def chat_url(self, ep):
        return f"{ep.base_url}/chat/completions"

    def build(self, ep, req):
        system = _json_instruction(req.system, req.user) if req.json_mode else req.system
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if req.images:
            content = [{"type": "text", "text": req.user}]
            for mime, data in encode_images(req.images):
                content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": req.user})

        body = {"model": req.model, "messages": messages}
        if req.temperature is not None:
            body["temperature"] = req.temperature
        if req.top_p is not None and req.top_p < 1.0:
            body["top_p"] = req.top_p
        if req.max_tokens:
            body[ep.endpoint.options.get("max_tokens_param", "max_tokens")] = req.max_tokens
        if req.seed is not None:
            body["seed"] = req.seed
        if req.stop:
            body["stop"] = req.stop
        if req.json_mode:
            body["response_format"] = {"type": "json_object"}
        if req.reasoning != "default":
            body["reasoning_effort"] = req.reasoning
        if req.stream:
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}
        return body

    def parse(self, data, result):
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        result.text = content or ""
        result.thinking = message.get("reasoning_content") or message.get("reasoning") or ""
        result.finish_reason = choice.get("finish_reason") or ""
        result.model = data.get("model", "")
        usage = data.get("usage") or {}
        result.input_tokens = usage.get("prompt_tokens")
        result.output_tokens = usage.get("completion_tokens")

    def stream(self, response, result):
        for _event, data in _iter_sse(response):
            if data.strip() == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("error"):
                raise LLMError(str(chunk["error"].get("message", chunk["error"])) if isinstance(chunk["error"], dict) else str(chunk["error"]))
            result.model = chunk.get("model") or result.model
            usage = chunk.get("usage")
            if usage:
                result.input_tokens = usage.get("prompt_tokens")
                result.output_tokens = usage.get("completion_tokens")
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                thinking = delta.get("reasoning_content") or delta.get("reasoning")
                if thinking:
                    yield "thinking", thinking
                if delta.get("content"):
                    yield "text", delta["content"]
                if choice.get("finish_reason"):
                    result.finish_reason = choice["finish_reason"]

    def list_models(self, ep, timeout):
        response = requests.get(f"{ep.base_url}/models", headers=self.headers(ep), timeout=timeout)
        _raise_for_status(response)
        models = []
        for item in response.json().get("data", []):
            detail = []
            ctx = item.get("context_length") or item.get("context_window") or item.get("max_model_len")
            if ctx:
                detail.append(f"{int(ctx) // 1024}k ctx" if int(ctx) >= 1024 else f"{ctx} ctx")
            if item.get("owned_by") and item["owned_by"] not in ("system", "organization-owner"):
                detail.append(str(item["owned_by"]))
            models.append({"id": item["id"], "detail": " · ".join(detail)})
        return sorted(models, key=lambda m: m["id"].lower())


class AnthropicAdapter:
    name = "anthropic"

    def headers(self, ep):
        headers = {"Content-Type": "application/json", "anthropic-version": ANTHROPIC_VERSION}
        if ep.api_key:
            headers["x-api-key"] = ep.api_key
        return headers | ep.headers

    def chat_url(self, ep):
        return f"{ep.base_url}/messages"

    def build(self, ep, req):
        system = req.system
        if req.json_mode and "json" not in (system + req.user).lower():
            system = f"{system}\n\nRespond only with valid JSON, no code fences.".strip()
        if req.images:
            content = [{"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}
                       for mime, data in encode_images(req.images)]
            content.append({"type": "text", "text": req.user})
        else:
            content = req.user
        body = {
            "model": req.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": req.max_tokens or ANTHROPIC_DEFAULT_MAX_TOKENS,
        }
        if system:
            body["system"] = system
        if req.stop:
            body["stop_sequences"] = req.stop
        budget = ANTHROPIC_THINKING_BUDGET.get(req.reasoning)
        if budget:
            # Extended thinking spends from max_tokens and fixes the sampling
            # parameters, so the reply keeps its full budget on top.
            body["thinking"] = {"type": "enabled", "budget_tokens": budget}
            body["max_tokens"] += budget
        else:
            if req.temperature is not None:
                body["temperature"] = min(req.temperature, 1.0)
            if req.top_p is not None and req.top_p < 1.0:
                body["top_p"] = req.top_p
        if req.stream:
            body["stream"] = True
        return body

    def parse(self, data, result):
        for block in data.get("content", []):
            if block.get("type") == "text":
                result.text += block.get("text", "")
            elif block.get("type") == "thinking":
                result.thinking += block.get("thinking", "")
        result.model = data.get("model", "")
        result.finish_reason = data.get("stop_reason") or ""
        usage = data.get("usage") or {}
        result.input_tokens = usage.get("input_tokens")
        result.output_tokens = usage.get("output_tokens")

    def stream(self, response, result):
        for event, data in _iter_sse(response):
            chunk = json.loads(data)
            kind = chunk.get("type", event)
            if kind == "error":
                raise LLMError(chunk.get("error", {}).get("message", data))
            if kind == "message_start":
                message = chunk.get("message", {})
                result.model = message.get("model", "")
                result.input_tokens = (message.get("usage") or {}).get("input_tokens")
            elif kind == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield "text", delta.get("text", "")
                elif delta.get("type") == "thinking_delta":
                    yield "thinking", delta.get("thinking", "")
            elif kind == "message_delta":
                result.finish_reason = (chunk.get("delta") or {}).get("stop_reason") or result.finish_reason
                output = (chunk.get("usage") or {}).get("output_tokens")
                if output is not None:
                    result.output_tokens = output
            elif kind == "message_stop":
                break

    def list_models(self, ep, timeout):
        response = requests.get(f"{ep.base_url}/models", params={"limit": 1000}, headers=self.headers(ep), timeout=timeout)
        _raise_for_status(response)
        return [{"id": m["id"], "detail": m.get("display_name", "")} for m in response.json().get("data", [])]


class OllamaAdapter:
    name = "ollama"

    def headers(self, ep):
        headers = {"Content-Type": "application/json"}
        if ep.api_key:
            headers["Authorization"] = f"Bearer {ep.api_key}"
        return headers | ep.headers

    def chat_url(self, ep):
        return f"{ep.base_url}/api/chat"

    def build(self, ep, req):
        messages = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        user = {"role": "user", "content": req.user}
        if req.images:
            user["images"] = [data for _mime, data in encode_images(req.images)]
        messages.append(user)

        options = {}
        if req.temperature is not None:
            options["temperature"] = req.temperature
        if req.top_p is not None and req.top_p < 1.0:
            options["top_p"] = req.top_p
        if req.max_tokens:
            options["num_predict"] = req.max_tokens
        if req.seed is not None:
            options["seed"] = req.seed
        if req.stop:
            options["stop"] = req.stop
        if req.context_length:
            options["num_ctx"] = req.context_length

        body = {"model": req.model, "messages": messages, "stream": req.stream, "options": options}
        if req.json_mode:
            body["format"] = "json"
        if req.reasoning == "none":
            body["think"] = False
        elif req.reasoning != "default":
            # gpt-oss takes a level; other thinking models only on/off.
            body["think"] = req.reasoning if "gpt-oss" in req.model.lower() and req.reasoning != "minimal" else True
        if req.keep_alive is not None:
            body["keep_alive"] = req.keep_alive
        return body

    def _apply_final(self, data, result):
        result.model = data.get("model", result.model)
        result.finish_reason = data.get("done_reason") or result.finish_reason
        result.input_tokens = data.get("prompt_eval_count", result.input_tokens)
        result.output_tokens = data.get("eval_count", result.output_tokens)

    def parse(self, data, result):
        message = data.get("message") or {}
        result.text = message.get("content", "")
        result.thinking = message.get("thinking", "")
        self._apply_final(data, result)

    def stream(self, response, result):
        for raw in response.iter_lines(decode_unicode=False):
            if not raw:
                continue
            chunk = json.loads(raw)
            if chunk.get("error"):
                raise LLMError(str(chunk["error"]))
            message = chunk.get("message") or {}
            if message.get("thinking"):
                yield "thinking", message["thinking"]
            if message.get("content"):
                yield "text", message["content"]
            if chunk.get("done"):
                self._apply_final(chunk, result)
                break

    def list_models(self, ep, timeout):
        headers = self.headers(ep)
        response = requests.get(f"{ep.base_url}/api/tags", headers=headers, timeout=timeout)
        _raise_for_status(response)
        loaded = set()
        try:
            ps = requests.get(f"{ep.base_url}/api/ps", headers=headers, timeout=timeout)
            if ps.ok:
                loaded = {m.get("name") for m in ps.json().get("models", [])}
        except requests.RequestException:
            pass
        models = []
        for item in response.json().get("models", []):
            details = item.get("details") or {}
            detail = [d for d in (details.get("parameter_size"), details.get("quantization_level")) if d]
            if item.get("size"):
                detail.append(f"{item['size'] / 1e9:.1f} GB")
            models.append({"id": item["name"], "detail": " · ".join(detail), "loaded": item["name"] in loaded})
        return sorted(models, key=lambda m: (not m["loaded"], m["id"].lower()))


ADAPTERS = {a.name: a for a in (OpenAIAdapter(), AnthropicAdapter(), OllamaAdapter())}


def get_adapter(provider):
    return ADAPTERS[provider]


def _raise_for_status(response):
    if not response.ok:
        raise LLMError(redact(f"{response.status_code} {response.reason}: {_error_text(response)}"),
                       status=f"{response.status_code} {response.reason}")


# --------------------------------------------------------------------------
# Running a request
# --------------------------------------------------------------------------

def _adjust_for_rejection(provider, body, error_text, already):
    """Drop or rename the first parameter the error names.

    Returns None if nothing matched, else a note for the status line ("" when
    the change is not worth reporting).
    """
    lowered = error_text.lower()
    for key in _ADJUSTABLE.get(provider, []):
        if key in body and key not in already and key in lowered:
            already.add(key)
            renamed = _RENAMES.get(key)
            if renamed and renamed not in already:
                body[renamed] = body.pop(key)
                already.add(renamed)
                return f"renamed {key} → {renamed}"
            body.pop(key)
            return "" if key == "stream_options" else f"dropped {key}"
    return None


def _wait(seconds, check_interrupt):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check_interrupt:
            check_interrupt()
        time.sleep(min(0.25, max(0.0, end - time.monotonic())))


def _retry_delay(response, attempt):
    header = response.headers.get("retry-after") if response is not None else None
    try:
        if header:
            return min(float(header), 60.0)
    except ValueError:
        pass
    return min(1.5 * (2 ** attempt), 20.0)


def run_chat(ep, req, *, timeout=300, max_retries=2, on_delta=None, check_interrupt=None, log=None):
    """Send a chat request to a resolved endpoint and return a ChatResult.

    on_delta(text, thinking) is called with the accumulated reply while
    streaming. check_interrupt() is called between chunks and during backoff
    and should raise to abort. log(message) gets redacted diagnostics.
    """
    adapter = get_adapter(ep.endpoint.provider)
    url = adapter.chat_url(ep)
    headers = adapter.headers(ep)
    body = adapter.build(ep, req)
    body.update(ep.endpoint.extra_body or {})

    result = ChatResult()
    adjusted = set()
    attempt = 0
    started = time.monotonic()

    while True:
        if check_interrupt:
            check_interrupt()
        if log:
            log(f"POST {url}\n{json.dumps(_loggable(body), indent=2, ensure_ascii=False)}")
        response = None
        try:
            response = requests.post(url, headers=headers, json=body, stream=bool(body.get("stream")),
                                     timeout=(15, timeout))
        except requests.RequestException as e:
            if attempt >= max_retries:
                raise LLMError(redact(f"Could not reach {ep.endpoint.name}: {_short_exception(e)}"), status="connection error")
            if log:
                log(f"Connection failed ({_short_exception(e)}); retrying.")
            _wait(_retry_delay(None, attempt), check_interrupt)
            attempt += 1
            continue

        if response.status_code in (400, 422):
            error_text = _error_text(response)
            note = _adjust_for_rejection(ep.endpoint.provider, body, error_text, adjusted)
            if note is not None:
                response.close()
                if note:
                    result.adjustments.append(note)
                if log:
                    log(f"Endpoint rejected a parameter ({redact(error_text[:200])}); {note or 'dropped stream_options'}, retrying.")
                continue

        if response.status_code in RETRY_STATUSES and attempt < max_retries:
            delay = _retry_delay(response, attempt)
            if log:
                log(f"{response.status_code} {response.reason}; retrying in {delay:.1f}s.")
            response.close()
            _wait(delay, check_interrupt)
            attempt += 1
            continue

        _raise_for_status(response)
        break

    try:
        if body.get("stream"):
            text_parts, thinking_parts = [], []
            last_push = 0.0
            for kind, piece in adapter.stream(response, result):
                (text_parts if kind == "text" else thinking_parts).append(piece)
                if check_interrupt:
                    check_interrupt()
                now = time.monotonic()
                if on_delta and now - last_push > 0.08:
                    last_push = now
                    on_delta("".join(text_parts), "".join(thinking_parts))
            result.text = "".join(text_parts)
            result.thinking = "".join(thinking_parts)
        else:
            adapter.parse(response.json(), result)
    except (ValueError, requests.RequestException) as e:
        raise LLMError(redact(f"Bad response from {ep.endpoint.name}: {_short_exception(e)}"), status="bad response")
    finally:
        response.close()

    result.seconds = time.monotonic() - started
    inline_reply, inline_thinking = split_thinking(result.text)
    result.text = inline_reply
    result.thinking = "\n\n".join(t for t in (result.thinking.strip(), inline_thinking) if t)
    if req.json_mode:
        result.text = strip_code_fence(result.text)
    return result


def _short_exception(e):
    if isinstance(e, requests.Timeout):
        return "timed out"
    text = str(e)
    match = re.search(r"\[Errno -?\d+\] ([^'\")]+)|Failed to establish a new connection: ([^'\")]+)", text)
    if match:
        return (match.group(1) or match.group(2)).strip()
    match = re.search(r"Caused by (\w+)\('([^']+)'", text)
    if match:
        return f"{match.group(1)}: {match.group(2)}"
    return text[:300]


def _loggable(body):
    """The request body with image data shortened, for console logs."""
    def shrink(value):
        if isinstance(value, dict):
            return {k: shrink(v) for k, v in value.items()}
        if isinstance(value, list):
            return [shrink(v) for v in value]
        if isinstance(value, str) and len(value) > 300 and re.fullmatch(r"[A-Za-z0-9+/=:;,.\-_a-z]+", value[:300]):
            return f"<{len(value)} chars of image data>"
        return value
    return shrink(body)


def list_models(ep, timeout=15):
    """Models the endpoint reports, falling back to the configured list."""
    adapter = get_adapter(ep.endpoint.provider)
    try:
        return adapter.list_models(ep, timeout)
    except requests.RequestException as e:
        raise LLMError(redact(f"Could not reach {ep.endpoint.name}: {_short_exception(e)}"), status="connection error")
    except (ValueError, KeyError) as e:
        raise LLMError(f"Unexpected model list from {ep.endpoint.name}: {e}", status="bad response")
