# 🔄 Type Converter

This node is a versatile utility for converting a single input of any type to the fundamental data types within ComfyUI: `INT`, `FLOAT`, `STRING`, and `BOOLEAN`.

---

### Node Reference

![Image of Type Converter node](https://via.placeholder.com/800x200.png?text=Type+Converter+Node)

---

### Inputs and Outputs

-   `input` (required): A wildcard input that accepts any data type.
-   `INT_OUT`: The integer result of the conversion. If conversion is not possible, this is `None`.
-   `FLOAT_OUT`: The float result of the conversion. If conversion is not possible, this is `None`.
-   `STRING_OUT`: The string result of the conversion.
-   `BOOLEAN_OUT`: The boolean result of the conversion. If conversion is not possible, this is `None`.

### How it Works

The node takes a single input and attempts to convert it to each of the four output types.

### Conversion Rules

-   **To Integer (`INT`)**:
    -   `FLOAT`: Rounds to the nearest integer.
    -   `BOOLEAN`: `True` -> `1`, `False` -> `0`.
    -   `STRING`: Parses numbers and number words (e.g., "one").

-   **To Float (`FLOAT`)**:
    -   `INT`: Converts to a float.
    -   `BOOLEAN`: `True` -> `1.0`, `False` -> `0.0`.
    -   `STRING`: Parses the string as a float.

-   **To String (`STRING`)**:
    -   Any type is converted to its string representation.

-   **To Boolean (`BOOLEAN`)**:
    -   `INT` or `FLOAT`: `0` -> `False`, any other number -> `True`.
    -   `STRING`: "true", "yes", "1" -> `True`; "false", "no", "0" -> `False`.