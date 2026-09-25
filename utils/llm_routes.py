"""HTTP routes behind the Universal LLM node's UI (web/js/llm_api.js).

Endpoints are addressed by name only; the browser never sends a URL and never
receives a key or a header value. Model listing happens here, server-side,
because the key must not reach the browser.
"""

import asyncio
import time

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
        return web.json_response({"endpoints": endpoints})

    @routes.get("/mnemic/llm/models")
    async def llm_models(request):
        name = request.query.get("endpoint", "")
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
