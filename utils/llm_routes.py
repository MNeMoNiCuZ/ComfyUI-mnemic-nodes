"""HTTP routes behind the Universal LLM node's UI (web/js/llm_api.js).

Endpoints are addressed by name only; the browser never receives a key or a
header value. Model listing happens here, server-side, because the key must
not reach the browser.

The one exception to "name only" is the custom endpoint: its panel sends the
address and key it was given to /mnemic/llm/custom, which stores them on this
machine and hands back an id. The key is never sent back.
"""

import asyncio
import time

from urllib.parse import urlparse

from .llm_custom import CUSTOM_ENDPOINT_NAME, CUSTOM_PROVIDERS, custom_endpoint, get_custom, save_custom
from .llm_endpoints import load_endpoints
from .llm_providers import LLMError, list_models
from .prompt_presets import load_llm_presets

_registered = False


def register_llm_routes():
    global _registered
    if _registered:
        return
    try:
        from aiohttp import web
        from server import PromptServer
    except ImportError:
        return
    routes = PromptServer.instance.routes

    @routes.get("/mnemic/llm/endpoints")
    async def llm_endpoints(request):
        endpoints = await asyncio.to_thread(lambda: [ep.resolve().public_info() for ep in load_endpoints().values()])
        endpoints.append({
            "name": CUSTOM_ENDPOINT_NAME, "provider": "custom", "is_custom": True, "description": "",
            "default_model": "", "location": "unknown", "host": "", "key_env": "", "key_set": False,
            "key_optional": True, "is_cli": False, "model_optional": False, "ok": True, "problems": [],
        })
        return web.json_response({"endpoints": endpoints})

    @routes.get("/mnemic/llm/custom")
    async def llm_custom_get(request):
        entry = get_custom(request.query.get("id", ""))
        if not entry:
            return web.json_response({"ok": False, "providers": list(CUSTOM_PROVIDERS)})
        parsed = urlparse(entry.get("base_url", ""))
        # The address without any user:password@ part; never the key.
        shown = parsed._replace(netloc=parsed.netloc.rsplit("@", 1)[-1]).geturl()
        info = custom_endpoint(request.query.get("id", "")).resolve()
        return web.json_response({"ok": True, "providers": list(CUSTOM_PROVIDERS),
                                  "provider": entry.get("provider"), "base_url": shown,
                                  "key_set": bool(entry.get("api_key")), "location": info.location()})

    @routes.post("/mnemic/llm/custom")
    async def llm_custom_save(request):
        try:
            data = await request.json()
            api_key = data.get("api_key")
            custom_id = await asyncio.to_thread(
                save_custom, data.get("id", ""), str(data.get("provider", "")), str(data.get("base_url", "")),
                None if api_key is None else str(api_key))
        except (ValueError, TypeError, AttributeError) as e:
            return web.json_response({"ok": False, "error": str(e) or "invalid request"}, status=400)
        return web.json_response({"ok": True, "id": custom_id})

    @routes.get("/mnemic/llm/models")
    async def llm_models(request):
        name = request.query.get("endpoint", "")
        if name == CUSTOM_ENDPOINT_NAME:
            endpoint = custom_endpoint(request.query.get("custom", ""))
            if endpoint is None:
                return web.json_response({"ok": False, "error": "The custom endpoint isn't saved yet.", "models": []})
        else:
            endpoint = load_endpoints().get(name)
        if endpoint is None:
            return web.json_response({"ok": False, "error": f"Unknown endpoint '{name}'."}, status=404)
        resolved = endpoint.resolve()
        if not resolved.ok:
            return web.json_response({"ok": False, "error": " ".join(resolved.problems), "models": _configured(endpoint)})

        started = time.monotonic()
        try:
            models = await asyncio.to_thread(list_models, resolved)
        except LLMError as e:
            return web.json_response({"ok": False, "error": str(e), "models": _configured(endpoint),
                                      "ms": int((time.monotonic() - started) * 1000)})
        known = {m["id"] for m in models}
        models += [m for m in _configured(endpoint) if m["id"] not in known]
        return web.json_response({"ok": True, "models": models, "ms": int((time.monotonic() - started) * 1000)})

    @routes.get("/mnemic/llm/presets")
    async def llm_presets(request):
        return web.json_response({"presets": await asyncio.to_thread(load_llm_presets)})

    _registered = True


def _configured(endpoint):
    """Models listed in the endpoint's config, for when the server can't be asked."""
    ids = list(endpoint.models)
    if endpoint.default_model and endpoint.default_model not in ids:
        ids.insert(0, endpoint.default_model)
    return [{"id": m, "detail": "from config"} for m in ids]
