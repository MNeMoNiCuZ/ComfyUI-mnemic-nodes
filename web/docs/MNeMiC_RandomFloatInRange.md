# 🎲 Random Float in Range

Rolls a decimal number between two bounds.

## Inputs

- **min_value** — Lowest number that can come out.
- **max_value** — Highest number that can come out.
- **decimals** *(optional)* — Round the result to this many decimal places.
  `-1` keeps full precision.
- **seed** *(optional)* — `-1` rolls freshly every run; any other value makes
  the result repeatable.

## Outputs

- **random_float** — The rolled number.

## Notes

If min is higher than max the two are swapped.
