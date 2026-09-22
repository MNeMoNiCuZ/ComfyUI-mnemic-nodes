# 🎲 Random Bool

Rolls True or False, with an adjustable bias.

## Inputs

- **true_probability** — Chance of True. `0.0` is always False, `1.0` is always
  True, `0.5` is a coin flip.
- **seed** *(optional)* — `-1` rolls freshly every run. Any other value makes
  the result repeatable.

## Outputs

- **random_bool** — The rolled value.

## Examples

```
true_probability: 0.25   ->  True roughly one run in four
true_probability: 1.0    ->  always True
seed: 12345              ->  same answer every time
```
