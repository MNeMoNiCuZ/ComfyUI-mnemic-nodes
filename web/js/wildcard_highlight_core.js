// Wildcard syntax highlighting for multiline text widgets.
//
// This module has no ComfyUI imports so it can be reused by any node (and
// tested outside ComfyUI). It provides:
//   - parseWildcardText(text): a syntax tree of the wildcard template
//   - computeWildcardRanges(text, options): the highlighted ranges and styles
//   - renderWildcardHTML(text, options): highlighted HTML (fallback)
//   - WildcardHighlighter: draws the highlighting behind a <textarea>
//
// The highlighter works as a "backdrop": a div with exactly the same font,
// padding and size as the textarea is placed behind it, and the textarea is
// made transparent. The textarea stays the real editor (caret, selection,
// undo and copy/paste all behave as normal); the backdrop only paints colors.
// Because of that the backdrop must never change text layout. It holds the
// text as one plain text node colored with the CSS Custom Highlight API;
// even layout-neutral spans can move a line break by a fraction of a pixel.
// Spans are only a fallback for browsers without that API.

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

const WILDCARD_RE = /__([a-zA-Z0-9_./\\*?\[\] -]+?)__/y;
const TAG_PREFIX_RE = /<([a-zA-Z_][a-zA-Z0-9_]*):/y;
const COUNT_RE = /\d+(?:-\d+)?\$\$/y;
const WEIGHT_RE = /\d+(?:\.\d+)?::/y;

// Limits that keep parsing fast and the call stack safe on pathological
// text (thousands of nested or unclosed braces). Text past them is shown
// without highlighting instead of freezing or crashing the editor.
const MAX_DEPTH = 200;
const STEP_BUDGET_BASE = 50000;
const STEP_BUDGET_PER_CHAR = 6;

class TooComplex extends Error {}

/** Run a sticky regex at exactly `index` and return the match or null. */
function matchAt(re, text, index) {
    re.lastIndex = index;
    return re.exec(text);
}

/** Make a syntax-character node covering text[start, end). */
function delim(start, end, kind) {
    return { type: "delim", kind, start, end, children: [] };
}

/**
 * Parse a wildcard template into a tree of nodes. Every node has
 * { type, start, end, children } where start/end are offsets into text.
 *
 * Node types:
 *   choice   {a|b|c} inline choice block
 *   option   one option of a choice block; has `index`
 *   vardef   ${name=!value} variable definition; has `name`
 *   varuse   ${name} variable use; has `name`
 *   varname  the name inside a vardef
 *   wildcard __file__ wildcard; has `name`
 *   tag      <name:value> property/LoRA tag; has `name`
 *   comment  # comment inside a choice block
 *   delim    syntax characters; has `kind` (brace, pipe, weight, count, sep, var, tag)
 *   error    stray or unclosed syntax characters; has `message`
 * Nodes that are usable but wrong (undefined variables, a definition cut
 * off at the first "}") get `error` set.
 *
 * If the text is too deeply nested or too expensive to parse, the root has
 * no children and `tooComplex` is set.
 */
export function parseWildcardText(text) {
    const n = text.length;
    let steps = 0;
    let level = 0;
    const budget = STEP_BUDGET_BASE + STEP_BUDGET_PER_CHAR * n;
    // Parsed blocks by start offset. A block at a given offset parses the
    // same wherever it is nested, so each is parsed only once. Without this,
    // unclosed blocks make the parse exponential (or quadratic when cached
    // only on failure).
    const blocks = new Map();

    /** Count one unit of parse work, giving up past the budget. */
    function step() {
        if (++steps > budget) throw new TooComplex();
    }

    /** Parse the block starting at i with `parse`, once per offset. */
    function block(i, parse) {
        if (!blocks.has(i)) blocks.set(i, parse(i));
        return blocks.get(i);
    }

    /**
     * Parse text from `i` until the end of the current block; returns { children, end }.
     * mode: "top" | "option" (inside a choice) | "value" (inside a vardef) | "tag"
     */
    function parseSequence(i, mode) {
        const children = [];
        if (++level > MAX_DEPTH) throw new TooComplex();
        while (i < n) {
            step();
            const c = text[i];
            if (c === "$" && text[i + 1] === "{") {
                const node = block(i, parseVariable);
                if (node) {
                    const stray = node.error && !node.recovered;
                    children.push(stray ? strayError(node) : node);
                    i = stray ? i + 2 : node.end;
                    continue;
                }
            } else if (c === "{") {
                const node = block(i, parseChoice);
                children.push(node.error ? strayError(node) : node);
                i = node.error ? i + 1 : node.end;
                continue;
            } else if (c === "}") {
                if (mode !== "top") break;
                children.push({ type: "error", start: i, end: i + 1, message: "Unmatched }", children: [] });
                i++;
                continue;
            } else if (c === "|" && (mode === "option" || mode === "tag")) {
                break;
            } else if ((c === ">" || c === "<" || c === "\n") && mode === "tag") {
                break;
            } else if (c === "#" && mode === "option") {
                // The processor resolves blocks nested in a comment first, so
                // only a } at the comment's own level ends it.
                let j = i;
                let nested = 0;
                while (j < n && text[j] !== "\n") {
                    if (text[j] === "{") nested++;
                    else if (text[j] === "}" && nested-- === 0) break;
                    j++;
                    step();
                }
                children.push({ type: "comment", start: i, end: j, children: [] });
                i = j;
                continue;
            } else if (c === "_" && text[i + 1] === "_") {
                const m = matchAt(WILDCARD_RE, text, i);
                if (m) {
                    children.push({ type: "wildcard", name: m[1], start: i, end: i + m[0].length, children: [] });
                    i += m[0].length;
                    continue;
                }
            } else if (c === "<") {
                const node = block(i, parseTag);
                if (node) {
                    children.push(node);
                    i = node.end;
                    continue;
                }
            }
            i++;
        }
        level--;
        return { children, end: i };
    }

    /**
     * An unclosed block only flags its opening characters; the text after
     * it is parsed again as normal text (the processor leaves it as-is too).
     */
    function strayError(node) {
        const length = node.type === "vardef" ? 2 : 1;
        return { type: "error", start: node.start, end: node.start + length, message: node.error, children: [] };
    }

    /**
     * The processor drops whitespace that contains a line break before it
     * reads counts and weights, so "{\n2$$a|b}" still has a count.
     */
    function skipLineBreak(i) {
        let j = i;
        while (j < n && /\s/.test(text[j])) j++;
        return text.slice(i, j).includes("\n") ? j : i;
    }

    /** Parse the {a|b|c} block that opens at `start`. Sets `error` if it never closes. */
    function parseChoice(start) {
        const node = { type: "choice", start, end: n, children: [delim(start, start + 1, "brace")] };
        let i = start + 1;

        // Optional count prefix (N$$ or N-M$$), then an optional custom separator (sep$$).
        const countAt = skipLineBreak(i);
        const count = matchAt(COUNT_RE, text, countAt);
        if (count) {
            i = countAt;
            node.children.push(delim(i, i + count[0].length, "count"));
            i += count[0].length;
            // A custom separator runs to the next "$$", if that comes
            // before any |, { or }.
            for (let j = i; j < n && !"|{}".includes(text[j]); j++) {
                step();
                if (text[j] === "$" && text[j + 1] === "$") {
                    node.children.push(delim(i, j + 2, "sep"));
                    i = j + 2;
                    break;
                }
            }
        }

        let index = 0;
        while (true) {
            const option = { type: "option", index: index++, start: i, end: i, children: [] };
            const weightAt = skipLineBreak(i);
            const weight = matchAt(WEIGHT_RE, text, weightAt);
            if (weight) {
                i = weightAt;
                option.children.push(delim(i, i + weight[0].length, "weight"));
                i += weight[0].length;
            }
            const seq = parseSequence(i, "option");
            option.children.push(...seq.children);
            option.end = seq.end;
            node.children.push(option);
            i = seq.end;

            if (text[i] === "|") {
                node.children.push(delim(i, i + 1, "pipe"));
                i++;
                continue;
            }
            if (text[i] === "}") {
                node.children.push(delim(i, i + 1, "brace"));
                node.end = i + 1;
            } else {
                node.error = "Unclosed {";
                node.end = n;
            }
            return node;
        }
    }

    /** Parse the ${name} use or ${name=!value} definition at `start`, or return null. */
    function parseVariable(start) {
        // start points at "${". Returns null when this is not a variable,
        // in which case the "$" is treated as plain text.
        let j = start + 2;
        while (j < n && text[j] !== "}" && text[j] !== "{" && text[j] !== "\n" && !(text[j] === "=" && text[j + 1] === "!")) j++;
        if (j >= n || text[j] === "{" || text[j] === "\n") return null;

        const rawName = text.slice(start + 2, j);
        if (text[j] === "}") {
            if (!rawName.trim()) return null;
            return {
                type: "varuse",
                name: rawName,
                start,
                end: j + 1,
                children: [delim(start, start + 2, "var"), delim(j, j + 1, "var")],
            };
        }

        // Definition: ${name=!value}
        const head = [
            delim(start, start + 2, "var"),
            { type: "varname", start: start + 2, end: j, children: [] },
            delim(j, j + 2, "var"),
        ];
        const node = { type: "vardef", name: rawName.trim(), start, end: n, children: [...head] };
        const seq = parseSequence(j + 2, "value");
        if (text[seq.end] === "}") {
            node.children.push(...seq.children, delim(seq.end, seq.end + 1, "var"));
            node.end = seq.end + 1;
            return node;
        }

        // Unbalanced value. The processor then ends the definition at the
        // first "}" on the same line (and still defines the variable), so
        // show it that way, flagged. With no such "}" it is left as text.
        const close = text.indexOf("}", j + 2);
        const lineEnd = text.indexOf("\n", j + 2);
        if (close !== -1 && (lineEnd === -1 || close < lineEnd)) {
            node.children = [...head, delim(close, close + 1, "var")];
            node.end = close + 1;
            node.error = "Unbalanced ${: the value ends at the first }";
            node.recovered = true;
        } else {
            node.error = "Unclosed ${";
        }
        return node;
    }

    /** Parse the <name:value> tag at `start`, or return null if it is not one. */
    function parseTag(start) {
        const m = matchAt(TAG_PREFIX_RE, text, start);
        if (!m) return null;
        const seq = parseSequence(start + m[0].length, "tag");
        if (text[seq.end] !== ">") return null;
        return {
            type: "tag",
            name: m[1].toLowerCase(),
            start,
            end: seq.end + 1,
            children: [delim(start, start + m[0].length, "tag"), ...seq.children, delim(seq.end, seq.end + 1, "tag")],
        };
    }

    let root;
    try {
        root = { type: "root", start: 0, end: n, children: parseSequence(0, "top").children };
    } catch (err) {
        if (!(err instanceof TooComplex)) throw err;
        return { type: "root", start: 0, end: n, children: [], tooComplex: true };
    }

    // Link variable definitions and uses. Each definition's value is
    // resolved on its own, so it is a separate scope: it sees only the
    // definitions inside it, and the rest of the text does not see those.
    function checkScope(node, defs, uses) {
        for (const child of node.children) {
            if (child.type === "vardef") {
                defs.add(child.name);
                const innerDefs = new Set();
                const innerUses = [];
                checkScope(child, innerDefs, innerUses);
                for (const use of innerUses) {
                    if (!innerDefs.has(use.name)) {
                        use.error = "Undefined here: a variable's value only sees variables defined inside that value";
                    }
                }
            } else if (child.type === "varuse") {
                uses.push(child);
            } else {
                checkScope(child, defs, uses);
            }
        }
    }
    const defs = new Set();
    const uses = [];
    checkScope(root, defs, uses);
    for (const use of uses) {
        if (!defs.has(use.name)) use.error = "Undefined variable";
    }

    return root;
}

/** Call fn on node and every node below it, parents first. */
function walk(node, fn) {
    fn(node);
    for (const child of node.children) walk(child, fn);
}

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

// Saturation / lightness per palette. Hues are generated with the golden
// angle so neighbouring blocks always get clearly different colors, however
// many blocks there are.
const PALETTES = {
    Pastel: { s: 75, l: 82 },
    Light: { s: 90, l: 70 },
    Vivid: { s: 85, l: 55 },
    Dark: { s: 60, l: 32 },
    Muted: { s: 25, l: 55 },
};


export const DEFAULT_OPTIONS = {
    enabled: true,
    palette: "Dark",
    style: "Background",
    coloring: "Each block",
    intensity: 35,
    emphasizeSyntax: true,
    markErrors: true,
    customColors: "",
};

const HUE_START = 200;
const GOLDEN_ANGLE = 137.508;

/** Parse "#rgb", "#rrggbb" or "rgb(r, g, b)" into [r, g, b], or return null. */
function parseColor(value) {
    const probe = String(value).trim();
    if (!probe) return null;
    let m = probe.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (m) {
        let hex = m[1];
        if (hex.length === 3) hex = hex.split("").map((ch) => ch + ch).join("");
        return [0, 2, 4].map((k) => parseInt(hex.slice(k, k + 2), 16));
    }
    m = probe.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
    if (m) return [Number(m[1]), Number(m[2]), Number(m[3])];
    return null;
}

/** Convert HSL (degrees, percent, percent) to [r, g, b] in 0-255. */
function hslToRgb(h, s, l) {
    s /= 100;
    l /= 100;
    const k = (x) => (x + h / 30) % 12;
    const a = s * Math.min(l, 1 - l);
    const f = (x) => l - a * Math.max(-1, Math.min(k(x) - 3, Math.min(9 - k(x), 1)));
    return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}

/** Return a function mapping a palette index to [r, g, b] for the chosen palette. */
function makeColorSource(options) {
    const custom = options.palette === "Custom"
        ? (String(options.customColors || "").match(/#[0-9a-f]{3}(?:[0-9a-f]{3})?\b|rgba?\([^)]*\)/gi) || []).map(parseColor).filter(Boolean)
        : [];
    if (custom.length) return (index) => custom[index % custom.length];
    const { s, l } = PALETTES[options.palette] || PALETTES.Dark;
    return (index) => hslToRgb((HUE_START + index * GOLDEN_ANGLE) % 360, s, l);
}

/** Format [r, g, b] and an alpha (clamped to 0-1) as a CSS rgba() color. */
function rgba(rgb, alpha) {
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${Math.max(0, Math.min(1, alpha)).toFixed(3)})`;
}

/**
 * Give every colorable node a palette index. Variables and file wildcards
 * with the same name share an index, so a variable's definition and all of
 * its uses always get the same color.
 */
function assignColors(root, coloring) {
    const byDepth = coloring === "Nesting depth";
    let next = 0;
    const named = new Map();
    const nameIndex = (key) => {
        if (!named.has(key)) named.set(key, byDepth ? 1000 + named.size : next++);
        return named.get(key);
    };
    const visit = (node, depth) => {
        switch (node.type) {
            case "choice":
                node.color = byDepth ? depth : next++;
                depth++;
                break;
            case "vardef":
            case "varuse":
                node.color = nameIndex(`var:${node.name.trim()}`);
                break;
            case "wildcard":
                node.color = nameIndex(`file:${node.name}`);
                break;
            case "tag":
                node.color = nameIndex(`tag:${node.name}`);
                break;
        }
        for (const child of node.children) visit(child, depth);
    };
    visit(root, 0);
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

const ERROR_COLOR = "#ff4d4f";
const COMMENT_RGB = [128, 128, 128];

/** Escape text for use in HTML content and attribute values. */
function escapeHTML(text) {
    return text.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
}

/**
 * Parse text and work out how each node is painted. Every styled node gets
 * `paint` = { background, color, underline, wavy, rounded } (only the parts
 * that apply) and `layer` = how deeply it is nested, so inner layers can be
 * painted on top of outer ones.
 */
function paintTree(text, options) {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const root = parseWildcardText(text);
    assignColors(root, opts.coloring);
    const colorOf = makeColorSource(opts);

    const colorsText = opts.style === "Text color" || opts.style === "Background + text color";
    const fillsBackground = opts.style === "Background" || opts.style === "Background + text color";
    const alpha = Math.max(0.05, Math.min(1, Number(opts.intensity) / 100 || DEFAULT_OPTIONS.intensity / 100));
    const bgAlpha = opts.style === "Background + text color" ? alpha * 0.6 : alpha;

    const visit = (node, inherited, layer) => {
        for (const child of node.children) {
            let paint = {};
            let rgb = inherited;
            if (child.color !== undefined) {
                rgb = colorOf(child.color);
                paint = blockPaint(rgb, opts);
            } else if (child.type === "delim" && opts.emphasizeSyntax && inherited) {
                // Syntax characters get a faint extra layer of their block's
                // color: just enough to spot, without drowning the text.
                paint.background = rgba(inherited, (fillsBackground ? bgAlpha : alpha) * 0.3);
            } else if (child.type === "comment") {
                paint.background = rgba(COMMENT_RGB, 0.2);
                if (colorsText) paint.color = rgba(COMMENT_RGB, 1);
            } else if (child.type === "varname" && inherited && !fillsBackground) {
                paint.background = rgba(inherited, alpha * 0.6);
            }
            if ((child.error || child.type === "error") && opts.markErrors) {
                paint.wavy = ERROR_COLOR;
                if (child.type === "error") paint.background = rgba([255, 77, 79], 0.35);
            }
            child.paint = Object.keys(paint).length ? paint : null;
            child.layer = layer;
            visit(child, rgb, layer + 1);
        }
    };
    visit(root, null, 1);
    return { root, colorsText };
}

/** How a colored block is painted in the chosen highlight style. */
function blockPaint(rgb, opts) {
    const colorsText = opts.style === "Text color" || opts.style === "Background + text color";
    const fillsBackground = opts.style === "Background" || opts.style === "Background + text color";
    const alpha = Math.max(0.05, Math.min(1, Number(opts.intensity) / 100 || DEFAULT_OPTIONS.intensity / 100));
    const paint = { rounded: true };
    if (fillsBackground) paint.background = rgba(rgb, opts.style === "Background + text color" ? alpha * 0.6 : alpha);
    if (colorsText) paint.color = rgba(rgb, 1);
    if (opts.style === "Underline") paint.underline = rgba(rgb, 1);
    return paint;
}

/**
 * Render a processed prompt for the node's Preview, colored by where each
 * part came from. `source` is the template the processor ran on, and
 * `segments` is the processor's tree of [{ text } | { key, children }],
 * where key is "c<offset>" (a {…} block), "w<offset>" (a __wildcard__) or
 * "v<name>" (a variable). Each part gets the color that source has in the
 * template's own highlighting. Hovering a part shows the source it came from.
 */
export function renderPreviewHTML(source, segments, options = {}) {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const root = parseWildcardText(source);
    assignColors(root, opts.coloring);
    const colorOf = makeColorSource(opts);

    const byKey = new Map();
    walk(root, (node) => {
        if (node.color === undefined) return;
        if (node.type === "choice") byKey.set(`c${node.start}`, node);
        else if (node.type === "wildcard") byKey.set(`w${node.start}`, node);
        else if (node.type === "vardef" && !byKey.has(`v${node.name}`)) byKey.set(`v${node.name}`, node);
    });

    const plainText = (items) => (items || []).map((item) => item.text ?? plainText(item.children)).join("");
    const render = (items) => {
        let html = "";
        for (const item of items || []) {
            if (typeof item.text === "string") {
                html += escapeHTML(item.text);
                continue;
            }
            const node = byKey.get(item.key);
            // A variable's text is shown in the variable's color only, so it
            // links clearly to its ${name} uses in the template.
            const inner = node?.type === "vardef" ? escapeHTML(plainText(item.children)) : render(item.children);
            if (!node) {
                html += inner;
                continue;
            }
            const origin = source.slice(node.start, node.end);
            const title = origin.length > 200 ? `${origin.slice(0, 200)}…` : origin;
            const css = paintToSpanCSS(blockPaint(colorOf(node.color), opts));
            html += `<span class="mnm-wh-from" style="${css}" title="${escapeHTML(title)}">${inner}</span>`;
        }
        return html;
    };
    return render(segments);
}

/** Inline CSS for a node's paint, for the span-based renderer. */
function paintToSpanCSS(paint) {
    const css = [];
    if (paint.background) css.push(`background-color:${paint.background}`);
    if (paint.color) css.push(`color:${paint.color}`);
    if (paint.underline) css.push(`box-shadow:inset 0 -2px 0 ${paint.underline}`);
    if (paint.rounded) css.push("border-radius:3px");
    if (paint.wavy) css.push(`text-decoration:underline wavy ${paint.wavy}`, "text-decoration-skip-ink:none");
    return css.join(";");
}

/** CSS for a node's paint as a ::highlight() rule (a subset of properties). */
function paintToHighlightCSS(paint) {
    const css = [];
    if (paint.background) css.push(`background-color:${paint.background}`);
    if (paint.color) css.push(`color:${paint.color}`);
    if (paint.wavy) css.push(`text-decoration:underline wavy ${paint.wavy}`);
    else if (paint.underline) css.push(`text-decoration:underline solid ${paint.underline} 2px`);
    return css.join(";");
}

/** The trailing text the backdrop needs: a final newline has no height in a div. */
function trailingFiller(text) {
    return text.endsWith("\n") || !text ? " " : "";
}

/**
 * Render text as highlighted HTML. The output keeps every character of text
 * in place (only wrapped in spans). `baseColor` is the textarea's own text
 * color, used for plain text when the style colors text.
 *
 * Spans can shift line wrapping by a fraction of a pixel, so the backdrop
 * prefers highlight ranges (computeWildcardRanges) and uses this only when
 * the browser has no CSS Custom Highlight API.
 */
export function renderWildcardHTML(text, options = {}, baseColor = "inherit") {
    const { root, colorsText } = paintTree(text, options);

    /** Render a node's children and the plain text between them as HTML. */
    function render(node) {
        let html = "";
        let pos = node.start;
        for (const child of node.children) {
            if (child.start > pos) html += escapeHTML(text.slice(pos, child.start));
            const css = child.paint ? paintToSpanCSS(child.paint) : "";
            const title = child.error || child.message;
            html += `<span class="mnm-wh-${child.type}"${css ? ` style="${css}"` : ""}${title ? ` data-error="${escapeHTML(title)}"` : ""}>`;
            html += render(child);
            html += "</span>";
            pos = child.end;
        }
        if (node.end > pos) html += escapeHTML(text.slice(pos, node.end));
        return html;
    }

    const html = render(root) + trailingFiller(text);
    return colorsText ? `<span style="color:${baseColor}">${html}</span>` : html;
}

/**
 * The highlighted ranges of text, as [{ start, end, css, layer }] where css
 * is a ::highlight() rule body and layer is the paint order (higher on top).
 */
export function computeWildcardRanges(text, options = {}) {
    const { root } = paintTree(text, options);
    const ranges = [];
    const visit = (node) => {
        for (const child of node.children) {
            if (child.paint && child.end > child.start) {
                const css = paintToHighlightCSS(child.paint);
                if (css) ranges.push({ start: child.start, end: child.end, css, layer: child.layer });
            }
            visit(child);
        }
    };
    visit(root);
    return ranges;
}

// ---------------------------------------------------------------------------
// CSS Custom Highlight registry
// ---------------------------------------------------------------------------

// Highlights color ranges of a plain text node without wrapping it in
// elements, so the backdrop wraps lines exactly like the textarea. Each
// distinct style is one named Highlight shared by all highlighters.
const highlightStyles = new Map();
let highlightSheet = null;

/** Whether this browser supports the CSS Custom Highlight API. */
function supportsHighlights() {
    return typeof CSS !== "undefined" && !!CSS.highlights && typeof Highlight === "function";
}

/** The shared Highlight for a style, created and registered on first use. */
function highlightFor(css, layer) {
    const key = `${layer}|${css}`;
    let highlight = highlightStyles.get(key);
    if (!highlight) {
        if (!highlightSheet) {
            const style = document.createElement("style");
            style.dataset.mnemic = "wildcard-highlight";
            document.head.appendChild(style);
            highlightSheet = style.sheet;
        }
        const name = `mnm-wh-${highlightStyles.size}`;
        highlight = new Highlight();
        highlight.priority = layer;
        CSS.highlights.set(name, highlight);
        highlightSheet.insertRule(`::highlight(${name}){${css}}`, highlightSheet.cssRules.length);
        highlightStyles.set(key, highlight);
    }
    return highlight;
}

// ---------------------------------------------------------------------------
// Textarea backdrop
// ---------------------------------------------------------------------------

const COPIED_STYLES = [
    "fontFamily", "fontSize", "fontWeight", "fontStyle", "fontVariant", "fontStretch",
    "fontKerning", "fontFeatureSettings", "fontVariationSettings",
    "letterSpacing", "wordSpacing", "lineHeight", "textTransform", "textIndent",
    "textAlign", "direction", "tabSize", "whiteSpace", "wordBreak", "overflowWrap",
    "hyphens",
    "paddingTop", "paddingLeft", "paddingBottom",
    "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
    "borderTopLeftRadius", "borderTopRightRadius", "borderBottomLeftRadius", "borderBottomRightRadius",
];

const highlighters = new Set();
let optionsProvider = () => DEFAULT_OPTIONS;

/** Set the function that returns the current highlight options (from settings). */
export function setWildcardHighlightOptionsProvider(fn) {
    optionsProvider = fn;
    refreshWildcardHighlighters();
}

const refreshListeners = new Set();

/** Call fn whenever the highlighters are refreshed (e.g. to redraw previews). */
export function onWildcardHighlightRefresh(fn) {
    refreshListeners.add(fn);
}

/** Re-render every highlighter, e.g. after a setting changed. */
export function refreshWildcardHighlighters() {
    for (const highlighter of highlighters) highlighter.refresh();
    for (const fn of refreshListeners) fn();
}

/** Current highlight options from the settings, falling back to the defaults. */
function readOptions() {
    try {
        return { ...DEFAULT_OPTIONS, ...optionsProvider() };
    } catch {
        return { ...DEFAULT_OPTIONS };
    }
}

/** Paints wildcard highlighting behind one textarea and keeps it in sync. */
export class WildcardHighlighter {
    /** @param {HTMLTextAreaElement} textarea */
    constructor(textarea) {
        this.textarea = textarea;
        this.backdrop = document.createElement("div");
        this.backdrop.className = "mnm-wildcard-highlight";
        this.backdrop.setAttribute("aria-hidden", "true");
        Object.assign(this.backdrop.style, {
            position: "absolute",
            pointerEvents: "none",
            overflow: "hidden",
            margin: "0",
            boxSizing: "border-box",
            borderStyle: "solid",
            borderColor: "transparent",
            zIndex: "0",
        });
        // The textarea itself is made transparent, so its theme colors are
        // read from this hidden twin. That keeps them live when the theme
        // or palette changes.
        this.probe = document.createElement("textarea");
        this.probe.setAttribute("aria-hidden", "true");
        this.probe.tabIndex = -1;
        this.probe.style.display = "none";
        this.probe.dataset.mnmProbe = "1";

        this.rendered = false;
        this.lastText = null;
        this.ranges = [];
        this.styleKey = null;
        this.active = false;
        this.saved = null;

        this.onInput = () => this.update();
        this.onScroll = () => this.syncScroll();
        textarea.addEventListener("input", this.onInput);
        textarea.addEventListener("scroll", this.onScroll);

        this.resizeObserver = typeof ResizeObserver !== "undefined"
            ? new ResizeObserver(() => this.syncGeometry())
            : null;
        this.resizeObserver?.observe(textarea);
        this.mutationObserver = typeof MutationObserver !== "undefined"
            ? new MutationObserver(() => this.update())
            : null;
        this.mutationObserver?.observe(textarea, { attributes: true, attributeFilter: ["style", "class", "hidden"] });

        highlighters.add(this);
        this.refresh();
    }

    /** Re-apply settings and re-render. */
    refresh() {
        this.options = readOptions();
        this.rendered = false;
        this.styleKey = null;
        if (!this.options.enabled) {
            this.deactivate();
            return;
        }
        if (!this.saved) {
            const style = this.textarea.style;
            this.saved = {
                background: style.background,
                color: style.color,
                caretColor: style.caretColor,
                position: style.position,
                zIndex: style.zIndex,
            };
        }
        this.active = true;
        this.update();
    }

    /** Remove the backdrop and restore the textarea's own styles. */
    deactivate() {
        if (this.saved) {
            Object.assign(this.textarea.style, this.saved);
            this.saved = null;
        }
        this.clearRanges();
        this.backdrop.textContent = "";
        this.backdrop.remove();
        this.probe.remove();
        this.active = false;
    }

    /**
     * Keep the backdrop right behind the textarea. The textarea may be created
     * detached and mounted later (ComfyUI does this), so nothing is read
     * from it until it is in the document. Returns false until then.
     */
    ensureMounted() {
        const ta = this.textarea;
        const parent = ta.parentElement;
        if (!this.active || !ta.isConnected || !parent) return false;
        if (this.backdrop.parentElement !== parent || this.backdrop.nextSibling !== ta) {
            if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
            parent.insertBefore(this.probe, ta);
            parent.insertBefore(this.backdrop, ta);
            this.styleKey = null;
        }
        this.syncStyles();
        return true;
    }

    /** Re-apply colors and layout if the theme, font or textarea styles changed. */
    syncStyles() {
        const ta = this.textarea;
        if (this.probe.className !== ta.className) this.probe.className = ta.className;
        this.probe.style.background = this.saved.background;
        this.probe.style.color = this.saved.color;
        const theme = getComputedStyle(this.probe);
        const cs = getComputedStyle(ta);
        const key = [
            theme.backgroundColor, theme.backgroundImage, theme.color,
            cs.font, cs.lineHeight, cs.letterSpacing, cs.padding, cs.borderWidth,
            cs.position, cs.display, cs.visibility, ta.className, this.options.style,
        ].join("|");
        if (key === this.styleKey) return;
        this.styleKey = key;

        this.baseColor = theme.color;
        this.backdrop.style.backgroundColor = theme.backgroundColor;
        this.backdrop.style.backgroundImage = theme.backgroundImage;
        ta.style.background = "transparent";
        const colorsText = this.options.style === "Text color" || this.options.style === "Background + text color";
        ta.style.color = colorsText ? "transparent" : this.saved.color;
        ta.style.caretColor = colorsText ? this.baseColor : this.saved.caretColor;
        // In background styles the textarea draws the text; the backdrop's
        // copy only carries the highlights, so it stays invisible.
        this.backdrop.style.color = colorsText ? this.baseColor : "transparent";
        // The textarea must be positioned to paint above the backdrop.
        if (cs.position === "static") ta.style.position = "relative";
        if (!ta.style.zIndex) ta.style.zIndex = "1";

        this.rendered = false;
        this.syncGeometry();
    }

    /** Re-render if the text or styles changed. Cheap enough to call on every draw. */
    update() {
        if (!this.ensureMounted()) return;
        const text = this.textarea.value;
        if (text === this.lastText && this.rendered) return;
        try {
            this.render(text);
        } catch (err) {
            // Never leave stale highlighting behind; show the text plainly.
            console.warn("[MNeMiC] Wildcard highlighting failed:", err);
            this.clearRanges();
            this.backdrop.textContent = text + trailingFiller(text);
        }
        this.lastText = text;
        this.rendered = true;
        this.syncGeometry();
    }

    /** Paint the text into the backdrop, with highlight ranges or spans. */
    render(text) {
        this.clearRanges();
        if (!supportsHighlights()) {
            this.backdrop.innerHTML = renderWildcardHTML(text, this.options, this.baseColor);
            return;
        }
        this.backdrop.textContent = text + trailingFiller(text);
        const node = this.backdrop.firstChild;
        for (const { start, end, css, layer } of computeWildcardRanges(text, this.options)) {
            const range = new Range();
            range.setStart(node, start);
            range.setEnd(node, end);
            const highlight = highlightFor(css, layer);
            highlight.add(range);
            this.ranges.push([highlight, range]);
        }
    }

    /** Remove this backdrop's ranges from the shared highlights. */
    clearRanges() {
        for (const [highlight, range] of this.ranges) highlight.delete(range);
        this.ranges = [];
    }

    /** Copy the textarea's font, padding, size and position onto the backdrop. */
    syncGeometry() {
        if (!this.active || !this.backdrop.parentElement || !this.textarea.isConnected) return;
        const ta = this.textarea;
        const cs = getComputedStyle(ta);
        const bd = this.backdrop.style;
        for (const prop of COPIED_STYLES) bd[prop] = cs[prop];

        // Use the exact (possibly fractional) border-box size. offsetWidth is
        // rounded, and even half a pixel can make a line wrap differently.
        const borderX = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
        const borderY = parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth);
        const paddingX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
        const paddingY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
        const contentBox = cs.boxSizing !== "border-box";
        const width = parseFloat(cs.width) + (contentBox ? paddingX + borderX : 0);
        const height = parseFloat(cs.height) + (contentBox ? paddingY + borderY : 0);

        // The textarea's scrollbar narrows its text area; mirror that with
        // padding. Scrollbars are whole pixels, so round away the rounding
        // error in offsetWidth/clientWidth.
        const scrollbar = Math.max(0, Math.round(ta.offsetWidth - ta.clientWidth - borderX));
        bd.paddingRight = `${parseFloat(cs.paddingRight) + scrollbar}px`;

        bd.left = `${ta.offsetLeft}px`;
        bd.top = `${ta.offsetTop}px`;
        bd.width = `${width}px`;
        bd.height = `${height}px`;
        bd.transform = cs.transform === "none" ? "" : cs.transform;
        bd.transformOrigin = cs.transformOrigin;
        bd.display = cs.display === "none" ? "none" : "block";
        bd.visibility = cs.visibility;
        bd.opacity = cs.opacity;
        this.syncScroll();
    }

    /** Scroll the backdrop to match the textarea. */
    syncScroll() {
        this.backdrop.scrollTop = this.textarea.scrollTop;
        this.backdrop.scrollLeft = this.textarea.scrollLeft;
    }

    /** Detach for good: remove listeners, observers and the backdrop. */
    destroy() {
        this.textarea.removeEventListener("input", this.onInput);
        this.textarea.removeEventListener("scroll", this.onScroll);
        this.resizeObserver?.disconnect();
        this.mutationObserver?.disconnect();
        this.deactivate();
        highlighters.delete(this);
    }
}

/** Find the <textarea> behind a ComfyUI multiline STRING widget. */
export function getWidgetTextarea(widget) {
    for (const el of [widget?.inputEl, widget?.element]) {
        if (!el) continue;
        if (el instanceof HTMLTextAreaElement) return el;
        const inner = el.querySelector?.("textarea");
        if (inner) return inner;
    }
    return null;
}
