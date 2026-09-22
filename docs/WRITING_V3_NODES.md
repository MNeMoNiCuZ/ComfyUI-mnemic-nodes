# Writing V3 Nodes for ⚡ MNeMiC Nodes

[V3 Migration - ComfyUI](https://docs.comfy.org/custom-nodes/v3_migration#dynamiccombo)

This is the house style for writing nodes in this pack using ComfyUI's **V3
node schema**. It is not a migration guide — it is what you follow when writing
a node from scratch, or when touching an existing one.

Everything here was verified against the ComfyUI install this pack ships next to
(`C:/AI/ComfyUI/comfy_api/latest/_io.py`).

---

## 1. The shape of a node

```python
from comfy_api.latest import io


class MyNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_MyNode",
            display_name="⚡ My Node",
            category="⚡ MNeMiC Nodes",
            description="One sentence saying what the node does.",
            inputs=[
                io.String.Input("text", tooltip="The text to process."),
            ],
            outputs=[
                io.String.Output(display_name="text", tooltip="The processed text."),
            ],
        )

    @classmethod
    def execute(cls, text: str) -> io.NodeOutput:
        return io.NodeOutput(text.strip())
```

Rules:

- One node per file in `nodes/`.
- `execute` is a **classmethod**, not an instance method. There is no `self`.
- `execute` receives inputs as **keyword arguments named after the input `id`**.
- `execute` must return `io.NodeOutput(...)`, never a bare tuple.
- No `INPUT_TYPES`, `RETURN_TYPES`, `RETURN_NAMES`, `FUNCTION`, `CATEGORY`,
  `DESCRIPTION`, `OUTPUT_NODE`, `OUTPUT_IS_LIST`, `OUTPUT_TOOLTIPS`,
  `IS_CHANGED` or `VALIDATE_INPUTS` class attributes. They all move into the
  schema or into the replacement methods in §7.

### Registration

The pack is registered through a single V3 entrypoint in the root `__init__.py`.
`NODE_CLASS_MAPPINGS` and `comfy_entrypoint` are **mutually exclusive** —
ComfyUI checks for `NODE_CLASS_MAPPINGS` first and never looks at
`comfy_entrypoint` if it exists. So the root `__init__.py` must not define
`NODE_CLASS_MAPPINGS` at all.

```python
from comfy_api.latest import ComfyExtension, io
from .nodes.my_node import MyNode


class MnemicExtension(ComfyExtension):
    async def on_load(self) -> None:
        ...  # one-time setup, node replacements, runtime hooks

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [MyNode, ...]


async def comfy_entrypoint() -> MnemicExtension:
    return MnemicExtension()
```

Individual node files must **not** define their own `NODE_CLASS_MAPPINGS` /
`NODE_DISPLAY_NAME_MAPPINGS` blocks. Adding a node means three edits:

1. `nodes/my_node.py` — the class.
2. `nodes/__init__.py` — import + `__all__` entry.
3. `__init__.py` — import + entry in `get_node_list()`.

---

## 2. Naming

| Thing                 | Rule                                                         | Example                          |
| --------------------- | ------------------------------------------------------------ | -------------------------------- |
| `node_id`             | ASCII, `MNeMiC_` prefix, PascalCase, **never changes**       | `MNeMiC_WildcardProcessor`       |
| `display_name`        | Emoji + Title Case words, this is the only user-visible name | `📝 Wildcard Processor`          |
| `category`            | Always `"⚡ MNeMiC Nodes"`                                    |                                  |
| input / output `id`   | `lower_snake_case`, ASCII                                    | `max_length`, `seed`             |
| `display_name` on I/O | Only when the id would read badly                            | `id="cfg"`, `display_name="CFG"` |
| Python class          | PascalCase, matches the `node_id` suffix                     | `WildcardProcessor`              |
| file name             | `lower_snake_case.py` of the class                           | `wildcard_processor.py`          |

`node_id` is what gets written into saved workflows. **Changing a `node_id`
breaks every saved workflow that uses the node.** Pick it once, carefully.
`display_name` is free to change at any time.

### Renaming, and `LEGACY_NODE_IDS`

Every node in this pack was once identified by its emoji display string
(`"📁 Get File Path"`). Those ids are still in every workflow anyone saved, so
the root `__init__.py` keeps a `LEGACY_NODE_IDS` map from old id to new id and
registers a `NodeReplace` for each one in `on_load`. ComfyUI rewrites matching
nodes when a workflow is loaded or queued.

- **Never delete an entry from that map.** It is what keeps old workflows
  loadable.
- If you ever rename an id again, add the old one to the map — that is the
  whole change. The replacement is generated from the schema.

§11 has the full mechanism and the three ways it goes wrong.

When a node is renamed for the user, keep discoverability with:

```python
search_aliases=["old name", "synonym", "abbreviation"],
```

---

## 3. Inputs

### Types

```python
io.Int.Input("count", default=1, min=0, max=100, step=1)
io.Float.Input("strength", default=1.0, min=0.0, max=10.0, step=0.01, round=0.001)
io.String.Input("text", default="", multiline=True, placeholder="Prompt…")
io.Boolean.Input("enabled", default=True, label_on="on", label_off="off")
io.Combo.Input("mode", options=["a", "b"], default="a")
io.MultiCombo.Input("tags", options=[...], default=[])

io.Image.Input("image")
io.Mask.Input("mask", optional=True)
io.Latent.Input("latent")
io.Model.Input("model")
io.Clip.Input("clip")          # note: io.Clip, not io.CLIP
io.Vae.Input("vae")            # note: io.Vae
io.Conditioning.Input("positive")
io.Audio.Input("audio")
io.AnyType.Input("anything")
```

### Arguments every input accepts

`id`, `display_name`, `optional`, `tooltip`, `lazy`, `advanced`, `raw_link`,
`extra_dict`. Widget inputs additionally accept `default`, `socketless`,
`force_input`.

### Seeds

```python
io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff,
             control_after_generate=True)
```

`control_after_generate` may also take a specific mode:
`io.ControlAfterGenerate.randomize` / `.increment` / `.decrement` / `.fixed`.

### Optional inputs

`optional=True` means the input may be missing. Give the parameter a default in
`execute` so the node still runs when nothing is connected:

```python
inputs=[io.Mask.Input("mask", optional=True)]

@classmethod
def execute(cls, image, mask=None) -> io.NodeOutput:
    ...
```

---

## 4. Tooltips, descriptions and hints — the house standard

Three separate surfaces, three different jobs. Fill in all three.

### 4.1 `description` — the node tooltip

One or two sentences. Shown when hovering the node title and in the node search
results. Say what the node **does** and what it is **for**. No parameter lists,
no priority tables, no ASCII art — that belongs in the help page (§5).

```python
description="Generates a random seed value between 0 and 2^64-1. Re-rolls on every run."
```

Standard: starts with a verb in third person ("Generates…", "Loads…",
"Splits…"), ends with a period, under ~200 characters.

### 4.2 `tooltip` — per input and per output

**Every input and every output gets a tooltip. No exceptions.** This is the
single highest-value thing in the schema and the thing most nodes in the wild
get wrong.

Standard form:

```
<What it is / does>. <Units, range or accepted values if not obvious>. <Default or edge-case behaviour if surprising>.
```

```python
io.Int.Input(
    "max_length",
    default=0, min=0, max=4096,
    tooltip="Maximum number of characters to keep. 0 disables truncation.",
)
io.Combo.Input(
    "mode",
    options=["first", "last", "all"],
    tooltip="Which match to return. 'all' joins every match with the separator.",
)
io.String.Output(
    display_name="text",
    tooltip="The cleaned text. Empty if the input contained no usable characters.",
)
```

Rules:

- Sentence case, ends with a period.
- Describe behaviour, not the type — the socket colour already says `INT`.
- Always document the meaning of `0`, `-1`, `""` and other sentinel values.
- Always state the unit (pixels, seconds, characters, tokens).
- Do not repeat the input's own name back at the user
  ("The seed" is worthless; "Seed for the random number generator. Same seed
  gives the same output." is a tooltip).
- **Keep them to one or two lines.** A tooltip is a mouseover, not a manual —
  once it needs a list, a table or an example, it belongs in the help page
  (§5), and the tooltip should end with "see the node Info panel for …" instead.

Tooltip width in this pack is set by `web/js/tooltip_width.js`; write for that
width rather than fighting it.

### 4.3 `placeholder` — the in-widget hint

`placeholder` is greyed-out background text drawn inside an **empty** widget.
It is not a value: it is never saved in the workflow, never passed to
`execute`, and it vanishes as soon as the field contains anything. Empty stays
empty.

```python
io.String.Input("wildcard_string", multiline=True,
                placeholder="A photo of a __sample_colors__ {dog|cat|monkey}.")
```

**Use it sparingly.** The house rule in this pack is: only when the field's
*syntax* is impossible to guess and an example is worth more than a sentence —
a template language, a token format. Not for paths, not for plain text, not for
anything the tooltip already covers, and never as a substitute for a tooltip.

Where it is used today: `wildcard_string` on the wildcard nodes and the batch
sampler, `prefix` on 💾 Save Text File With Path, and the delimiter/index
fields on the two ✂️ String Text nodes.

### 4.4 Node status flags

```python
is_experimental=True   # shows the "experimental" badge; may change or break
is_deprecated=True     # shows the "deprecated" badge; hidden from search
```

Deprecate rather than delete. A deleted node makes saved workflows unloadable;
a deprecated one keeps working and tells the user to move on.

---

## 5. Help pages

Every node needs `web/docs/<node_id>.md` — file name exactly the `node_id`,
media in `web/docs/media/`, referenced relatively. Nothing else to register:
`web/js/help_button.js` adds the `?` to every node in `⚡ MNeMiC Nodes` and
loads that file. Long reference material goes here, not in tooltips (§4.2).

Template:

```markdown
# 📝 Wildcard Processor

Short paragraph: what the node does and when you would reach for it.

## Inputs

- **wildcard_text** — Text containing `__wildcard__` tokens to resolve.
- **seed** — Seed for wildcard selection. Same seed gives the same result.

## Outputs

- **text** — The resolved text with all wildcards replaced.

## How it works

Longer explanation, priority orders, matching rules, gotchas — everything that
is too long for a tooltip.

## Examples

```
Input:  A photo of a __color__ __animal__
Output: A photo of a red fox
```

![example](media/wildcard_example.png)
```

Sections in order: title (matching `display_name`), intro paragraph, `Inputs`,
`Outputs`, `How it works`, `Examples`, `Notes`. Skip a section if it has nothing
to say; do not reorder them.

---

## 6. Hiding advanced controls

Anything a user touches on fewer than roughly one workflow in five belongs
behind the node's **Show advanced inputs** toggle:

```python
io.Boolean.Input("hires_fix", default=False,
                 tooltip="Enable the second high-resolution pass."),
io.Float.Input("hires_denoise", default=0.4, min=0.0, max=1.0,
               tooltip="Denoise strength for the high-res pass.",
               advanced=True),
```

House rules for `advanced=True`:

- The **switch stays visible, the knobs go advanced.** If a group of settings is
  gated by a boolean, that boolean is always visible and the settings it
  controls are advanced.
- Never make an input advanced if the node produces wrong or surprising output
  at its default. Advanced means "tune it", never "you must set this".
- Never make a required-to-understand input advanced just to shorten the node.
- Debug / logging / verbosity toggles are always advanced.
- Advanced inputs still need full tooltips — more so, since they are the obscure
  ones.

**Limits.** `advanced` only affects **widgets**. It does nothing for connection
slots (`MODEL`, `CLIP`, `VAE`, `LATENT`, `CONDITIONING`, `IMAGE` sockets) and
nothing for outputs. There is no supported way to hide an output slot from
Python.

---

## 7. Replacing the old V1 special methods

| V1                         | V3                                                    |
| -------------------------- | ----------------------------------------------------- |
| `IS_CHANGED`               | `fingerprint_inputs`                                  |
| `VALIDATE_INPUTS`          | `validate_inputs`                                     |
| `check_lazy_status`        | `check_lazy_status` (unchanged)                       |
| `OUTPUT_NODE = True`       | `is_output_node=True` in the schema                   |
| `INPUT_IS_LIST`            | `is_input_list=True`                                  |
| `OUTPUT_IS_LIST = (True,)` | `is_output_list=True` on that `Output`                |
| hidden `UNIQUE_ID` etc.    | `hidden=[io.Hidden.unique_id]`, read via `cls.hidden` |

```python
@classmethod
def fingerprint_inputs(cls, path: str, **kwargs):
    return os.path.getmtime(path)      # re-runs when the file changes

@classmethod
def validate_inputs(cls, width: int, **kwargs) -> bool | str:
    if width % 8:
        return "Width must be a multiple of 8."
    return True
```

Force a node to re-run every execution: keep returning a always-changing value
from `fingerprint_inputs` (the old `return time.time()` trick).

```python
@classmethod
def fingerprint_inputs(cls, **kwargs):
    return time.time()
```

`not_idempotent=True` is **not** a substitute for this. It only adds the node id
to the cache key, so two identically-configured copies of the node each get
their own cache entry; it does not force a re-run.

### Hidden inputs

```python
return io.Schema(
    ...,
    hidden=[io.Hidden.unique_id, io.Hidden.prompt, io.Hidden.extra_pnginfo],
)

@classmethod
def execute(cls, ...) -> io.NodeOutput:
    node_id = cls.hidden.unique_id
    prompt = cls.hidden.prompt
```

`is_output_node=True` automatically adds `prompt` and `extra_pnginfo`.

---

## 8. Outputs and UI results

```python
return io.NodeOutput(width, height, latent)          # order matches schema
return io.NodeOutput(image, ui=ui.PreviewImage(image, cls=cls))
return io.NodeOutput(ui=ui.PreviewText(report))      # UI only, no outputs
return io.NodeOutput()                               # nothing
```

`from comfy_api.latest import ui` gives `ui.PreviewImage`, `ui.PreviewMask`,
`ui.PreviewAudio`, `ui.PreviewVideo`, `ui.PreviewText`, `ui.PreviewUI3D`, plus
`ui.ImageSaveHelper` and `ui.AudioSaveHelper` for save nodes. Always pass
`cls=cls` to the preview helpers so results are attributed to the right node.

A node that only writes files or shows a preview is an output node:

```python
is_output_node=True
```

---

## 9. Dynamic inputs

Use these instead of a wall of `optional` widgets or a giant combo whose value
half the widgets ignore.

### DynamicCombo — show only the widgets that the chosen mode uses

```python
io.DynamicCombo.Input("resize_type", options=[
    io.DynamicCombo.Option("scale by dimensions", [
        io.Int.Input("width", default=512, min=0, max=8192,
                     tooltip="Target width in pixels."),
        io.Int.Input("height", default=512, min=0, max=8192,
                     tooltip="Target height in pixels."),
    ]),
    io.DynamicCombo.Option("scale by multiplier", [
        io.Float.Input("multiplier", default=1.0, min=0.01, max=8.0,
                       tooltip="Multiplier applied to the source size."),
    ]),
])

@classmethod
def execute(cls, image, resize_type: dict) -> io.NodeOutput:
    mode = resize_type["resize_type"]
    if mode == "scale by dimensions":
        w, h = resize_type["width"], resize_type["height"]
```

The whole group arrives as **one dict** keyed by the input ids, plus the combo's
own id holding the selected option name.

### Autogrow — a variable number of the same input

```python
template = io.Autogrow.TemplatePrefix(
    input=io.Image.Input("image", tooltip="An image to append to the batch."),
    prefix="image", min=2, max=50,
)
inputs=[io.Autogrow.Input("images", template=template)]

@classmethod
def execute(cls, images: io.Autogrow.Type) -> io.NodeOutput:
    return io.NodeOutput(batch(list(images.values())))
```

### MatchType — outputs that take the type of an input

```python
t = io.MatchType.Template("type", allowed_types=[io.Image, io.Mask, io.Latent])
inputs=[
    io.Boolean.Input("switch", tooltip="Which input to pass through."),
    io.MatchType.Input("on_false", template=t, lazy=True),
    io.MatchType.Input("on_true", template=t, lazy=True),
]
outputs=[io.MatchType.Output(template=t, display_name="output")]
```

### MultiType — one input accepting several types

```python
io.MultiType.Input("source", types=[io.Image, io.Mask])
io.MultiType.Input(io.String.Input("model_file", default=""),
                   types=[io.File3DGLB, io.File3DOBJ])
```

Prefer `MatchType` / `MultiType` over `io.AnyType`. `AnyType` gives the user no
guard rails and no error until execution.

---

## 10. Async and progress

`execute` may be `async`. Anything doing network I/O (the Groq nodes, URL
downloads, model fetches) should be, so it does not block the executor.

```python
from comfy_api.latest import ComfyAPI
api = ComfyAPI()

@classmethod
async def execute(cls, images) -> io.NodeOutput:
    for i, image in enumerate(images):
        ...
        await api.execution.set_progress(value=i + 1, max_value=len(images))
    return io.NodeOutput(result)
```

---

## 11. Renaming a node without breaking workflows

A saved workflow stores the `node_id`, so changing one orphans every workflow
that used the node. `NodeReplace` fixes that: it tells ComfyUI how to turn the
old node into the new one, on load in the UI and on queue in the backend.

**Do not hand-write one.** The whole pack is renamed by the generator in the
root `__init__.py` — add the old id to `LEGACY_NODE_IDS` and you are done:

```python
LEGACY_NODE_IDS = {
    "📁 Get File Path": "MNeMiC_GetFilePath",
    ...
}
```

`on_load` then builds a `NodeReplace` per entry from the node's own schema.
The rest of this section is why that generator looks the way it does — read it
before touching it, because every trap here fails **silently**: the workflow
loads, it just comes back wrong.

### It rebuilds the node; nothing is carried by default

The replacement does not edit the old node. It constructs a fresh one from the
new schema and then copies things across, one mapping entry at a time. Anything
not named in a mapping is simply not copied.

```python
io.NodeReplace(
    new_node_id=schema.node_id,
    old_node_id=old_node_id,
    old_widget_ids=widget_ids,
    input_mapping=[{"new_id": i, "old_id": i} for i in input_ids],
    output_mapping=[{"new_idx": i, "old_idx": i} for i in range(len(schema.outputs))],
)
```

For a pure rename every entry is the identity — but it still has to be written
out. In particular `output_mapping=None` does **not** mean "outputs are
unchanged", it means "carry no output links", and the frontend skips the entire
output block. Leave it out and every node comes back with its outputs
disconnected.

### `old_widget_ids` is positional, and seeds take two slots

Widget values live in the workflow as a bare `widgets_values` array with no
names in it. The frontend recovers them with:

```js
widgets_values[old_widget_ids.indexOf(id)]
```

So `old_widget_ids` has to mirror that array exactly, entry for entry:

- **Sockets are not in it.** Skip anything that is not a `WidgetInput`, and
  anything with `force_input=True` — those render as connection slots.
- **A seed takes two slots.** The frontend attaches a linked *control after
  generate* widget to any INT widget named `seed` or `noise_seed`, and to any
  input that sets `control_after_generate`. That widget has its own entry in
  `widgets_values`, so `old_widget_ids` needs a placeholder for it:

```python
widget_ids.append(input_id)
if _has_control_after_generate(node_input, input_id):
    widget_ids.append(f"{input_id}_control_after_generate")
```

Miss that placeholder and every widget after the seed is read one slot early:
`batch_size` receives the string `"randomize"` and shows `NaN`, `width` receives
the old `batch_size`, and the whole node arrives shifted by one. It looks like
an output-count problem; it is not.

Do **not** add the placeholder to `input_mapping`. The backend does
`old_node["inputs"][old_id]` with no guard, so an id the old node never had
raises `KeyError` and kills the prompt. The cost of leaving it out is small:
the control-after-generate *setting* comes back at its default while every real
widget value transfers.

### Inputs added at runtime by JS cannot survive

Slots that a JS extension creates on the fly — `string_2`, `string_3`, … on
🔗 String Concat, the `region_N` pins on 🧩 Ideogram 4 Prompt Builder — are not
in the schema, so they are not in the mapping. The frontend looks each slot up
**by name on the freshly built node**, does not find it, and drops the link.
There is no supported fix: `NodeReplace` has no field for a note and the
replacement dialog's text is fixed.

`web/js/legacy_node_warning.js` warns instead — on graph load it counts links
sitting on at-risk slots and raises a toast naming the node and the number of
connections a replacement would drop. Add to its `DYNAMIC_INPUT_NODES` map if
you ever write another node of that shape.

### Verifying a rename

The failures are silent, so check by hand: load a workflow saved before the
rename and confirm the node arrives with its **widget values**, its **input
links** and its **output links** intact. A value showing `NaN`, or a number
appearing one row below where it belongs, is the seed-slot bug above.

### When the input set itself changes

Everything here assumes an id-only rename. If inputs are added, removed or
restructured, the mapping stops being the identity and you are writing it by
hand — `{"new_id": ..., "old_id": ...}` per surviving input and
`{"new_id": ..., "set_value": ...}` for anything new that needs a value.
`set_value` is a constant: it cannot look at the old node, so a new mode widget
gets one fixed answer for every migrated node. If the right value depends on
what the old node was set to, ship a new node instead of converting the old
one.

---

## 12. Checklist before committing a node

- [ ] `node_id` is ASCII, `MNeMiC_`-prefixed, and unchanged from what shipped.
- [ ] `display_name` has an emoji and reads as Title Case.
- [ ] `category="⚡ MNeMiC Nodes"`.
- [ ] `description` is one or two sentences, verb-first.
- [ ] **Every** input has a `tooltip`. **Every** output has a `tooltip`.
- [ ] Sentinel values (`0`, `-1`, `""`, `None`) are documented in the tooltip.
- [ ] String inputs with a format have a `placeholder`.
- [ ] Rarely-used and all debug/logging widgets are `advanced=True`.
- [ ] `web/docs/<node_id>.md` exists and follows the §5 template.
- [ ] `execute` is a classmethod returning `io.NodeOutput`.
- [ ] No leftover V1 attributes or per-file `NODE_CLASS_MAPPINGS`.
- [ ] Registered in `nodes/__init__.py` and in `get_node_list()`.
- [ ] Optional inputs have Python defaults in the `execute` signature.
