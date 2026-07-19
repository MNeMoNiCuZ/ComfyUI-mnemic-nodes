import json
import os

import folder_paths

FUZZY_SEARCH_SETTING_ID = "MNeMiC.FuzzySearch"


def get_comfy_setting(setting_id, default=None):
    """Read a value from the (default) user's comfy.settings.json.

    ComfyUI's Settings panel stores values server-side per user. Node
    execution has no request/user context, so this looks at the "default"
    user, which is what a standard single-user install uses.
    """
    try:
        if hasattr(folder_paths, "get_public_user_directory"):
            user_dir = folder_paths.get_public_user_directory("default")
        else:
            user_dir = os.path.join(folder_paths.get_user_directory(), "default")
        settings_path = os.path.join(user_dir, "comfy.settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings.get(setting_id, default)
    except (OSError, ValueError, AttributeError):
        return default


def is_fuzzy_search_enabled():
    return bool(get_comfy_setting(FUZZY_SEARCH_SETTING_ID, False))
