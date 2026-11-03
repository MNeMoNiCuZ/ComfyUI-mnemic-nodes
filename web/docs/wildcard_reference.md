## Feature Summary

| Feature | Example | Result |
| --- | --- | --- |
| Random line from a file | `__animals__` | one line from `animals.txt` |
| Whole file | `___scenes/forest___` | all of `forest.txt` |
| Random file from a folder, one line | `~~outfits~~` | a line from a random file in `outfits/` |
| Random file from a folder, whole file | `~~~scenes~~~` | all of a random file in `scenes/` |
| Glob patterns | `__animals/*__` | a line from any file in `animals/` |
| Pick a reference, load its whole file | `___{__scene_list__}___` | all of the one file picked from the list |
| Inline choice | `{red\|green\|blue}` | `green` |
| Empty option | `{red\|blue\|}` | `red`, `blue` or nothing |
| Weights | `{4::red\|blue\|}` | `red` 4/6, `blue` 1/6, nothing 1/6 |
| Pick several | `{2$$red\|green\|blue}` | `red blue` |
| Pick a range | `{1-3$$red\|green\|blue}` | 1 to 3 items |
| Custom separator | `{2$$, $$red\|green\|blue}` | `red, blue` |
| Variables | `${c=!{red\|blue}} a ${c} car, a ${c} bike` | the same colour both times |
| If | `if{${c}==red:a fire truck}` | `a fire truck` when `c` is `red`, otherwise nothing |
| If / else | `if{${c}==red:a fire truck\|a taxi}` | `a fire truck` when `c` is `red`, otherwise `a taxi` |
| If / else if / else | `if{${c}==red:a fire truck\|${c}==blue:a police car\|a taxi}` | the first branch that matches, otherwise `a taxi` |
| Not equal | `if{${c}!=red:not red}` | `not red` when `c` is anything but `red` |
| Nesting | `{{rose\|white} gold\|platinum}` | `rose gold` |
| Names built from variables or choices | `__people/${c}-woman__`, `__people/{France\|Spain}-woman__` | the file is picked by the resolved name |
| Comments | `# note` in a block or at the start of a file line | ignored; whole-file wildcards keep `#` lines |

Each feature is covered in detail below.

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

### Whole-document wildcards

`___filename___` (three underscores on each side) inserts the entire contents
of `filename.txt`. Use it for a multi-paragraph prompt, reusable instructions,
or a complete scene description. It uses the same folders and filename matching
as `__filename__`, which continues to select one random line.

Line breaks, blank lines, indentation, and `#` lines are kept. Wildcards and
inline choices inside the document are resolved normally, so syntax such as
`{red|blue}` still chooses one option. Comment and whitespace rules inside
choice blocks still apply. This includes text files, not PDF or Word documents.

For example, save this as `wildcards/scenes/forest.txt`:

```text
A __animal__ in a quiet forest.

Soft {morning|evening} light filters through the trees.
```

Then use `___scenes/forest___` in your prompt to insert both paragraphs.
You can mix it with line wildcards:

```text
___scenes/forest___
Art style: __styles__
```

`___scenes/*.txt___` chooses one matching file and inserts its full contents;
each matched file contributes one choice, regardless of its length. A named
document without a glob does not consume a random selection for the file itself.
Missing documents stay as tokens; an empty document inserts empty text. Cyclic
document includes and document nesting beyond **Max nested passes** leave the
inner token unresolved. Enable **recache_wildcards** after editing a document.

### Choose one reference, then load its whole document

Use `___{__scene_list__}___` when a wildcard file contains a list of other
wildcard references. It selects **one line** from `scene_list.txt`, then loads
**all lines of that one selected file**.

For example, `scene_list.txt` contains:

```text
__scenes/forest__
__scenes/beach__
```

With `___{__scene_list__}___`, the result is the complete `forest.txt` or the
complete `beach.txt`. It does not combine the two files. Ordinary wildcards
inside the selected document still select individual lines as usual.

You can also choose a document by name directly: `___{scenes/forest|scenes/beach}___`.
Alternatively, put `___scenes/forest___` and `___scenes/beach___` in the list
itself and use the normal `__scene_list__` token to pick one of those entries.

### Folder wildcards

Tildes name a folder instead of a file. The node finds the best matching
folder, picks one random `.txt` file inside it or any of its subfolders, and
then reads it:

- `~~folder~~` inserts a random line from that file, like `__filename__`.
- `~~~folder~~~` inserts the whole file, like `___filename___`.

```text
A __color__ ~~animals~~ in ~~~scenes~~~
```

Folders are matched by name with the same ranking as files: `~~pets~~` finds
`animals/pets`, but a `pets` folder at a wildcard root ranks higher.
`~~animals/pets~~` prefers that exact subfolder. Only one folder is used; folders
with the same name elsewhere are not combined. Every file in the folder has the
same chance, regardless of its length or subfolder; empty and comment-only
files are skipped. Wildcards inside the chosen line or file
are resolved as usual. With the console log enabled, the folder ranking and the
picked file are printed.

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

`{2$$a|b|c|d}` selects exactly two different items. When the count is larger
than the number of options, every option is used once and the rest are picked
again, so `{5$$a|b|c}` gives all three plus two repeats. Weights also apply to
multiple selections.

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

${vehicle=!car|bike} A ${vehicle}.
→ A bike.
```

A bare choice list such as `${vehicle=!car|bike}` works like
`${vehicle=!{car|bike}}`.

A value can use variables defined before it, and variables defined inside
that value. Variables defined later, or inside another value, are not
available. The highlighter marks those uses as errors.

```text
${name=!Anna} ${greeting=!Hello ${name}} ${greeting}!
→ Hello Anna!
```

### Nesting

Combine file wildcards, choices, weights, counts, and variables. The processor
resolves inner expressions first, then repeats up to **Max nested passes**.
Increase that setting if a deep chain is not fully resolving.

```text
A {{rose|yellow|white} gold|platinum} band.
→ A rose gold band.
```

### If blocks

`if{...}` picks text by comparing values, usually variables. Each branch is
`left==right:text` or `left!=right:text`; the first branch whose comparison
holds is used. A branch without a comparison always holds, so put it last as
the else. With no match and no else the block is empty.

```text
${mode=!one|two|three}
if{${mode}==one:a red car}                                   → if
if{${mode}==one:a red car|a blue car}                        → if / else
if{${mode}==one:a red car|${mode}==two:a bus|a blue car}     → if / else if / else
if{${mode}!=one:not one}                                     → not equal
```

- Comparisons ignore case and the spaces around each side.
- Only the chosen branch is resolved, so wildcards and blocks in the other
  branches are never read. Branches can contain blocks, wildcards and other
  `if{...}` blocks.
- `|`, `:` and `==` inside a variable's value or a nested block do not split
  the branch. A plain value written in a condition cannot contain `:`.
- `if` must not end a longer word: `motif{a|b}` is a normal block.
- The highlighter marks a branch with `==` but no `:`, and branches after an
  else, which are never used.

### Building wildcard names

A wildcard name can contain `${variables}` and `{...}` blocks. They are resolved
first, then the finished name is looked up. This works for `__`, `___`, `~~`
and `~~~`.

```text
${location=!__countries__}
A __people/${location}-woman__ in a cafe in ${location}.
→ A line from people/France-woman.txt, in a cafe in France.

__people/{3::France|Spain}-woman__  → a line from people/France-woman.txt or people/Spain-woman.txt
___scenes/${location}___            → all of scenes/France.txt
~~outfits/${location}~~             → a line from a random file in outfits/France
```

The finished name may only contain letters, digits, spaces, `_ - . /` and glob
characters; otherwise the token stays in the output as text. A wildcard cannot
be written directly inside another name: `__people/__countries__-woman__` is
read as `__people/__` followed by text. Use a variable or wrap it in a block,
as in `__people/{__countries__}-woman__`.

### Resolution order

1. **Variable definitions.** Every `${name=!value}` is removed from the
   template, and its value is resolved once, in the order the definitions
   appear. A value can use the variables defined before it.
2. **Passes** over the remaining text, repeated until nothing changes or
   **Max nested passes** is reached. Each pass:
   1. replaces every `${name}` with its value;
   2. resolves `if{...}` blocks: picks a branch, then resolves it completely;
   3. resolves `___{...}___` document choices;
   4. resolves the innermost `{...}` blocks: reads the count, separator and
      weights, picks the options, then resolves the picked text completely;
   5. resolves `__file__`, `___file___`, `~~folder~~`, `~~~folder~~~` and globs,
      then resolves the picked line or document completely.

So nested blocks resolve from the inside out, wildcards inside a block are only
read when their option is picked (`{__a__|__b__}` reads one file), and variables
and blocks are always ready before the wildcard name that contains them.

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

```text
${mode=!portrait|scene}
if{${mode}==portrait:a close-up portrait of __hero__|a wide shot of __location__}

→ a wide shot of Abandoned Asylum
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
definitions, undefined variables, an `if{...}` branch with `==` but no `:`,
and branches after an `if{...}` else can be underlined in red.

```text
{red|{dark|light} blue}       → separate colours for the nested blocks
${animal=!cat} ${animal}     → matching colours for the definition and use
__animals__ __animals__     → matching colours for the same file wildcard
<lora:{styleA|styleB}:0.8>   → tag and its inner choice are highlighted
${undefined}               → red wavy underline when error highlighting is on
if{${m}==a:x|y|z}          → z is underlined: it comes after the else y
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

Tag extraction is disabled, so the Advanced node's four tag outputs are always
empty. They stay on the node so saved workflows keep their connections.

### Related nodes

- **Wildcard Processor Advanced** adds separator control and a seed output.
- **Batch Wildcard Upscale Sampler** resolves fresh prompts per image and samples them.
