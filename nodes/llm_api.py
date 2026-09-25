import asyncio
import sys
import time

import numpy as np
from PIL import Image

from ..utils.env_manager import redact
from ..utils.llm_endpoints import load_endpoints
from ..utils.llm_providers import ChatRequest, LLMError, list_models, run_chat
from ..utils.prompt_presets import load_llm_presets
from ..utils.settings_utils import get_llm_request_timeout, is_llm_console_log_enabled, is_llm_live_preview_enabled

from comfy_api.latest import io

DEFAULT_PROMPT = "Use [system_message] and [user_input]"
REASONING_LEVELS = ["default", "none", "minimal", "low", "medium", "high"]
STREAM_EVENT = "mnemic.llm.stream"


def _current_client_id():
    """The websocket client that queued the running prompt, or None."""
    try:
        from server import PromptServer
        return PromptServer.instance.client_id
    except Exception:
        return None


def _send(event, data, client_id):
    # Only to the client that queued the prompt: replies must not be
    # broadcast to everyone connected to a shared ComfyUI server.
    if client_id is None:
        return
    try:
        from server import PromptServer
        PromptServer.instance.send_sync(event, data, client_id)
    except Exception:
        pass


def _check_interrupt():
    try:
        import comfy.model_management
        comfy.model_management.throw_exception_if_processing_interrupted()
    except ImportError:
        pass


def _free_comfy_vram():
    import comfy.model_management
    comfy.model_management.unload_all_models()
    comfy.model_management.soft_empty_cache()


def _log(message):
    line = f"\033[36m[MNeMiC LLM]\033[0m {redact(message)}"
    try:
        print(line)
    except UnicodeEncodeError:
        # A cp1252 console can't show emoji or CJK prompts; logging must
        # never be what fails the node.
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(line.encode(encoding, "replace").decode(encoding))


def _tensor_to_pil_list(images):
    if images is None:
        return []
    batch = images if images.ndim == 4 else images.unsqueeze(0)
    return [Image.fromarray(np.clip(img.cpu().numpy() * 255.0, 0, 255).astype(np.uint8)) for img in batch]


# Settings whose last run failed with raise_on_error off. Their result must
# not be served from ComfyUI's cache, or a transient 429/5xx/connection
# error would repeat on every queue until an input changes.
_FAILED_SIGNATURES = []
_MAX_FAILED = 64


def _signature(kwargs):
    return {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))}


def _recently_failed(constants):
    # ComfyUI passes fingerprint_inputs only the widget constants (linked
    # inputs are absent), so compare on the keys it gave us.
    return any(all(failed.get(k) == v for k, v in constants.items()) for failed in _FAILED_SIGNATURES)


class LLMAPI(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        endpoint_names = list(load_endpoints().keys()) or ["(no endpoints configured)"]
        try:
            presets = list(load_llm_presets().keys())
        except Exception as e:
            print(f"\033[91m[MNeMiC LLM] Failed to load prompt presets: {e}\033[0m")
            presets = []

        return io.Schema(
            node_id="MNeMiC_LLMAPI",
            display_name="✨🧠 Universal LLM API",
            category="⚡ MNeMiC Nodes",
            description="Sends a prompt, and optionally images, to any LLM: ChatGPT, Claude, Gemini, Grok, Groq, OpenRouter, or Ollama and LM Studio on this PC or your network.",
            search_aliases=["llm", "chat", "ollama", "openai", "chatgpt", "gpt", "claude", "anthropic", "gemini",
                            "grok", "xai", "groq", "openrouter", "lm studio", "llama.cpp", "vllm", "vlm", "prompt generator"],
            inputs=[
                io.Combo.Input("endpoint", options=endpoint_names, default=endpoint_names[0],
                               tooltip="Which server to talk to. Endpoints are defined in nodes/llm/*.json; keys and private addresses come from .env and are never saved in the workflow."),
                io.String.Input("model", default="",
                                tooltip="Model name as the endpoint knows it. Empty uses the endpoint's default model. Use the 🔍 Models button on the node to browse what the endpoint offers."),
                io.Combo.Input("preset", options=[DEFAULT_PROMPT] + presets, default=DEFAULT_PROMPT,
                               tooltip="A saved system prompt, shared with the Groq nodes. The first entry uses the system_message field instead."),
                io.String.Input("system_message", multiline=True, default="",
                                tooltip="Instructions setting the model's role and rules. Ignored while a preset is selected."),
                io.String.Input("user_input", multiline=True, default="",
                                tooltip="The request itself: what you want the model to write, rewrite or describe."),
                io.Image.Input("images", optional=True,
                               tooltip="Images to send along with the prompt, for vision models. Every image in the batch is sent."),
                io.Float.Input("temperature", default=0.8, min=0.0, max=2.0, step=0.05,
                               tooltip="Randomness. Low is focused and repeatable, high is varied and creative. Dropped automatically for models that only allow their default."),
                io.Combo.Input("reasoning", options=REASONING_LEVELS, default="default", advanced=True,
                               tooltip="How hard a reasoning model should think. 'default' sends nothing; 'none' turns thinking off where supported. On Claude this sets adaptive thinking's effort (a thinking budget on older models)."),
                io.Int.Input("max_tokens", default=0, min=0, max=262144, step=1, advanced=True,
                             tooltip="Maximum length of the reply in tokens. 0 leaves it to the server (Claude, which needs a value, gets 16000)."),
                io.Float.Input("top_p", default=1.0, min=0.0, max=1.0, step=0.01, advanced=True,
                               tooltip="Nucleus sampling: only consider the most likely words adding up to this probability. 1.0 disables it and is not sent."),
                io.Int.Input("seed", default=42, min=0, max=0xffffffff, advanced=True,
                             control_after_generate=io.ControlAfterGenerate.fixed,
                             tooltip="Sent to the endpoint for repeatable replies where supported. Changing it also forces a fresh reply instead of the cached one."),
                io.String.Input("stop", default="", advanced=True,
                                tooltip="Stop generating when this text appears. Separate several with |. Empty sends none."),
                io.Boolean.Input("json_mode", default=False, advanced=True,
                                 tooltip="Ask for a valid JSON reply. Code fences around the reply are removed."),
                io.Boolean.Input("unload_model_after", default=False, advanced=True,
                                 tooltip="Ollama only: unload the model from memory right after replying, so image generation gets the VRAM back."),
                io.Int.Input("context_length", default=0, min=0, max=1048576, step=256, advanced=True,
                             tooltip="Ollama only: context window in tokens (num_ctx). 0 uses the model's default."),
                io.Boolean.Input("free_comfy_vram", default=False, advanced=True,
                                 tooltip="Unload ComfyUI's models from VRAM before the call. Useful when a local LLM shares the GPU with ComfyUI."),
                io.Int.Input("max_retries", default=2, min=0, max=10, step=1, advanced=True,
                             tooltip="Extra attempts on connection errors, rate limits and server errors. 0 tries once."),
                io.Boolean.Input("raise_on_error", default=True, advanced=True,
                                 tooltip="Stop the workflow with an error when the call fails. Off returns an empty response and success = false instead, for branching."),
            ],
            outputs=[
                io.String.Output(display_name="response", tooltip="The model's reply, with any <think> reasoning removed."),
                io.String.Output(display_name="thinking", tooltip="The model's reasoning, when the endpoint returns it. Empty otherwise."),
                io.Boolean.Output(display_name="success", tooltip="True when the call succeeded. Only false when raise_on_error is off."),
                io.String.Output(display_name="status", tooltip="HTTP status or error message, e.g. '200 OK'. Never contains keys."),
            ],
            hidden=[io.Hidden.unique_id],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        if _recently_failed(_signature(kwargs)):
            return time.time()
        return ""

    @classmethod
    async def execute(cls, endpoint, model, preset, system_message, user_input, temperature,
                      reasoning="default", max_tokens=0, top_p=1.0, seed=42, stop="", json_mode=False,
                      unload_model_after=False, context_length=0, free_comfy_vram=False, max_retries=2,
                      raise_on_error=True, images=None) -> io.NodeOutput:
        signature = _signature(dict(
            endpoint=endpoint, model=model, preset=preset, system_message=system_message, user_input=user_input,
            temperature=temperature, reasoning=reasoning, max_tokens=max_tokens, top_p=top_p, seed=seed, stop=stop,
            json_mode=json_mode, unload_model_after=unload_model_after, context_length=context_length,
            free_comfy_vram=free_comfy_vram, max_retries=max_retries, raise_on_error=raise_on_error))
        if signature in _FAILED_SIGNATURES:
            _FAILED_SIGNATURES.remove(signature)
        node_id = cls.hidden.unique_id if cls.hidden else None
        client_id = _current_client_id()
        console_log = is_llm_console_log_enabled()
        log = _log if console_log else None

        def fail(message, status="error"):
            message = redact(message)
            _send(STREAM_EVENT, {"node": node_id, "phase": "error", "error": message}, client_id)
            if signature not in _FAILED_SIGNATURES:
                _FAILED_SIGNATURES.append(signature)
                del _FAILED_SIGNATURES[:-_MAX_FAILED]
            if raise_on_error:
                # from None: the chained original error would otherwise be
                # printed in ComfyUI's traceback.
                raise RuntimeError(f"✨🧠 Universal LLM API — {message}") from None
            return io.NodeOutput("", "", False, message,
                                 ui={"mnemic_llm": [{"ok": False, "error": message, "status": status}]})

        ep_config = load_endpoints().get(endpoint)
        if ep_config is None:
            return fail(f"Endpoint '{endpoint}' is not configured. Check nodes/llm/UserEndpoints.json.")
        ep = ep_config.resolve()
        if not ep.ok:
            return fail(f"{endpoint}: {' '.join(ep.problems)}", "not configured")

        model = (model or "").strip() or ep_config.default_model
        if not model and ep_config.provider == "ollama":
            try:
                available = await asyncio.to_thread(list_models, ep)
            except LLMError as e:
                return fail(str(e), e.status)
            model = available[0]["id"] if available else ""
        if not model:
            return fail(f"No model chosen for {endpoint}. Type one in, or click 🔍 Models on the node.")

        if preset != DEFAULT_PROMPT:
            system_message = load_llm_presets().get(preset, system_message)

        request = ChatRequest(
            model=model,
            system=system_message or "",
            user=user_input or "",
            images=_tensor_to_pil_list(images),
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            stop=[s for s in (stop or "").split("|") if s],
            json_mode=json_mode,
            reasoning=reasoning,
            keep_alive=0 if unload_model_after else None,
            context_length=context_length,
            stream=is_llm_live_preview_enabled() and node_id is not None and client_id is not None,
        )
        if not request.user and not request.images:
            return fail("user_input is empty and no images are connected; there is nothing to send.")

        if free_comfy_vram:
            await asyncio.to_thread(_free_comfy_vram)

        _send(STREAM_EVENT, {"node": node_id, "phase": "start", "endpoint": endpoint, "model": model}, client_id)

        def on_delta(text, thinking):
            _send(STREAM_EVENT, {"node": node_id, "phase": "stream", "text": text, "thinking": thinking}, client_id)

        try:
            result = await asyncio.to_thread(
                run_chat, ep, request,
                timeout=get_llm_request_timeout(), max_retries=max_retries,
                on_delta=on_delta, check_interrupt=_check_interrupt, log=log,
            )
        except LLMError as e:
            return fail(str(e), e.status)

        status = "200 OK"
        if result.adjustments:
            status += f" ({', '.join(result.adjustments)})"
        if not result.text and result.finish_reason in ("length", "max_tokens"):
            hint = "the reply hit max_tokens before any text"
            if result.thinking:
                hint += " (the model spent it thinking)"
            return fail(f"{endpoint}: {hint}. Raise max_tokens or lower reasoning.", "length")

        if log:
            _log(f"{result.model or model}: {result.output_tokens} tokens in {result.seconds:.1f}s\n{result.text}")

        summary = {
            "ok": True,
            "text": result.text,
            "thinking": result.thinking,
            "endpoint": endpoint,
            "model": result.model or model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "seconds": round(result.seconds, 2),
            "finish_reason": result.finish_reason,
            "status": status,
        }
        return io.NodeOutput(result.text, result.thinking, True, status, ui={"mnemic_llm": [summary]})
