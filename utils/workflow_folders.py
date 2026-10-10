"""Directory operations for the native workflow sidebar enhancement.

All paths are relative to the requesting user's workflows directory. Workflows
keep their normal ComfyUI file format and storage location.
"""

import asyncio
import errno
import ipaddress
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_registered = False
_locks = {}
_INVALID_NAME = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_RESERVED_NAME = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def _relative_path(value, allow_root=False):
    if not isinstance(value, str):
        raise ValueError("A folder path must be text.")
    if value == "" and allow_root:
        return ""
    parts = value.split("/")
    if any(not part or part in (".", "..") or part.endswith((" ", "."))
           or _INVALID_NAME.search(part) or _RESERVED_NAME.match(part) for part in parts):
        raise ValueError("Use a relative path with valid folder names, separated by /.")
    return value


def _resolve(root, relative, allow_root=False):
    relative = _relative_path(relative, allow_root)
    target = root.joinpath(*relative.split("/")) if relative else root
    # The user configures links/junctions inside workflows to expose storage on
    # other drives. Keep operations in that logical namespace, but let existing
    # links resolve to their real targets. The API accepts no absolute paths or
    # traversal components, and cannot create/change a link target.
    if os.path.commonpath((str(root.absolute()), str(target.absolute()))) != str(root.absolute()):
        raise ValueError("The path must stay inside the workflows folder.")
    return target


def _list_folders(root):
    _resolve(root, "", allow_root=True)
    result = {"folders": [], "folder_paths": {"": str(root.resolve())}}
    if not root.exists():
        return result
    if not root.is_dir():
        raise ValueError("The workflows path is not a directory.")
    # Follow configured directory links, keeping an ancestor set for each
    # branch so a link back to its parent cannot recurse indefinitely. Two
    # separate aliases of the same folder still get their own visible trees.
    pending = [(root, {os.path.normcase(str(root.resolve()))})]
    while pending:
        directory, ancestors = pending.pop()
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name.casefold())
        for entry in children:
            if not entry.is_dir(follow_symlinks=True):
                continue
            relative = (directory / entry.name).relative_to(root).as_posix()
            try:
                child = _resolve(root, relative)
                resolved = str(child.resolve())
            except (ValueError, RuntimeError):
                continue
            result["folders"].append(relative)
            result["folder_paths"][relative] = resolved
            identity = os.path.normcase(resolved)
            if identity not in ancestors:
                pending.append((child, ancestors | {identity}))
    result["folders"].sort(key=str.casefold)
    return result


def _create_folder(root, relative):
    target = _resolve(root, relative)
    _resolve(root, "", allow_root=True)
    root.mkdir(parents=True, exist_ok=True)
    if not target.parent.is_dir():
        raise FileNotFoundError("The parent folder no longer exists. Refresh and try again.")
    target.mkdir()  # Existing files/folders are a conflict, never reused silently.


def _move(root, source, destination):
    src = _resolve(root, source)
    dst = _resolve(root, destination)
    if not src.exists():
        raise FileNotFoundError("The source no longer exists. Refresh and try again.")
    if source == destination:
        return
    if src.is_dir() and dst.resolve().is_relative_to(src.resolve()):
        raise ValueError("A folder cannot be moved inside itself.")
    if os.path.lexists(dst):
        raise FileExistsError("A workflow or folder with that name already exists.")
    if not dst.parent.is_dir():
        raise FileNotFoundError("The destination folder no longer exists.")
    # Renaming a linked folder moves the link itself. Operations on its children
    # use the real target; a move between the local root and a linked drive may
    # need shutil's copy/remove fallback instead of a same-volume rename.
    try:
        os.rename(src, dst)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        if hasattr(src, "is_junction") and src.is_junction():
            raise ValueError("Move a junction's contents between drives; the junction itself can only be moved on its own drive.") from error
        shutil.move(str(src), str(dst))


def _local_request(request):
    try:
        return ipaddress.ip_address(request.remote or "").is_loopback
    except ValueError:
        return False


def _open_folder(root, relative):
    target = _resolve(root, relative, allow_root=True)
    if not relative:
        root.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise FileNotFoundError("The folder no longer exists.")
    target = target.resolve()
    if sys.platform == "win32":
        os.startfile(str(target))
    else:
        command = "open" if sys.platform == "darwin" else "xdg-open"
        # No shell, no arguments supplied by the browser, and no terminal window.
        subprocess.Popen([command, str(target)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


def register_workflow_folder_routes():
    global _registered
    if _registered:
        return
    from aiohttp import web
    from server import PromptServer

    server = PromptServer.instance

    def root_for(request):
        user_root = server.user_manager.get_request_user_filepath(request, None, create_dir=False)
        if user_root is None:
            raise ValueError("The user directory is unavailable.")
        return Path(user_root).absolute() / "workflows"

    def error_response(error):
        status = (403 if isinstance(error, KeyError) else 409 if isinstance(error, FileExistsError)
                  else 404 if isinstance(error, FileNotFoundError) else 400)
        return web.json_response({"error": str(error)}, status=status)

    @server.routes.get("/mnemic/workflows/folders")
    async def get_folders(request):
        try:
            root = root_for(request)
            listing = await asyncio.to_thread(_list_folders, root)
            return web.json_response({"path": str(root.resolve()), **listing,
                                      "can_open": _local_request(request)})
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            return error_response(error)

    @server.routes.post("/mnemic/workflows/folders/{action}")
    async def folder_action(request):
        try:
            root = root_for(request)
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Expected a folder operation.")
            action = request.match_info["action"]
            # Serialize operations for a user root, including filesystem work
            # dispatched to a worker thread.
            lock = _locks.setdefault(str(root), asyncio.Lock())
            async with lock:
                if action == "create":
                    await asyncio.to_thread(_create_folder, root, body.get("path"))
                elif action == "move":
                    await asyncio.to_thread(_move, root, body.get("source"), body.get("destination"))
                elif action == "open":
                    if not _local_request(request):
                        return web.json_response({"error": "Open folder is available on the ComfyUI machine. Use Copy path for remote access."}, status=403)
                    await asyncio.to_thread(_open_folder, root, body.get("path", ""))
                else:
                    raise ValueError("Unknown folder operation.")
            return web.json_response({"ok": True})
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            return error_response(error)

    _registered = True
