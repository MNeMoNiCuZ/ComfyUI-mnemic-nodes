# 🎲 Random Float in Range

Generates a random floating-point number within a specified range.

-   **Description**: Generates a random float between min and max values. Supports optional decimal rounding and seed for reproducibility.
-   **Inputs**:
    -   `min_value`: Minimum value for the random float (inclusive).
    -   `max_value`: Maximum value for the random float (inclusive).
    -   `decimals` (optional): Number of decimal places to round to. Use -1 for full precision.
    -   `seed` (optional): Seed for random number generator. Use -1 for random results, or set a specific value for reproducibility.
-   **Outputs**:
    -   `random_float`: The generated random floating-point number.

**Note**: If min_value is greater than max_value, they are automatically swapped.
