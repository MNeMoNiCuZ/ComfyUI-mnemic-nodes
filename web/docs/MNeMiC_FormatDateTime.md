# 📅 Format Date Time

Renders the current date and time as text, using Python's `strftime`
directives. Handy for filenames and folder names.

The node re-runs on every queue, so the timestamp is always current.

## Inputs

- **date_format** — The format string. Directives are listed below.
- **respect_system_locale** — When on, `%x` and `%c` follow your OS locale
  (which may be MM/DD/YY). When off, `%x` is forced to `YYYY-MM-DD` and `%c` to
  `YYYY-MM-DD HH.MM.SS`.

## Outputs

- **formatted_date_time** — The rendered text.

## Directives

```
%Y  Year (2025)              %A  Weekday name (Thursday)
%m  Month (01-12)            %a  Weekday short (Thu)
%d  Day of month (01-31)     %B  Month name (August)
%H  Hour, 24h (00-23)        %b  Month short (Aug)
%M  Minute (00-59)           %j  Day of year (001-366)
%S  Second (00-59)           %W  Week of year, Mon first (00-53)
%f  Microsecond              %U  Week of year, Sun first (00-53)
%p  AM/PM                    %w  Weekday index, Monday = 0
%x  Date                     %u  Weekday index, Sunday = 0
%X  Time (dots, not colons)  %%  A literal % sign
%c  Date and time
```

`%X` and `%c` use `.` instead of `:` so the result is safe in a filename.
`%w` and `%u` are handled by this node rather than by `strftime`, to give the
Monday-first and Sunday-first indexes shown above.

## Examples

```
%Y-%m-%d/%Y-%m-%d - %H.%M.%S   ->  2025-08-14/2025-08-14 - 17.42.09
%Y%m%d_%H%M%S                  ->  20250814_174209
100%% done                     ->  100% done
```
