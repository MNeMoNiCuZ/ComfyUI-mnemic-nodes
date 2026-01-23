# 🎲 Random Seed

Generates a random seed value for use with other nodes.

-   **Description**: Generates a random 64-bit integer seed value. Regenerates on each execution. Useful for feeding into other nodes that accept seed inputs for controlled randomness.
-   **Inputs**: None
-   **Outputs**:
    -   `seed`: A random integer between 0 and 2^64-1.

**Use Case**: Connect the output to seeds of other random nodes to get different results each run while maintaining reproducibility within a single execution.
