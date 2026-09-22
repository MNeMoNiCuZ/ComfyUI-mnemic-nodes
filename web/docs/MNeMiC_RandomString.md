# 🎲 Random String

Picks one line at random from a list you type in.

## Inputs

- **input_list** — One option per line. Blank lines are ignored.
- **seed** *(optional)* — `-1` rolls freshly every run; any other value makes
  the pick repeatable.

## Outputs

- **random_choice** — The chosen line, or an empty string if the list had no
  usable lines.

## Examples

```
input_list:
    a photo of a cat
    a painting of a dog

    an ink sketch of a bird

Output: one of the three non-empty lines
```

For anything more involved — weights, nesting, multiple picks — use
📝 Wildcard Processor instead.
