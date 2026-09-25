"""Secrets for the pack: API keys and private addresses live in `.env`.

`.env` sits in the pack root, is git-ignored, and is the only place a key is
ever read from (besides variables already set in the process environment,
which win, so Docker / system-level setups keep working). Nothing read here
is ever written into a node widget, so it never ends up in a saved workflow
or in the metadata of a generated image.

The file is re-read whenever it changes on disk, so editing a key does not
need a ComfyUI restart.
"""

import os
import re
import shutil
from pathlib import Path

from dotenv import dotenv_values

_ENV_CACHE = {"mtime": None, "values": {}}

# ${VAR} or ${VAR:-fallback}
_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

# Values that mean "not filled in yet": template placeholders, and a bare
# comment (python-dotenv reads `KEY=   # note` as the value "# note").
_PLACEHOLDER_PATTERN = re.compile(r"^(your_.*|.*x{8,}.*|changeme|#.*|)$", re.IGNORECASE)


def get_project_root():
    """Get the absolute path to the project root directory."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent


def get_env_path():
    return get_project_root() / ".env"


def ensure_env_file():
    """Ensure .env file exists, create from template if it doesn't."""
    root_dir = get_project_root()
    env_file = root_dir / '.env'
    env_example = root_dir / '.env.example'

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("Created new .env file from template. Please edit it with your API key.")


def _load_env_file():
    """Return the parsed .env, re-reading it only when it has changed."""
    path = get_env_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _ENV_CACHE.update(mtime=None, values={})
        return {}
    if _ENV_CACHE["mtime"] != mtime:
        values = {k: v for k, v in dotenv_values(path).items() if v is not None}
        _ENV_CACHE.update(mtime=mtime, values=values)
    return _ENV_CACHE["values"]


def is_placeholder(value):
    return value is None or bool(_PLACEHOLDER_PATTERN.match(value.strip()))


def get_secret(name, default=None):
    """Look up a value by name: process environment first, then .env.

    Template placeholders (`gsk_xxxx…`, `your_api_key_here`) count as unset.
    """
    if not name:
        return default
    value = os.environ.get(name)
    if value is None:
        value = _load_env_file().get(name)
    if value is None or is_placeholder(value):
        return default
    return value.strip()


def expand_vars(text):
    """Expand `${VAR}` and `${VAR:-fallback}` using get_secret().

    Returns (expanded_text, missing_var_names). A variable that is unset and
    has no fallback expands to an empty string and is reported as missing.
    """
    if not isinstance(text, str):
        return text, []
    missing = []

    def _sub(match):
        name, fallback = match.group(1), match.group(2)
        value = get_secret(name)
        if value is None:
            if fallback is None:
                missing.append(name)
                return ""
            return fallback
        return value

    return _VAR_PATTERN.sub(_sub, text), missing


def _secret_values():
    """Every value from .env that is long enough to be worth scrubbing."""
    values = set(_load_env_file().values())
    return sorted((v.strip() for v in values if v and len(v.strip()) >= 8 and not is_placeholder(v)), key=len, reverse=True)


def redact(text, extra=()):
    """Replace every known secret in `text` with a masked form.

    Used on anything that leaves the backend: node outputs, status strings,
    console logs and API route responses. Error bodies from some providers
    echo part of the key back, and this keeps that out of workflows too.
    """
    if not text or not isinstance(text, str):
        return text
    for secret in list(extra) + _secret_values():
        if secret and len(secret) >= 8 and secret in text:
            text = text.replace(secret, mask(secret))
    return text


def mask(secret):
    if not secret:
        return ""
    if len(secret) <= 10:
        return "•" * 6
    return f"{secret[:4]}…{secret[-2:]}"


def get_api_key():
    """Get the Groq API key from environment variables."""
    api_key = get_secret('GROQ_API_KEY')
    if not api_key:
        raise ValueError("Please set your GROQ_API_KEY in the .env file")
    return api_key
