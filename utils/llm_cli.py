"""Local subscription CLIs as LLM endpoints: Claude Code and Codex.

Both run the CLI installed on this machine in non-interactive mode, signed in
with your own subscription, so no API key is involved:

- Claude Code: `claude -p` with stream-json input/output. All tools are
  disabled (`--tools ""`), MCP servers aren't loaded and nothing is saved as
  a session, so it answers as a plain model.
- Codex: `codex exec --json`. Its tool features (shell, browser, computer
  use, apps…) are disabled where this Codex version has them, and it runs in
  a read-only sandbox in an empty temporary folder.

API-key variables (ANTHROPIC_API_KEY, OPENAI_API_KEY…) are removed from the
CLI's environment so the subscription login is what gets used.
"""

import base64
import json
import re
import os
import contextlib
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from .env_manager import redact

CLAUDE = "claude_cli"
CODEX = "codex_cli"
CLI_PROVIDERS = (CLAUDE, CODEX)

# Only as a fallback when nothing else is given; Claude Code's own default
# system prompt is a coding agent's.
DEFAULT_SYSTEM = "You are a helpful assistant."

_STRIP_ENV = {
    CLAUDE: ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
    CODEX: ("OPENAI_API_KEY", "CODEX_API_KEY"),
}
_CODEX_TOOL_FEATURES = (
    "shell_tool", "unified_exec", "browser_use", "browser_use_external", "in_app_browser",
    "computer_use", "apps", "image_generation", "plugins", "remote_plugin", "tool_suggest",
    "standalone_web_search", "web_search_request", "web_search_cached",
)
# Model names go on the command line. On Windows an npm-installed CLI is a
# .cmd script run through cmd.exe, which Python can't quote safely, so a
# model name from a (possibly shared) workflow is restricted to plain
# characters.
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@\[\]-]{0,127}$")
_CODEX_SHELL_FEATURES = {"shell_tool", "unified_exec"}
_EFFORT = {"minimal": "low", "none": "low", "low": "low", "medium": "medium", "high": "high"}
_codex_features_cache = {}


class CLIError(Exception):
    def __init__(self, message, status="cli error"):
        super().__init__(redact(str(message)))
        self.status = status


def find_command(command):
    """Full path of the CLI, or None if it isn't installed."""
    if not command:
        return None
    if os.path.isfile(command):
        return command
    return shutil.which(command)


def _env(provider):
    env = dict(os.environ)
    for name in _STRIP_ENV[provider]:
        env.pop(name, None)
    return env


def _popen(args, provider, cwd):
    # Its own process group: npm installs are wrappers (node, or a .cmd on
    # Windows) around the real binary, and stopping only the wrapper would
    # leave the model call running.
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=cwd, env=_env(provider), **kwargs,
    )


def _terminate(proc):
    """Stop the CLI and everything it started."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            os.killpg(proc.pid, signal.SIGTERM)  # the node wrapper forwards it
            try:
                proc.wait(timeout=3)
                return
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        proc.kill()
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)


@contextlib.contextmanager
def _work_dir():
    """A temporary folder that is removed afterwards even if a stopped CLI
    still had it open (Windows refuses to delete it then)."""
    path = tempfile.mkdtemp(prefix="mnemic_llm_")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _read_lines(stream, out):
    for raw in iter(stream.readline, b""):
        out.put(raw)
    out.put(None)


def _run(args, provider, cwd, stdin_bytes, on_line, timeout, check_interrupt):
    """Run the CLI, feeding stdin and passing each stdout line to on_line.

    Returns (exit_code, stderr_text). Kills the process on timeout or
    interrupt.
    """
    proc = _popen(args, provider, cwd)
    lines = queue.Queue()
    stderr_chunks = []
    threading.Thread(target=_read_lines, args=(proc.stdout, lines), daemon=True).start()
    threading.Thread(target=lambda: stderr_chunks.append(proc.stderr.read()), daemon=True).start()
    try:
        proc.stdin.write(stdin_bytes)
        proc.stdin.close()
    except OSError:
        pass

    deadline = time.monotonic() + timeout
    try:
        while True:
            if check_interrupt:
                check_interrupt()
            if time.monotonic() > deadline:
                raise CLIError(f"no reply within {timeout} s", status="timeout")
            try:
                raw = lines.get(timeout=0.25)
            except queue.Empty:
                continue
            if raw is None:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                on_line(line)
        proc.wait(timeout=10)
    except BaseException:
        _terminate(proc)
        raise
    stderr = b"".join(c for c in stderr_chunks if c).decode("utf-8", errors="replace")
    return proc.returncode, stderr


def _last_line(text):
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return lines[-1][:500] if lines else ""


# --------------------------------------------------------------------------
# Claude Code
# --------------------------------------------------------------------------

def _claude_content(req, encoded_images):
    content = [{"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}
               for mime, data in encoded_images]
    if req.user:
        content.append({"type": "text", "text": req.user})
    return content


def run_claude(command, req, result, *, encoded_images, system, timeout, on_delta, check_interrupt, log):
    with _work_dir() as work:
        system_file = os.path.join(work, "system.txt")
        with open(system_file, "w", encoding="utf-8") as f:
            f.write(system or DEFAULT_SYSTEM)
        args = [command, "-p", "--input-format", "stream-json", "--output-format", "stream-json",
                "--verbose", "--include-partial-messages", "--tools", "", "--strict-mcp-config",
                "--no-session-persistence", "--system-prompt-file", system_file]
        if req.model:
            args += ["--model", req.model]
        if req.reasoning in _EFFORT:
            args += ["--effort", _EFFORT[req.reasoning]]
        message = {"type": "user", "message": {"role": "user", "content": _claude_content(req, encoded_images)}}
        if log:
            shown = " ".join(a if a else '""' for a in args[1:])
            log(f"Claude Code CLI: {shown}")

        text, thinking = [], []
        final = {}
        last_push = [0.0]

        def on_line(line):
            try:
                event = json.loads(line)
            except ValueError:
                return
            kind = event.get("type")
            if kind == "stream_event":
                inner = event.get("event") or {}
                if inner.get("type") == "content_block_delta":
                    delta = inner.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text.append(delta.get("text", ""))
                    elif delta.get("type") == "thinking_delta":
                        thinking.append(delta.get("thinking", ""))
                    now = time.monotonic()
                    if on_delta and now - last_push[0] > 0.08:
                        last_push[0] = now
                        on_delta("".join(text), "".join(thinking))
                elif inner.get("type") == "message_start":
                    result.model = (inner.get("message") or {}).get("model", result.model)
            elif kind == "result":
                final.update(event)

        code, stderr = _run(args, CLAUDE, work, (json.dumps(message) + "\n").encode("utf-8"),
                            on_line, timeout, check_interrupt)

    if final.get("is_error") or final.get("subtype", "success") != "success" or (code and not final):
        detail = final.get("result") or _last_line(stderr) or f"exit code {code}"
        raise CLIError(f"Claude Code CLI: {detail}. If it asks you to log in, run `claude` once in a terminal.")
    result.text = final.get("result") if isinstance(final.get("result"), str) else "".join(text)
    result.thinking = "".join(thinking)
    result.finish_reason = final.get("stop_reason") or "end_turn"
    usage = final.get("usage") or {}
    result.input_tokens = usage.get("input_tokens")
    result.output_tokens = usage.get("output_tokens")
    return result


# --------------------------------------------------------------------------
# Codex
# --------------------------------------------------------------------------

def _codex_features(command, work):
    """Feature flags this Codex version knows (disabling an unknown one is a
    hard error). Only a successful probe is cached, per binary."""
    try:
        key = (command, os.path.getmtime(command))
    except OSError:
        key = (command, None)
    if key in _codex_features_cache:
        return _codex_features_cache[key]
    names = set()
    try:
        out = subprocess.run([command, "features", "list"], capture_output=True, cwd=work,
                             env=_env(CODEX), timeout=60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0)
        if out.returncode == 0:
            for line in out.stdout.decode("utf-8", errors="replace").splitlines():
                parts = line.split()
                if parts and parts[0].replace("_", "").replace(".", "").isalnum():
                    names.add(parts[0])
    except (OSError, subprocess.SubprocessError):
        pass
    # Fail closed: without the shell tools turned off, a prompt could make
    # Codex read files on this machine (.env, stored keys) into its reply.
    if not names & _CODEX_SHELL_FEATURES:
        raise CLIError("could not confirm that Codex's shell tools can be turned off "
                       "(`codex features list` failed or changed), so it was not run. Update Codex and try again.",
                       status="unsafe")
    _codex_features_cache[key] = names
    return names


def run_codex(command, req, result, *, encoded_images, system, timeout, on_delta, check_interrupt, log):
    with _work_dir() as work:
        last_message = os.path.join(work, "last_message.txt")
        args = [command, "exec", "--json", "--skip-git-repo-check", "--ephemeral",
                "--sandbox", "read-only", "-C", work, "-o", last_message]
        known = _codex_features(command, work)
        for feature in _CODEX_TOOL_FEATURES:
            if feature in known:
                args += ["--disable", feature]
        if req.model:
            args += ["-m", req.model]
        if req.reasoning in _EFFORT:
            args += ["-c", f'model_reasoning_effort="{_EFFORT[req.reasoning]}"']
        for i, (mime, data) in enumerate(encoded_images):
            path = os.path.join(work, f"image_{i}.jpg")
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            # --image=<file> takes exactly one value; "-i a b" would also
            # swallow the "-" prompt argument as an image.
            args.append(f"--image={path}")
        args.append("-")
        # Codex has no separate system prompt in exec mode.
        prompt = f"{system}\n\n---\n\n{req.user}" if system and req.user else (system or req.user)
        if log:
            log(f"Codex CLI: {' '.join(args[1:])}")

        text, thinking = [], []
        failure = []
        last_error = []

        def on_line(line):
            try:
                event = json.loads(line)
            except ValueError:
                return
            kind = event.get("type")
            item = event.get("item") or {}
            if kind == "item.completed":
                if item.get("type") == "agent_message" and item.get("text"):
                    text.append(item["text"])
                elif item.get("type") == "reasoning" and item.get("text"):
                    thinking.append(item["text"])
                if on_delta:
                    on_delta("\n\n".join(text), "\n\n".join(thinking))
            elif kind == "turn.completed":
                usage = event.get("usage") or {}
                result.input_tokens = usage.get("input_tokens")
                result.output_tokens = usage.get("output_tokens")
            elif kind == "turn.failed":
                failure.append((event.get("error") or {}).get("message") or "turn failed")
            elif kind == "error":
                # Usually a transient "Reconnecting…" notice; kept in case
                # the run fails.
                last_error.append(str(event.get("message", "")))

        code, stderr = _run(args, CODEX, work, prompt.encode("utf-8"), on_line, timeout, check_interrupt)
        final_text = ""
        if os.path.exists(last_message):
            with open(last_message, "r", encoding="utf-8", errors="replace") as f:
                final_text = f.read().strip()

    if failure or code:
        detail = (failure or last_error or [_last_line(stderr) or f"exit code {code}"])[-1]
        raise CLIError(f"Codex CLI: {detail[:500]}. If it asks you to log in, run `codex login` in a terminal.")
    result.text = final_text or "\n\n".join(text)
    result.thinking = "\n\n".join(thinking)
    result.finish_reason = "stop"
    result.model = req.model or "codex default"
    return result


# --------------------------------------------------------------------------
# Entry points used by llm_providers
# --------------------------------------------------------------------------

def run_cli_chat(provider, command, req, result, **kwargs):
    if req.model and not _SAFE_MODEL.match(req.model):
        raise CLIError("invalid model name: use letters, digits and . _ - : / @ only", status="invalid model")
    runner = run_claude if provider == CLAUDE else run_codex
    try:
        return runner(command, req, result, **kwargs)
    except FileNotFoundError:
        raise CLIError("the CLI was not found; install it or set its path in .env", status="not installed") from None
    except OSError as e:
        raise CLIError(f"could not start the CLI ({type(e).__name__})", status="cli error") from None


CLAUDE_MODELS = [
    {"id": "sonnet", "detail": "latest Sonnet"},
    {"id": "opus", "detail": "latest Opus"},
    {"id": "haiku", "detail": "latest Haiku"},
    {"id": "fable", "detail": "latest Fable"},
]


def list_cli_models(provider):
    """The CLIs can't list models; these are the aliases they accept."""
    return list(CLAUDE_MODELS) if provider == CLAUDE else []
