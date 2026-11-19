from datetime import datetime
import time

from comfy_api.latest import io
from comfy_execution.utils import get_executing_context

from ..utils.date_templates import format_date_time
from ..utils.settings_utils import is_format_date_time_locale_respected

# (prompt id, time) shared by every Format Date Time node with sync_time on in that run.
_SYNCED_TIME = (None, None)


class FormatDateTime(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_FormatDateTime",
            display_name="📅 Format Date Time",
            category="⚡ MNeMiC Nodes",
            description="Formats the current date and time into a string based on a specified format.",
            inputs=[
                io.String.Input(
                    "date_format",
                    default="%Y-%m-%d/%Y-%m-%d - %H.%M.%S",
                    multiline=True,
                    tooltip="Formats a date string using Python's strftime directives.\n\n"
                            "%Y: Year (e.g., 2025)\n"
                            "%m: Month (01-12)\n"
                            "%d: Day of month (01-31)\n"
                            "%H: Hour (24-hour clock) (00-23)\n"
                            "%S: Second (00-59)\n"
                            "%f: Microsecond (000000-999999)\n"
                            "%x: Date representation\n"
                            "%X: Time (. to separate instead of :)\n"
                            "%c: Date and time representation\n"
                            "%p: AM/PM\n"
                            "%A: Weekday full name (e.g., Thursday)\n"
                            "%a: Weekday abbreviated name (e.g., Thu)\n"
                            "%B: Month full name (e.g., August)\n"
                            "%b: Month abbreviated name (e.g., Aug)\n"
                            "%j: Day of year (001-366)\n"
                            "%W: Week number of year (Monday as first day) (00-53)\n"
                            "%w: Day index of week (Monday is 0) (0-6)\n"
                            "%U: Week number of year (Sunday as first day) (00-53)\n"
                            "%u: Day index of week (Sunday is 0) (0-6)\n"
                            "%%: A literal '%' character",
                ),
                io.Boolean.Input(
                    "sync_time",
                    default=False,
                    tooltip="Use one shared time for every Format Date Time node with this on, so their outputs match across the whole run instead of differing by when each node runs.",
                ),
            ],
            outputs=[
                io.String.Output(display_name="formatted_date_time", tooltip="The current date and time rendered with the format above."),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return time.time()

    @classmethod
    def execute(cls, date_format, sync_time=False) -> io.NodeOutput:
        global _SYNCED_TIME
        now = datetime.now()
        if sync_time:
            context = get_executing_context()
            prompt_id = context.prompt_id if context else None
            if prompt_id is None or _SYNCED_TIME[0] != prompt_id:
                _SYNCED_TIME = (prompt_id, now)
            now = _SYNCED_TIME[1]
        return io.NodeOutput(format_date_time(date_format, now, is_format_date_time_locale_respected()))
