# 🎲 Random String

Randomly selects one string from a newline-separated list of options.

-   **Description**: Choose randomly from a list of options. Each line in the input is one option. Empty lines are ignored.
-   **Inputs**:
    -   `input_list`: Newline-separated list of strings to choose from.
    -   `seed` (optional): Seed for random number generator. Use -1 for random results, or set a specific value for reproducibility.
-   **Outputs**:
    -   `random_choice`: The randomly selected string.

**Example Input**:
```
apple
banana
cherry
orange
```

One of these options will be randomly selected each time the node executes.
