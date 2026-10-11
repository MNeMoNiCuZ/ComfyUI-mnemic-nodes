"""Date templates shared by image download and image saving nodes."""

import re
from datetime import datetime


def _format_like_format_date_time(date_format: str, respect_system_locale: bool = False) -> str:
    now = datetime.now()
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


def resolve_date_template(text: str) -> str:
    pattern = re.compile(r"%date:([^%]+)%")
    if pattern.search(text):
        def repl(match):
            fmt = match.group(1)
            converted = (
                fmt.replace("yyyy", "%Y")
                .replace("MM", "%m")
                .replace("dd", "%d")
                .replace("hh", "%H")
                .replace("mm", "%M")
                .replace("ss", "%S")
            )
            return _format_like_format_date_time(converted)

        return pattern.sub(repl, text)
    return _format_like_format_date_time(text)
