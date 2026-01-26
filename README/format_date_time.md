# 📅 Format Date Time
This node converts date and time formats into literal outputs for you to use.

`respect_system_locale` toggle functionality: This option allows you to choose between standard SI formats (when disabled) or system-specific locale formats (when enabled) for the `%x` and `%c` directives.
- **Disabled (Default):** `%x` forces `YYYY-MM-DD`, and `%c` forces `YYYY-MM-DD HH.MM.SS`. providing consistent results across different systems.
- **Enabled:** `%x` and `%c` use your operating system's locale settings, which may result in formats like `MM/DD/YY`.

<img width="1405" height="315" alt="image" src="https://github.com/user-attachments/assets/a54e2a4f-c81b-442c-8965-5eda2c835f17" />

<img width="1420" height="682" alt="image" src="https://github.com/user-attachments/assets/eaf18367-ccf2-4adb-a152-7e85c54118d3" />

```
%%Y = %Y = Year
%%m = %m = Month
%%d = %d = Day
%%H = %H = Hour
%%S = %S = Second
%%f = %f = Microsecond
%%x = %x = Date (Affected by respect_system_locale)
%%X = %X = Time
%%c = %c = Date + Time (Affected by respect_system_locale)
%%p = %p = am/pm
%%A = %A = Weekday
%%a = %a = Weekday short
%%B = %B = Month
%%b = %b = Month short
%%j = %j = Day of year
%%W = %W = Week index (Monday start)
%%w = %w = Weekday index (Monday start)
%%U = %U = Week index (Sunday start)
%%u = %u = Weekday index (Sunday start)
%%%% = %% = Prints a literal %%
```
