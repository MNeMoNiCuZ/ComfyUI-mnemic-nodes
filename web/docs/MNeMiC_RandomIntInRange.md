# 🎲 Random Int in Range

Rolls a whole number between two bounds, both included.

## Inputs

- **min_value** — Lowest number that can come out.
- **max_value** — Highest number that can come out.
- **seed** *(optional)* — `-1` rolls freshly every run; any other value makes
  the result repeatable.

## Outputs

- **random_int** — The rolled number.

## Notes

If min is higher than max the two are swapped, so the node never errors on a
reversed range.
