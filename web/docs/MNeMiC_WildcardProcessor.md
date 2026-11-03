# 📝 Wildcard Processor

Resolves a prompt template with wildcards, choices, variables and if blocks
into one concrete prompt. The resolved text is shown on the node and sent to
the output. The **Feature Summary** below lists every syntax.

## Inputs

- **wildcard_string** — The template to resolve. Full syntax below.
- **seed** — Random selection seed. The same template, seed, settings, and
  wildcard file contents produce the same result.
- **recache_wildcards** — Re-scan the wildcard folders from disk. Turn it on
  once after adding or editing files, then turn it back off.

## Outputs

- **processed_text** — The resolved prompt.
