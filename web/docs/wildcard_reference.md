## How it works

Write a template in **wildcard_string**, choose a **seed**, and run the workflow.
Connect **processed_text** to the next node that needs your resolved prompt.
The same template, seed, settings, and wildcard file contents produce the same
result. Change the seed for another selection. Enable **recache_wildcards**
once after adding or editing files, then turn it off again to reuse the cache.
Examples below show possible outputs; your seed determines the actual choices.

### File wildcards

`__filename__` inserts a random non-empty line from `filename.txt`.
Lines whose first non-whitespace character is `#` are ignored. A file's lines
can contain further wildcards. Missing or empty wildcards stay in the prompt.

```text
A photo of a __color__ __animal__.
→ A photo of a blue fox.
```

Wildcard folders are scanned recursively:

- `ComfyUI/wildcards/`
- `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards/`
- Additional folders in `nodes/wildcards/wildcards_paths_user.json` inside the pack.
- Wildcard folders registered with ComfyUI by other integrations.

Exact filename matches rank highest. Specifying a subfolder, as in
`__characters/head__`, prefers that subfolder. Without a subfolder, files closer
to a wildcard folder's root rank above deeper files. Base, numbered, prefix,
and contains matches provide fallbacks. **Fuzzy search** is off by default;
when enabled it also accepts reordered words and interchangeable spaces,
underscores, and hyphens when no literal match is found.

### Glob wildcards

Patterns collect lines from all matching files and choose one line from that
combined pool. Files with more lines contribute more choices.
Supported patterns include `*`, `?`, bracket patterns, and recursive `**`.

```text
__*color*__           → a line from a file with "color" in its name
__animals/*__        → a line from a file in the animals folder
__animals/**/*.txt__ → a line from a matching file under animals
```

### Inline choices

`{a|b|c}` selects one option.

```text
A {red|green|blue} car.
→ A green car.
```

### Empty options

An empty option can leave out part of a prompt. `{red|blue|}` has a one-in-three
chance of producing nothing. Spaces outside the block remain in the output.

```text
A {red |blue |}car.
→ A car.
```

### Weighted choices

Prefix an option with `weight::` to change its chance of being picked.
Unweighted options have weight **1**. Decimal weights, such as `1.5`, work too.
An option's probability is its weight divided by the total weight in the block.

| Example | Chances |
| --- | --- |
| `{5::black\|green\|red}` | Black 5/7, green 1/7, red 1/7 |
| `{4::red\|2::green\|blue}` | Red ~57%, green ~29%, blue ~14% |
| `{5::red\|4::green\|7::blue\|black}` | Red ~29%, green ~24%, blue ~41%, black ~6% |

```text
A {5::black|green|red} car.
→ A black car.

{1.5::cat|dog}
→ cat
```

### Fixed multiple selections

`{2$$a|b|c|d}` selects exactly two items. Items are selected without replacement
within each round; counts exceeding the available choices start another round.
Weights also apply to multiple selections.

The default separator is a **single space**. The Advanced node lets you change
it with **multiple_separator**.

```text
My favourite colours are {2$$red|green|blue|purple}.
→ My favourite colours are red blue.
```

### Ranged multiple selections

`{1-3$$a|b|c|d}` selects a random count from one to three, inclusive.
Selection and separator rules are the same as for fixed counts.

```text
A {1-3$$red|green|blue} outfit.
→ A green blue red outfit.
```

### Custom separators

Place a separator between a second pair of `$$` to override the default or the
Advanced node's separator for that block. It can be any text, including empty.

```text
Comma and space: {2$$, $$red|green|blue}
→ red, blue

Dash: {1-3$$ - $$red|green|blue}
→ green - red

Empty separator: {2$$$$red|green|blue}
→ redblue
```

### Variables

Define a value with `${name=!value}` and reuse it with `${name}`. The value is
evaluated once and the definition itself is removed from the output. Values
may be literal text, file wildcards, inline choices, or nested expressions.

```text
${animal=!__animals__} The ${animal} plays with another ${animal}.
→ The cat plays with another cat.

${color=!{red|{dark|light} blue}} A ${color} car and a ${color} bike.
→ A dark blue car and a dark blue bike.
```

Each variable value is evaluated separately: it can use variables defined
inside that value, but cannot rely on variables defined in the outer template.
Undefined references stay as text and are marked as errors by the highlighter.

### Nesting

Combine file wildcards, choices, weights, counts, and variables. The processor
resolves inner expressions first, then repeats up to **Max nested passes**.
Increase that setting if a deep chain is not fully resolving.

```text
A {{rose|yellow|white} gold|platinum} band.
→ A rose gold band.
```

### Comments and line breaks

Inside choice blocks, `#` starts a comment that ends at the line break.
Line breaks and surrounding whitespace are removed when the block is parsed.

```text
A diamond ring on a {
    {rose|yellow|white} gold # choose a gold colour
    | platinum             # or another metal
} band
→ A diamond ring on a rose gold band
```

## Examples

```text
${animal=!{cat|dog}} A {3::large|small} ${animal} with a
{2$$, $$red|blue|green} collar, beside another ${animal}.

→ A large dog with a red, green collar, beside another dog.
```

## Notes

### Hover help and settings

All settings below are under **Settings → ⚡MNeMiC Nodes → Wildcard Processing**.
**Show hover tooltips** controls the ordinary node and input hover tooltips for
both Wildcard Processor variants and Batch Wildcard Upscale Sampler (including
its positive and negative prompts). It is disabled by default. Hovering **?**
always shows this full, formatted documentation; move into it to scroll.
Click **?** to open the resizable help panel. Press **Escape** to close help.

| Setting | Purpose |
| --- | --- |
| Show hover tooltips | Show or hide ordinary tooltips on both processors and the wildcard sampler; off by default |
| Console logging | Print matching and processing details; off by default |
| Fuzzy search | Enable fuzzy filename matching; off by default |
| Max logged candidates | Limit candidate files printed per match; default 15 |
| Max nested passes | Limit nested resolution passes; default 10 |

### Syntax highlighting

Highlighting works in Wildcard Processor, Wildcard Processor Advanced, Batch
Wildcard Upscale Sampler, and Prompt Property Extractor prompt boxes.
Blocks have separate colours; variables, file wildcards, and tags are coloured
by name. Braces, pipes, weights, counts, and separators can use a stronger shade.
Comments are greyed out. Unclosed braces, stray closing braces, malformed
definitions, and undefined variables can be underlined in red.

```text
{red|{dark|light} blue}       → separate colours for the nested blocks
${animal=!cat} ${animal}     → matching colours for the definition and use
__animals__ __animals__     → matching colours for the same file wildcard
<lora:{styleA|styleB}:0.8>   → tag and its inner choice are highlighted
${undefined}               → red wavy underline when error highlighting is on
```

| Setting | Options |
| --- | --- |
| Enable wildcard highlighting | On / off |
| Highlight color palette | Dark (default), Pastel, Light, Vivid, Muted, Custom |
| Highlight style | Background, Text color, Background + text color, Underline |
| Highlight blocks by | Each block or Nesting depth |
| Highlight background intensity (%) | Background opacity; default 35% |
| Highlight syntax characters more strongly | Emphasize braces, separators, weights, and counts |
| Highlight syntax errors | Red wavy underlines on syntax errors |
| Highlight custom colors | Comma- or space-separated hex or RGB colours for Custom |

Both classic canvas and Nodes 2.0 are supported. Current Chromium browsers
support precise alignment through the CSS Custom Highlight API; older browsers
use a fallback whose alignment can vary with wrapping.

### Preview

Both processors have a collapsible **Preview** section. Open it and run the
workflow to see the resolved prompt coloured by its source in the template.
Hover a coloured segment to see the template text that produced it. Variable
values retain their variable's colour.

```text
Template: A {red|blue} __animal__.
Preview:  A blue fox.

Hover "blue" → {red|blue}
Hover "fox"  → __animal__
```

### Advanced default separator

On **Wildcard Processor Advanced**, **multiple_separator** controls the join
text for multi-pick blocks without their own separator. The default is a single
space. A separator inside a block takes priority.

```text
multiple_separator: ,
Template: {2$$red|green|blue}
→ red,blue

Template: {2$$ - $$red|green|blue}
→ red - blue
```

### Advanced tag outputs

Tag extraction is currently disabled in the UI, so the Advanced node's four
tag outputs are normally empty. They remain for compatibility with saved
workflows. When extraction is supplied by an existing integration, delimiter
pairs such as `[],<>` remove tagged content from the main prompt and resolve its
wildcards separately. Delimiters cannot use `( ) { } |`.

For `[photo by __artist__]<{realistic|painterly}>`, possible extracted values are:

```text
Delimiter pairs: [],<>
Template: A landscape [photo by __artist__]<{realistic|painterly}>

processed_text:        A landscape
extracted_tags_string: photo by Ansel Adams|realistic
extracted_tags_list:   ['photo by Ansel Adams', 'realistic']
raw_tags_string:       [photo by Ansel Adams]<realistic>
raw_tags_list:         ['[photo by Ansel Adams]', '<realistic>']
```

The raw outputs retain delimiters but contain **resolved** wildcard values.
Use **String Text Splitter** to split the pipe-separated extracted string, or
**String Text Extractor** to capture content enclosed by delimiters.

### Related nodes

- **Wildcard Processor Advanced** adds separator control, seed, and tag outputs.
- **Batch Wildcard Upscale Sampler** resolves fresh prompts per image and samples them.
- **String Text Splitter** and **String Text Extractor** help route extracted text.
