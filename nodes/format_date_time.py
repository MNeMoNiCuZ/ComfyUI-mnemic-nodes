from datetime import datetime
import re
import time

class FormatDateTime:
    def __init__(self):
        pass

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "date_format": ("STRING", {
                    "default": "%Y-%m-%d - %H.%M.%S",
                    "multiline": True,
                    "tooltip": "Formats a date string using Python's strftime directives.\n\n"
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
                               "%%: A literal '%' character"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("formatted_date_time",)
    OUTPUT_NODE = True
    FUNCTION = "format_date_time"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Formats the current date and time into a string based on a specified format."

    def format_date_time(self, date_format):
        """
        Formats the current date and time using the provided format string.
        The format string directly uses Python's strftime directives.
        Adjusts time separators for %X and %c to use '.' instead of ':'.
        Includes custom handling for %w (Monday is 0) and %u (Sunday is 0).
        """
        now = datetime.now()
        
        # Store original format to check for %X and %c later
        original_date_format = date_format
        
        # Step 1: Temporarily replace '%%' with a unique placeholder
        # This prevents '%%w' from becoming '%w' prematurely and being
        # caught by our custom %w/%u replacement logic.
        temp_format = date_format.replace('%%', '__DOUBLE_PERCENT_PLACEHOLDER__')

        # Step 2: Replace custom %w and %u directives with their calculated values
        # We use regex with a negative lookbehind to ensure we only replace
        # standalone %w and %u (i.e., not preceded by another '%').
        custom_w_value = str(now.weekday()) # Monday is 0
        custom_u_value = str(now.isoweekday() % 7) # Sunday is 0

        # Replace %w and %u with their custom values directly in temp_format
        temp_format = re.sub(r'(?<!%)%w', custom_w_value, temp_format)
        temp_format = re.sub(r'(?<!%)%u', custom_u_value, temp_format)

        # Step 3: Perform strftime on the modified format string.
        # strftime will process all standard directives and pass through
        # our '__DOUBLE_PERCENT_PLACEHOLDER__' as it's not a valid directive.
        formatted_string = now.strftime(temp_format)

        # Step 4: Restore '%%' from the placeholder. strftime converts '%%' to '%',
        # so we replace our placeholder with a single '%' to match strftime's behavior.
        formatted_string = formatted_string.replace('__DOUBLE_PERCENT_PLACEHOLDER__', '%')

        # Step 5: Custom replacement for %X and %c to use '.' instead of ':' for time separators
        # These replacements should happen after the main strftime call
        # and should target the actual formatted output of %X and %c.
        if '%X' in original_date_format:
            # Get the default strftime output for %X
            formatted_x_from_strftime = now.strftime("%X")
            # Replace colons with dots
            formatted_x_with_dots = formatted_x_from_strftime.replace(':', '.')
            # Replace the original %X output in the final string with the dot version
            formatted_string = formatted_string.replace(formatted_x_from_strftime, formatted_x_with_dots)

        if '%c' in original_date_format:
            # Get the default strftime output for %c
            formatted_c_from_strftime = now.strftime("%c")
            # Replace colons with dots
            formatted_c_with_dots = formatted_c_from_strftime.replace(':', '.')
            # Replace the original %c output in the final string with the dot version
            formatted_string = formatted_string.replace(formatted_c_from_strftime, formatted_c_with_dots)

        return (formatted_string,)
