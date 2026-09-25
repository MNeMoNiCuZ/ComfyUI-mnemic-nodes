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

from .env_manager import expand_vars, get_secret, register_secret

LLM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "nodes", "llm")
DEFAULT_ENDPOINTS_FILE = os.path.join(LLM_DIR, "DefaultEndpoints.json")
USER_ENDPOINTS_FILE = os.path.join(LLM_DIR, "UserEndpoints.json")
USER_ENDPOINTS_EXAMPLE = os.path.join(LLM_DIR, "UserEndpoints.example.json")

PROVIDERS = ("openai", "anthropic", "ollama", "claude_cli", "codex_cli")
CLI_PROVIDERS = ("claude_cli", "codex_cli")
CUSTOM_ENDPOINT_NAME = "Custom Endpoint - WARNING"


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
    command: str = ""               # CLI providers: executable name or path
    api_key: str = ""               # custom endpoints: the key itself
    private_address: bool = False   # custom endpoints: never show the address

    @property
    def is_cli(self):
        return self.provider in CLI_PROVIDERS

    @property
    def model_optional(self):
        """An empty model is sent as-is (the server or CLI picks its default)."""
        return self.is_cli or bool(self.options.get("model_optional"))

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
        if ep.is_cli:
            return cls._from_cli(ep)
        problems = []
        base_url, missing = expand_vars(ep.base_url)
        base_url = normalize_url(base_url)
        if missing or not base_url:
            names = ", ".join(missing) or "base_url"
            problems.append(f"No address configured: set {names} in the .env file.")
        suffix = str(ep.options.get("ensure_path", "") or "").rstrip("/")
        if base_url and suffix and not urlparse(base_url).path.rstrip("/").endswith(suffix):
            base_url += suffix

        api_key = ep.api_key or (get_secret(ep.api_key_env) if ep.api_key_env else None)
        if ep.api_key_env and not api_key and not ep.api_key_optional:
            problems.append(f"No API key: set {ep.api_key_env} in the .env file.")

        headers = {}
        for key, value in (ep.headers or {}).items():
            expanded, missing = expand_vars(str(value))
            if missing:
                problems.append(f"Header '{key}' needs {', '.join(missing)} in the .env file.")
            headers[key] = expanded
        # Whatever the source (.env, system environment, a URL), these must
        # never show up in outputs, errors or logs.
        register_secret(api_key, partial=True)
        for key, value in headers.items():
            if "${" in str((ep.headers or {}).get(key, "")):
                register_secret(value)
        if base_url:
            parsed = urlparse(base_url)
            register_secret(parsed.password)
            if ("${" in ep.base_url or ep.private_address) and classify_location(base_url) != "local":
                # A private address from .env: mask it even on its own, as
                # servers and proxies echo bare hostnames in errors.
                register_secret(parsed.hostname)
        return cls(ep, base_url, api_key or "", headers, problems)

    @classmethod
    def _from_cli(cls, ep):
        from .llm_cli import find_command
        command, _missing = expand_vars(ep.command)
        path = find_command(command.strip())
        problems = []
        if not path:
            var = ep.options.get("command_env", "")
            where = f", or set {var} in the .env file to its full path" if var else ""
            problems.append(f"The {command or 'CLI'} command was not found on this machine. "
                            f"Install it and sign in once in a terminal{where}.")
        # base_url holds the executable path; it is never shown or sent.
        return cls(ep, path or "", "", {}, problems)

    @property
    def ok(self):
        return not self.problems

    def location(self):
        if self.endpoint.is_cli:
            return "local"
        return classify_location(self.base_url)

    def display_host(self):
        """What the panel may show as the address.

        The real host for addresses written in the shipped/user JSON and for
        this machine. An address that comes from .env is private (a LAN IP, an
        internal hostname), so the browser only learns where it came from.
        """
        if self.endpoint.is_cli:
            # Never the path: it comes from .env and names a local folder.
            return {"claude_cli": "Claude Code CLI", "codex_cli": "Codex CLI"}[self.endpoint.provider] if self.base_url else ""
        if not self.base_url:
            return ""
        if self.endpoint.private_address and self.location() != "local":
            return "address stored on this machine"
        if "${" in self.endpoint.base_url and self.location() != "local":
            return "address set in .env"
        return _display_host(urlparse(self.base_url))

    def public_info(self):
        """What the browser is allowed to know: no key, no header values, no private address."""
        ep = self.endpoint
        return {
            "name": ep.name,
            "provider": ep.provider,
            "description": ep.description,
            "default_model": ep.default_model,
            "location": self.location(),
            "host": self.display_host(),
            "key_env": ep.api_key_env,
            "key_set": bool(self.api_key),
            "key_optional": ep.api_key_optional or not ep.api_key_env,
            "is_cli": ep.is_cli,
            "model_optional": ep.model_optional,
            "ok": self.ok,
            "problems": self.problems,
        }


def _display_host(parsed):
    """host[:port] without any user:password@ part of the URL."""
    if not parsed or not parsed.hostname:
        return ""
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    try:
        port = parsed.port
    except ValueError:
        port = None
    return f"{host}:{port}" if port else host


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
        command=str(entry.get("command", "") or ""),
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
        if name == CUSTOM_ENDPOINT_NAME:
            continue  # reserved; see llm_custom
        endpoint = _to_endpoint(entry)
        if endpoint is not None:
            merged.pop(name, None)  # re-insert so the user file's position wins
            merged[name] = endpoint
    # Entries marked pin_last go after everything else, in their own order.
    pinned = [n for n, ep in merged.items() if ep.options.get("pin_last")]
    return {**{n: ep for n, ep in merged.items() if n not in pinned}, **{n: merged[n] for n in pinned}}


def endpoint_names():
    """The node's dropdown: every configured endpoint, then the custom one."""
    return list(load_endpoints().keys()) + [CUSTOM_ENDPOINT_NAME]


def get_endpoint(name):
    endpoint = load_endpoints().get(name)
    if endpoint is None:
        raise KeyError(f"Endpoint '{name}' is not configured. Check nodes/llm/UserEndpoints.json.")
    return endpoint
