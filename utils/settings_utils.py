import json
import os

import folder_paths

LORA_FUZZY_SEARCH_SETTING_ID = "MNeMiC.LoRALoading.FuzzySearch"
LORA_CONSOLE_LOG_SETTING_ID = "MNeMiC.LoRALoading.ConsoleLogging"
LORA_MAX_LOGGED_CANDIDATES_SETTING_ID = "MNeMiC.LoRALoading.MaxLoggedCandidates"

WILDCARD_FUZZY_SEARCH_SETTING_ID = "MNeMiC.WildcardProcessing.FuzzySearch"
WILDCARD_CONSOLE_LOG_SETTING_ID = "MNeMiC.WildcardProcessing.ConsoleLogging"
WILDCARD_MAX_LOGGED_CANDIDATES_SETTING_ID = "MNeMiC.WildcardProcessing.MaxLoggedCandidates"
WILDCARD_MAX_NESTED_PASSES_SETTING_ID = "MNeMiC.WildcardProcessing.MaxNestedPasses"

GROQ_LLM_CONSOLE_LOG_SETTING_ID = "MNeMiC.GroqLLM.ConsoleLogging"
GROQ_LLM_TIMEOUT_SETTING_ID = "MNeMiC.GroqLLM.RequestTimeout"
GROQ_COMPLETION_CONSOLE_LOG_SETTING_ID = "MNeMiC.GroqCompletion.ConsoleLogging"
GROQ_COMPLETION_TIMEOUT_SETTING_ID = "MNeMiC.GroqCompletion.RequestTimeout"
GROQ_TRANSCRIBE_CONSOLE_LOG_SETTING_ID = "MNeMiC.GroqTranscribe.ConsoleLogging"
GROQ_TRANSCRIBE_TIMEOUT_SETTING_ID = "MNeMiC.GroqTranscribe.RequestTimeout"
GROQ_TRANSLATE_CONSOLE_LOG_SETTING_ID = "MNeMiC.GroqTranslate.ConsoleLogging"
GROQ_TRANSLATE_TIMEOUT_SETTING_ID = "MNeMiC.GroqTranslate.RequestTimeout"

DEFAULT_MAX_LOGGED_CANDIDATES = 15
DEFAULT_MAX_NESTED_PASSES = 10
DEFAULT_GROQ_REQUEST_TIMEOUT = 120

PROMPT_PROPERTY_EXTRACTOR_CONSOLE_LOG_SETTING_ID = "MNeMiC.PromptPropertyExtractor.ConsoleLogging"

LOAD_RANDOM_CHECKPOINT_CONSOLE_LOG_SETTING_ID = "MNeMiC.LoadRandomCheckpoint.ConsoleLogging"

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


def get_comfy_int_setting(setting_id, default):
    try:
        return int(get_comfy_setting(setting_id, default))
    except (TypeError, ValueError):
        return default


def is_lora_fuzzy_search_enabled():
    return bool(get_comfy_setting(LORA_FUZZY_SEARCH_SETTING_ID, False))


def is_lora_console_log_enabled():
    return bool(get_comfy_setting(LORA_CONSOLE_LOG_SETTING_ID, False))


def is_wildcard_fuzzy_search_enabled():
    return bool(get_comfy_setting(WILDCARD_FUZZY_SEARCH_SETTING_ID, False))


def is_wildcard_console_log_enabled():
    return bool(get_comfy_setting(WILDCARD_CONSOLE_LOG_SETTING_ID, False))


def get_lora_max_logged_candidates():
    return get_comfy_int_setting(LORA_MAX_LOGGED_CANDIDATES_SETTING_ID, DEFAULT_MAX_LOGGED_CANDIDATES)


def get_wildcard_max_logged_candidates():
    return get_comfy_int_setting(WILDCARD_MAX_LOGGED_CANDIDATES_SETTING_ID, DEFAULT_MAX_LOGGED_CANDIDATES)


def get_wildcard_max_nested_passes():
    return get_comfy_int_setting(WILDCARD_MAX_NESTED_PASSES_SETTING_ID, DEFAULT_MAX_NESTED_PASSES)


def is_groq_llm_console_log_enabled():
    return bool(get_comfy_setting(GROQ_LLM_CONSOLE_LOG_SETTING_ID, False))


def get_groq_llm_request_timeout():
    return get_comfy_int_setting(GROQ_LLM_TIMEOUT_SETTING_ID, DEFAULT_GROQ_REQUEST_TIMEOUT)


def is_groq_completion_console_log_enabled():
    return bool(get_comfy_setting(GROQ_COMPLETION_CONSOLE_LOG_SETTING_ID, False))


def get_groq_completion_request_timeout():
    return get_comfy_int_setting(GROQ_COMPLETION_TIMEOUT_SETTING_ID, DEFAULT_GROQ_REQUEST_TIMEOUT)


def is_groq_transcribe_console_log_enabled():
    return bool(get_comfy_setting(GROQ_TRANSCRIBE_CONSOLE_LOG_SETTING_ID, False))


def get_groq_transcribe_request_timeout():
    return get_comfy_int_setting(GROQ_TRANSCRIBE_TIMEOUT_SETTING_ID, DEFAULT_GROQ_REQUEST_TIMEOUT)


def is_groq_translate_console_log_enabled():
    return bool(get_comfy_setting(GROQ_TRANSLATE_CONSOLE_LOG_SETTING_ID, False))


def get_groq_translate_request_timeout():
    return get_comfy_int_setting(GROQ_TRANSLATE_TIMEOUT_SETTING_ID, DEFAULT_GROQ_REQUEST_TIMEOUT)


def is_prompt_property_extractor_console_log_enabled():
    return bool(get_comfy_setting(PROMPT_PROPERTY_EXTRACTOR_CONSOLE_LOG_SETTING_ID, False))


def is_load_random_checkpoint_console_log_enabled():
    return bool(get_comfy_setting(LOAD_RANDOM_CHECKPOINT_CONSOLE_LOG_SETTING_ID, False))
