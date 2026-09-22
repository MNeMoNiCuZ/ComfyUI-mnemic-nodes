# 📝 Wildcard Processor

Resolves a prompt template into one concrete prompt: pulls random lines out of
wildcard files, picks between inline choices, applies weights, and expands
variables. The resolved text is shown on the node and sent to the output.

## Inputs

- **wildcard_string** — The template to resolve. Syntax below.
- **seed** — Same seed plus same template always gives the same result.
- **recache_wildcards** — Re-scan the wildcard folders from disk. Turn it on
  once after adding or editing files, then turn it back off.

## Outputs

- **text** — The resolved prompt.

## Syntax

**File wildcards** — `__filename__` inserts one random line from
`filename.txt` in a wildcard folder. Lines starting with `#` are comments.

```
A photo of a __color__ __animal__     ->  A photo of a red fox
```

**Inline choices** — `{a|b|c}` picks one option.

```
A {red|green|blue} car               ->  A green car
```

**Weighted choices** — `{5::black|green|red}` makes `black` five times as
likely as the unweighted options. Weights are normalised across the whole
block: `{5::red|4::green|7::blue|black}` sums to 17, giving red ~29%,
green ~24%, blue ~41%, black ~6%.

**Pick several** — `{2$$a|b|c|d}` picks exactly two. `{1-3$$...}` picks a
random count in that range.

```
My favourite colours are {3$$red|green|blue|yellow|purple}
->  My favourite colours are blue, yellow, purple
```

**Custom separator** — put it between the count and the options:
`{1-3$$, $$red|green|blue}` joins the picks with `", "`.

**Variables** — define once, reuse anywhere. The value can itself be a
wildcard.

```
${animal=!__animals__} The ${animal} is friends with the other ${animal}
->  The cat is friends with the other cat
```

Blocks can be nested; the node keeps resolving until nothing is left to expand,
up to the pass limit in **Settings → ⚡MNeMiC Nodes → Wildcard Processing**.

## Where wildcard files live

The node scans the pack's `wildcards/` folder plus any folders listed in its
user paths file, matching by filename with subfolder priority and optional
fuzzy word matching. Console logging, fuzzy search, the candidate-log cap and
the nested pass limit are all in **Settings → ⚡MNeMiC Nodes → Wildcard
Processing**.

## Related

- **📝 Wildcard Processor Advanced** — same engine, plus a separator setting and
  extra outputs.
- **🔀 Batch Wildcard Upscale Sampler** — resolves a fresh prompt per image and
  samples them in one node.
