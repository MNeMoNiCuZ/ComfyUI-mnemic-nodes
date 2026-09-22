# 🔗 String Concat / Append

Joins several strings into one, with an optional separator between them.
Input slots appear as you connect them: plug something into the last free
`string_N` slot and a new one is added below it.

## Inputs

- **delimiter** — Text inserted between the pieces. Leave empty to glue them
  together with nothing in between.
- **string_0**, **string_1**, … — The pieces, joined in slot order. Slots that
  are empty or unconnected are skipped, so gaps never produce double
  separators.

## Outputs

- **concatenated_string** — The joined text.

## Examples

```
delimiter: ", "
string_0:  a photo of a cat
string_1:  (blank)
string_2:  golden hour

Output: "a photo of a cat, golden hour"
```
