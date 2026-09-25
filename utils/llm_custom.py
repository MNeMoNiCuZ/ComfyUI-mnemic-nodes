"""Runtime-configured ("Custom Endpoint - WARNING") endpoints.

The address and key typed into the node's custom-endpoint panel are stored
here, on this machine, in the git-ignored `nodes/llm/CustomEndpoints.local.json`.
The workflow only holds a random id pointing at the entry, so the address and
key never end up in a saved workflow or an image's metadata.
"""

import json
import os
import secrets
import threading

from .llm_endpoints import CUSTOM_ENDPOINT_NAME, LLM_DIR, Endpoint, normalize_url

CUSTOM_PROVIDERS = ("openai", "anthropic", "ollama")
STORE_FILE = os.path.join(LLM_DIR, "CustomEndpoints.local.json")

_lock = threading.Lock()


def _load():
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    tmp = STORE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, STORE_FILE)


def _valid_id(custom_id):
    return isinstance(custom_id, str) and 16 <= len(custom_id) <= 64 and custom_id.replace("-", "").replace("_", "").isalnum()


def save_custom(custom_id, provider, base_url, api_key):
    """Create or update an entry. api_key None keeps the stored key; "" clears it.

    Returns the entry's id.
    """
    if provider not in CUSTOM_PROVIDERS:
        raise ValueError(f"protocol must be one of {', '.join(CUSTOM_PROVIDERS)}")
    base_url = normalize_url(base_url)
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("the address must start with http:// or https://")
    with _lock:
        data = _load()
        if not _valid_id(custom_id) or custom_id not in data:
            custom_id = secrets.token_urlsafe(18)
            data[custom_id] = {}
        entry = data[custom_id]
        entry["provider"] = provider
        entry["base_url"] = base_url
        if api_key is not None:
            entry["api_key"] = api_key.strip()
        _save(data)
    return custom_id


def get_custom(custom_id):
    if not _valid_id(custom_id):
        return None
    with _lock:
        return _load().get(custom_id)


def custom_endpoint(custom_id):
    """An Endpoint for a stored entry, or None if the id is unknown here."""
    entry = get_custom(custom_id)
    if not entry:
        return None
    return Endpoint(
        name=CUSTOM_ENDPOINT_NAME,
        provider=entry.get("provider", "openai"),
        base_url=entry.get("base_url", ""),
        api_key=entry.get("api_key", ""),
        api_key_optional=True,
        # Treated like an address from .env: never shown back in full.
        private_address=True,
        description="Runtime-configured endpoint.",
    )
