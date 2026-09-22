# 📝 Wildcard Processor Advanced

The same wildcard engine as **📝 Wildcard Processor**, with control over the
multi-pick separator and extra outputs for the seed and for extracted tags.
See that node's help page for the full syntax reference.

## Inputs

- **wildcard_string** — The template to resolve.
- **seed** — Same seed plus same template always gives the same result.
- **multiple_separator** — What joins the picks when a block selects more than
  one item, e.g. `{2$$red|green|blue}`. A per-block separator written into the
  template overrides this.
- **recache_wildcards** — Re-scan the wildcard folders from disk. Turn it on
  once after adding or editing files, then turn it back off.

## Outputs

- **processed_text** — The resolved prompt.
- **seed** — The seed that produced it, handy for feeding a sampler so the
  image and the prompt share one seed.
- **extracted_tags_string** — Resolved tag content, joined with `|`.
- **extracted_tags_list** — The same content as a list, one entry per tag.
- **raw_tags_string** — The tags as they were written, delimiters included.
- **raw_tags_list** — The same, as a list.

## Notes

Tag extraction is currently inactive in the UI (the delimiter input is
disabled), so the four tag outputs are empty in normal use. They stay on the
node so existing workflows keep their wiring.

## Examples

```
multiple_separator: ", "
wildcard_string:    {2$$red|green|blue}

processed_text: "red, blue"
```
