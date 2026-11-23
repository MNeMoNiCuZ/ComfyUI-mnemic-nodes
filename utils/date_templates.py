"""Date templates shared by image download and image and video saving nodes."""

import re
from datetime import datetime


def format_date_time(date_format: str, now: datetime, respect_system_locale: bool = False) -> str:
    """Format Date Time's strftime rules: %w Monday = 0, %u Sunday = 0, dots instead of colons in %X and %c."""
    temp_format = date_format.replace("%%", "__DOUBLE_PERCENT_PLACEHOLDER__")
    if not respect_system_locale:
        temp_format = temp_format.replace("%x", "%Y-%m-%d")
        temp_format = temp_format.replace("%c", "%Y-%m-%d %H.%M.%S")
    temp_format = re.sub(r"(?<!%)%w", str(now.weekday()), temp_format)
    temp_format = re.sub(r"(?<!%)%u", str(now.isoweekday() % 7), temp_format)
    formatted_string = now.strftime(temp_format).replace("__DOUBLE_PERCENT_PLACEHOLDER__", "%")
    if "%X" in date_format:
        formatted_string = formatted_string.replace(now.strftime("%X"), now.strftime("%X").replace(":", "."))
    if "%c" in date_format:
        formatted_string = formatted_string.replace(now.strftime("%c"), now.strftime("%c").replace(":", "."))
    return formatted_string


def _date_token_to_strftime(fmt: str) -> str:
    return (
        fmt.replace("yyyy", "%Y")
        .replace("MM", "%m")
        .replace("dd", "%d")
        .replace("hh", "%H")
        .replace("mm", "%M")
        .replace("ss", "%S")
    )


def resolve_date_template(text: str) -> str:
    pattern = re.compile(r"%date:([^%]+)%")
    if pattern.search(text):
        def repl(match):
            return format_date_time(_date_token_to_strftime(match.group(1)), datetime.now())

        return pattern.sub(repl, text)
    return format_date_time(text, datetime.now())


# %date:...%, ComfyUI's own save path variables (kept for folder_paths), or one strftime code.
_FILENAME_TOKEN = re.compile(r"%date:([^%]+)%|(%(?:width|height|year|month|day|hour|minute|second)%)|%[aAbBcdfGHIjmMpSuUVwWxXyYzZ%]")


def resolve_filename_template(text: str) -> str:
    """Resolve strftime codes and %date:...% in a save prefix, leaving other % text untouched."""
    now = datetime.now()

    def repl(match):
        if match.group(1) is not None:
            return format_date_time(_date_token_to_strftime(match.group(1)), now)
        if match.group(2) is not None:
            return match.group(2)
        return format_date_time(match.group(0), now)

    return _FILENAME_TOKEN.sub(repl, text)
