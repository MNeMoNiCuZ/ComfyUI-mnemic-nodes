"""Endpoint configuration for the Universal LLM node.

Endpoints come from two JSON files in `nodes/llm/`:

- `DefaultEndpoints.json` ships with the pack.
- `UserEndpoints.json` is yours: git-ignored, created from
  `UserEndpoints.example.json` on first run. Entries are merged by `name`.

A workflow only ever stores the endpoint's *name*. The URL, the key and any
extra headers are resolved here at run time, from the JSON and from `.env`, so
sharing a workflow or an image shares none of them.
"""

import ipaddress
import json
import os
import shutil
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .env_manager import expand_vars, get_secret

LLM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "nodes", "llm")
DEFAULT_ENDPOINTS_FILE = os.path.join(LLM_DIR, "DefaultEndpoints.json")
USER_ENDPOINTS_FILE = os.path.join(LLM_DIR, "UserEndpoints.json")
USER_ENDPOINTS_EXAMPLE = os.path.join(LLM_DIR, "UserEndpoints.example.json")

PROVIDERS = ("openai", "anthropic", "ollama")


@dataclass
class Endpoint:
    name: str
    provider: str
    base_url: str
    api_key_env: str = ""
    api_key_optional: bool = False
    default_model: str = ""
    models: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    extra_body: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    description: str = ""

    def resolve(self):
        return ResolvedEndpoint.from_endpoint(self)


@dataclass
class ResolvedEndpoint:
    """An endpoint with its URL, key and headers filled in from `.env`.

    Lives only in memory for the duration of a request. Never serialise it
    to the frontend: use public_info() for that.
    """
    endpoint: Endpoint
    base_url: str
    api_key: str
    headers: dict
    problems: list

    @classmethod
    def from_endpoint(cls, ep):
        problems = []
        base_url, missing = expand_vars(ep.base_url)
        base_url = normalize_url(base_url)
        if missing or not base_url:
            names = ", ".join(missing) or "base_url"
            problems.append(f"No address configured: set {names} in the .env file.")

        api_key = get_secret(ep.api_key_env) if ep.api_key_env else None
        if ep.api_key_env and not api_key and not ep.api_key_optional:
            problems.append(f"No API key: set {ep.api_key_env} in the .env file.")

        headers = {}
        for key, value in (ep.headers or {}).items():
            expanded, missing = expand_vars(str(value))
            if missing:
                problems.append(f"Header '{key}' needs {', '.join(missing)} in the .env file.")
            headers[key] = expanded
        return cls(ep, base_url, api_key or "", headers, problems)

    @property
    def ok(self):
        return not self.problems

    def location(self):
        return classify_location(self.base_url)

    def public_info(self):
        """What the browser is allowed to know. No key, no header values."""
        ep = self.endpoint
        parsed = urlparse(self.base_url) if self.base_url else None
        return {
            "name": ep.name,
            "provider": ep.provider,
            "description": ep.description,
            "default_model": ep.default_model,
            "location": self.location(),
            "host": parsed.netloc if parsed else "",
            "key_env": ep.api_key_env,
            "key_set": bool(self.api_key),
            "key_optional": ep.api_key_optional or not ep.api_key_env,
            "ok": self.ok,
            "problems": self.problems,
        }


def normalize_url(url):
    url = (url or "").strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


def classify_location(url):
    """'local' for this machine, 'network' for a private address, else 'cloud'."""
    host = (urlparse(url).hostname or "").lower() if url else ""
    if not host:
        return "unknown"
    if host in ("localhost", "host.docker.internal") or host.endswith(".localhost"):
        return "local"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host.endswith((".local", ".lan", ".home", ".internal")) or "." not in host:
            return "network"
        return "cloud"
    if ip.is_loopback or ip.is_unspecified:
        return "local"
    if ip.is_private or ip.is_link_local:
        return "network"
    return "cloud"


def ensure_user_endpoints_file():
    if not os.path.exists(USER_ENDPOINTS_FILE) and os.path.exists(USER_ENDPOINTS_EXAMPLE):
        try:
            shutil.copy(USER_ENDPOINTS_EXAMPLE, USER_ENDPOINTS_FILE)
        except OSError as e:
            print(f"[MNeMiC LLM] Could not create {USER_ENDPOINTS_FILE}: {e}")


def _read_entries(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"\033[91m[MNeMiC LLM] Could not read {os.path.basename(path)}: {e}\033[0m")
        return []
    entries = data.get("endpoints", []) if isinstance(data, dict) else data
    return [e for e in entries if isinstance(e, dict) and e.get("name")]


def _to_endpoint(entry):
    provider = str(entry.get("provider", "openai")).lower()
    if provider not in PROVIDERS:
        print(f"\033[91m[MNeMiC LLM] Endpoint '{entry['name']}' has unknown provider '{provider}'; "
              f"use one of {', '.join(PROVIDERS)}.\033[0m")
        return None
    return Endpoint(
        name=str(entry["name"]),
        provider=provider,
        base_url=str(entry.get("base_url", "")),
        api_key_env=str(entry.get("api_key_env", "") or ""),
        api_key_optional=bool(entry.get("api_key_optional", False)),
        default_model=str(entry.get("default_model", "") or ""),
        models=[str(m) for m in entry.get("models", []) or []],
        headers=dict(entry.get("headers", {}) or {}),
        extra_body=dict(entry.get("extra_body", {}) or {}),
        options=dict(entry.get("options", {}) or {}),
        description=str(entry.get("description", "") or ""),
    )


def load_endpoints():
    """Return {name: Endpoint}, built-ins first, user entries merged by name."""
    ensure_user_endpoints_file()
    merged = {}
    for entry in _read_entries(DEFAULT_ENDPOINTS_FILE) + _read_entries(USER_ENDPOINTS_FILE):
        name = str(entry["name"])
        if entry.get("enabled", True) is False:
            merged.pop(name, None)
            continue
        endpoint = _to_endpoint(entry)
        if endpoint is not None:
            merged[name] = endpoint
    return merged


def get_endpoint(name):
    endpoint = load_endpoints().get(name)
    if endpoint is None:
        raise KeyError(f"Endpoint '{name}' is not configured. Check nodes/llm/UserEndpoints.json.")
    return endpoint
