# 📝 Wildcard Processor

Resolves a prompt template into one concrete prompt: pulls random lines out of
wildcard files, picks between inline choices, applies weights, and expands
variables. The resolved text is shown on the node and sent to the output.

## Inputs

- **wildcard_string** — The template to resolve. Full syntax below.
- **seed** — Random selection seed. The same template, seed, settings, and
  wildcard file contents produce the same result.
- **recache_wildcards** — Re-scan the wildcard folders from disk. Turn it on
  once after adding or editing files, then turn it back off.

## Outputs

- **processed_text** — The resolved prompt.
