# 🔗 String Concat / Append

Concatenates multiple strings together with dynamic input expansion.

<img width="1983" height="593" alt="image" src="https://github.com/user-attachments/assets/cd50a487-428d-4c24-9603-7a9e2221cc1c" />

-   **Description**: Combines multiple strings into one. Features dynamic inputs - new input slots automatically appear as you connect strings, and unused slots are removed when disconnected.
-   **Inputs**:
    -   `delimiter` (optional): Separator to insert between concatenated strings (e.g., `, ` or ` | `). Leave empty for direct concatenation.
    -   `string_0`, `string_1`, ...: String inputs. More inputs appear automatically as you connect strings.
-   **Outputs**:
    -   `concatenated_string`: All connected strings joined together.

**Features**:
- **Dynamic Inputs**: The node starts with 2 string inputs. When you connect the last available input, a new empty input automatically appears. Unused inputs at the end are removed when you disconnect.
- **Empty Handling**: Empty inputs are automatically skipped during concatenation.
- **Delimiter Support**: Add any separator between strings, or leave empty for direct concatenation.

**Example**:
- Inputs: `"Hello"`, `"World"`, `"!"` with delimiter ` `
- Output: `"Hello World !"`
