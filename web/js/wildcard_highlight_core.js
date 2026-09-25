// Wildcard syntax highlighting for multiline text widgets.
//
// This module has no ComfyUI imports so it can be reused by any node (and
// tested outside ComfyUI). It provides:
//   - parseWildcardText(text): a syntax tree of the wildcard template
//   - renderWildcardHTML(text, options): highlighted HTML for that template
//   - WildcardHighlighter: draws the highlighting behind a <textarea>
//
// The highlighter works as a "backdrop": a div with exactly the same font,
// padding and size as the textarea is placed behind it, and the textarea is
// made transparent. The textarea stays the real editor (caret, selection,
// undo and copy/paste all behave as normal); the backdrop only paints colors.
// Because of that the backdrop must never change text layout: no bold, no
// padding, no borders on highlighted spans. Only colors, backgrounds,
// box-shadows and text decorations are used.

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

const WILDCARD_RE = /__([a-zA-Z0-9_./\\*?\[\] -]+?)__/y;
const TAG_RE = /<([a-zA-Z_][a-zA-Z0-9_]*):[^<>\n]*>/y;
const COUNT_RE = /\d+(?:-\d+)?\$\$/y;
const WEIGHT_RE = /\d+(?:\.\d+)?::/y;

function matchAt(re, text, index) {
    re.lastIndex = index;
    return re.exec(text);
}

function delim(start, end, kind) {
    return { type: "delim", kind, start, end, children: [] };
}

/**
 * Parse a wildcard template into a tree of nodes. Every node has
 * { type, start, end, children } where start/end are offsets into text.
 *
 * Node types:
 *   choice   {a|b|c} inline choice block (any depth); has `depth`
 *   option   one option of a choice block; has `index`
 *   vardef   ${name=!value} variable definition; has `name`
 *   varuse   ${name} variable use; has `name`
 *   varname  the name inside a vardef
 *   wildcard __file__ wildcard; has `name`
 *   tag      <name:value> property/LoRA tag; has `name`
 *   comment  # comment inside a choice block
 *   delim    syntax characters; has `kind` (brace, pipe, weight, count, sep, var)
 *   error    stray or unclosed syntax characters; has `message`
 * Variable uses without a definition get `error` set.
 */
export function parseWildcardText(text) {
    const n = text.length;
    // Blocks that never close, by start offset. Whether a block closes does
    // not depend on where it is nested, so each one is parsed only once;
    // without this, nested unclosed blocks take exponential time.
    const failed = new Map();

    function parseSequence(i, mode, depth) {
        // mode: "top" | "option" (inside a choice) | "value" (inside a vardef)
        const children = [];
        while (i < n) {
            const c = text[i];
            if (c === "$" && text[i + 1] === "{") {
                const node = failed.get(i) ?? parseVariable(i, depth);
                if (node) {
                    if (node.error) failed.set(i, node);
                    children.push(node.error ? strayError(node) : node);
                    i = node.error ? i + 2 : node.end;
                    continue;
                }
            } else if (c === "{") {
                const node = failed.get(i) ?? parseChoice(i, depth + 1);
                if (node.error) failed.set(i, node);
                children.push(node.error ? strayError(node) : node);
                i = node.error ? i + 1 : node.end;
                continue;
            } else if (c === "}") {
                if (mode !== "top") break;
                children.push({ type: "error", start: i, end: i + 1, message: "Unmatched }", children: [] });
                i++;
                continue;
            } else if (c === "|" && mode === "option") {
                break;
            } else if (c === "#" && mode === "option") {
                let j = i;
                while (j < n && text[j] !== "\n" && text[j] !== "}") j++;
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
                const m = matchAt(TAG_RE, text, i);
                if (m) {
                    children.push({ type: "tag", name: m[1].toLowerCase(), start: i, end: i + m[0].length, children: [] });
                    i += m[0].length;
                    continue;
                }
            }
            i++;
        }
        return { children, end: i };
    }

    // An unclosed block only flags its opening characters; the text after
    // it is parsed again as normal text (the processor leaves it as-is too).
    function strayError(node) {
        const length = node.type === "vardef" ? 2 : 1;
        return { type: "error", start: node.start, end: node.start + length, message: node.error, children: [] };
    }

    function parseChoice(start, depth) {
        const node = { type: "choice", depth, start, end: n, children: [delim(start, start + 1, "brace")] };
        let i = start + 1;

        // Optional count prefix (N$$ or N-M$$), then an optional custom separator (sep$$).
        const count = matchAt(COUNT_RE, text, i);
        if (count) {
            node.children.push(delim(i, i + count[0].length, "count"));
            i += count[0].length;
            const sepEnd = text.indexOf("$$", i);
            if (sepEnd !== -1) {
                let stop = n;
                for (const ch of "|{}") {
                    const k = text.indexOf(ch, i);
                    if (k !== -1 && k < stop) stop = k;
                }
                if (sepEnd < stop) {
                    node.children.push(delim(i, sepEnd + 2, "sep"));
                    i = sepEnd + 2;
                }
            }
        }

        let index = 0;
        while (true) {
            const option = { type: "option", index: index++, start: i, end: i, children: [] };
            const weight = matchAt(WEIGHT_RE, text, i);
            if (weight) {
                option.children.push(delim(i, i + weight[0].length, "weight"));
                i += weight[0].length;
            }
            const seq = parseSequence(i, "option", depth);
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

    function parseVariable(start, depth) {
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
        const node = {
            type: "vardef",
            name: rawName.trim(),
            start,
            end: n,
            children: [
                delim(start, start + 2, "var"),
                { type: "varname", start: start + 2, end: j, children: [] },
                delim(j, j + 2, "var"),
            ],
        };
        const seq = parseSequence(j + 2, "value", depth);
        node.children.push(...seq.children);
        if (text[seq.end] === "}") {
            node.children.push(delim(seq.end, seq.end + 1, "var"));
            node.end = seq.end + 1;
        } else {
            node.error = "Unclosed ${";
        }
        return node;
    }

    const root = { type: "root", start: 0, end: n, children: parseSequence(0, "top", 0).children };

    // Link variable definitions and uses.
    const defined = new Set();
    walk(root, (node) => {
        if (node.type === "vardef") defined.add(node.name);
    });
    walk(root, (node) => {
        if (node.type === "varuse" && !defined.has(node.name)) node.error = "Undefined variable";
    });

    return root;
}

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
export const PALETTES = {
    Pastel: { s: 75, l: 82 },
    Light: { s: 90, l: 70 },
    Vivid: { s: 85, l: 55 },
    Dark: { s: 60, l: 32 },
    Muted: { s: 25, l: 55 },
};

export const HIGHLIGHT_STYLES = ["Background", "Text color", "Background + text color", "Underline"];
export const COLORING_MODES = ["Each block", "Nesting depth"];

export const DEFAULT_OPTIONS = {
    enabled: true,
    palette: "Pastel",
    style: "Background",
    coloring: "Each block",
    intensity: 35,
    emphasizeSyntax: true,
    markErrors: true,
    customColors: "",
};

const HUE_START = 200;
const GOLDEN_ANGLE = 137.508;

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

function hslToRgb(h, s, l) {
    s /= 100;
    l /= 100;
    const k = (x) => (x + h / 30) % 12;
    const a = s * Math.min(l, 1 - l);
    const f = (x) => l - a * Math.max(-1, Math.min(k(x) - 3, Math.min(9 - k(x), 1)));
    return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}

function makeColorSource(options) {
    const custom = options.palette === "Custom"
        ? String(options.customColors || "").split(/[\s,;]+/).map(parseColor).filter(Boolean)
        : [];
    if (custom.length) return (index) => custom[index % custom.length];
    const { s, l } = PALETTES[options.palette] || PALETTES.Pastel;
    return (index) => hslToRgb((HUE_START + index * GOLDEN_ANGLE) % 360, s, l);
}

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
    walk(root, (node) => {
        switch (node.type) {
            case "choice":
                node.color = byDepth ? node.depth - 1 : next++;
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
    });
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

const ERROR_COLOR = "#ff4d4f";
const COMMENT_RGB = [128, 128, 128];

function escapeHTML(text) {
    return text.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
}

/**
 * Render text as highlighted HTML. The output keeps every character of text
 * in place (only wrapped in spans), so it lines up with the textarea.
 * `baseColor` is the textarea's own text color, used for plain text when the
 * style colors text.
 */
export function renderWildcardHTML(text, options = {}, baseColor = "inherit") {
    const opts = { ...DEFAULT_OPTIONS, ...options };
    const root = parseWildcardText(text);
    assignColors(root, opts.coloring);
    const colorOf = makeColorSource(opts);

    const colorsText = opts.style === "Text color" || opts.style === "Background + text color";
    const fillsBackground = opts.style === "Background" || opts.style === "Background + text color";
    const alpha = Math.max(0.05, Math.min(1, Number(opts.intensity) / 100 || DEFAULT_OPTIONS.intensity / 100));
    const bgAlpha = opts.style === "Background + text color" ? alpha * 0.6 : alpha;

    function styleFor(node, inherited) {
        const css = [];
        let rgb = inherited;

        if (node.color !== undefined) {
            rgb = colorOf(node.color);
            if (fillsBackground) css.push(`background-color:${rgba(rgb, bgAlpha)}`);
            if (colorsText) css.push(`color:${rgba(rgb, 1)}`);
            if (opts.style === "Underline") css.push(`box-shadow:inset 0 -2px 0 ${rgba(rgb, 1)}`);
            css.push("border-radius:3px");
        } else if (node.type === "delim" && opts.emphasizeSyntax && inherited) {
            // Syntax characters get a second layer of their block's color.
            if (opts.style === "Underline") css.push(`background-color:${rgba(inherited, alpha)}`);
            else css.push(`background-color:${rgba(inherited, Math.min(1, bgAlpha + 0.15))}`);
            css.push("border-radius:2px");
        } else if (node.type === "comment") {
            css.push(`background-color:${rgba(COMMENT_RGB, 0.2)}`);
            if (colorsText) css.push(`color:${rgba(COMMENT_RGB, 1)}`);
        } else if (node.type === "varname" && inherited && !fillsBackground) {
            css.push(`background-color:${rgba(inherited, alpha * 0.6)}`);
        }

        if ((node.error || node.type === "error") && opts.markErrors) {
            css.push(`text-decoration:underline wavy ${ERROR_COLOR}`, "text-decoration-skip-ink:none");
            if (node.type === "error") css.push(`background-color:${rgba([255, 77, 79], 0.35)}`);
        }
        return { css: css.join(";"), rgb };
    }

    function render(node, inherited) {
        let html = "";
        let pos = node.start;
        for (const child of node.children) {
            if (child.start > pos) html += escapeHTML(text.slice(pos, child.start));
            const { css, rgb } = styleFor(child, inherited);
            const title = child.error || child.message;
            html += `<span class="mnm-wh-${child.type}"${css ? ` style="${css}"` : ""}${title ? ` data-error="${escapeHTML(title)}"` : ""}>`;
            html += render(child, rgb);
            html += "</span>";
            pos = child.end;
        }
        if (node.end > pos) html += escapeHTML(text.slice(pos, node.end));
        return html;
    }

    let html = render(root, null);
    // A trailing newline has no height in a div, but it does in a textarea.
    if (text.endsWith("\n") || !text) html += " ";
    return colorsText ? `<span style="color:${baseColor}">${html}</span>` : html;
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

/** Re-render every highlighter, e.g. after a setting changed. */
export function refreshWildcardHighlighters() {
    for (const highlighter of highlighters) highlighter.refresh();
}

function readOptions() {
    try {
        return { ...DEFAULT_OPTIONS, ...optionsProvider() };
    } catch {
        return { ...DEFAULT_OPTIONS };
    }
}

export class WildcardHighlighter {
    /**
     * @param {HTMLTextAreaElement} textarea
     * @param {object} [options] Fixed options for this textarea, overriding the settings.
     */
    constructor(textarea, options = null) {
        this.textarea = textarea;
        this.fixedOptions = options;
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
        this.lastHTML = null;
        this.lastText = null;
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
            ? new MutationObserver(() => this.syncGeometry())
            : null;
        this.mutationObserver?.observe(textarea, { attributes: true, attributeFilter: ["style", "class", "hidden"] });

        highlighters.add(this);
        this.refresh();
    }

    /** Re-apply settings and re-render. */
    refresh() {
        this.options = { ...readOptions(), ...this.fixedOptions };
        this.lastHTML = null;
        if (!this.options.enabled) {
            this.deactivate();
            return;
        }
        this.activate();
        this.update();
    }

    activate() {
        const ta = this.textarea;
        if (!this.saved) {
            this.saved = {
                background: ta.style.background,
                color: ta.style.color,
                caretColor: ta.style.caretColor,
                position: ta.style.position,
                zIndex: ta.style.zIndex,
            };
        }
        // Read the textarea's natural colors with our overrides removed.
        ta.style.background = this.saved.background;
        ta.style.color = this.saved.color;
        const computed = getComputedStyle(ta);
        this.baseColor = computed.color;
        this.backdrop.style.backgroundColor = computed.backgroundColor;
        this.backdrop.style.backgroundImage = computed.backgroundImage;

        ta.style.background = "transparent";
        const colorsText = this.options.style === "Text color" || this.options.style === "Background + text color";
        if (colorsText) {
            ta.style.color = "transparent";
            ta.style.caretColor = this.baseColor;
        } else {
            ta.style.caretColor = this.saved.caretColor;
        }
        if (computed.position === "static") ta.style.position = "relative";
        if (!ta.style.zIndex) ta.style.zIndex = "1";
        this.active = true;
        this.ensureMounted();
    }

    deactivate() {
        if (this.saved) {
            Object.assign(this.textarea.style, this.saved);
            this.saved = null;
        }
        this.backdrop.remove();
        this.active = false;
    }

    /** Make sure the backdrop sits right behind the textarea. Cheap to call often. */
    ensureMounted() {
        if (!this.active) return false;
        const parent = this.textarea.parentElement;
        if (!parent) return false;
        if (this.backdrop.parentElement !== parent || this.backdrop.nextSibling !== this.textarea) {
            if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
            parent.insertBefore(this.backdrop, this.textarea);
            this.syncGeometry();
        }
        return true;
    }

    /** Re-render if the text changed (also catches programmatic value changes). */
    update() {
        if (!this.active) return;
        this.ensureMounted();
        const text = this.textarea.value;
        if (text === this.lastText && this.lastHTML !== null) return;
        this.lastText = text;
        const html = renderWildcardHTML(text, this.options, this.baseColor);
        if (html !== this.lastHTML) {
            this.backdrop.innerHTML = html;
            this.lastHTML = html;
        }
        this.syncGeometry();
    }

    syncGeometry() {
        if (!this.active || !this.backdrop.parentElement) return;
        const ta = this.textarea;
        const cs = getComputedStyle(ta);
        const bd = this.backdrop.style;
        for (const prop of COPIED_STYLES) bd[prop] = cs[prop];

        // The textarea's scrollbar narrows its text area; mirror that with padding.
        const borderX = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
        const scrollbar = Math.max(0, ta.offsetWidth - ta.clientWidth - borderX);
        bd.paddingRight = `${parseFloat(cs.paddingRight) + scrollbar}px`;

        bd.left = `${ta.offsetLeft}px`;
        bd.top = `${ta.offsetTop}px`;
        bd.width = `${ta.offsetWidth}px`;
        bd.height = `${ta.offsetHeight}px`;
        bd.transform = cs.transform === "none" ? "" : cs.transform;
        bd.transformOrigin = cs.transformOrigin;
        bd.display = cs.display === "none" ? "none" : "block";
        bd.visibility = cs.visibility;
        bd.opacity = cs.opacity;
        this.syncScroll();
    }

    syncScroll() {
        this.backdrop.scrollTop = this.textarea.scrollTop;
        this.backdrop.scrollLeft = this.textarea.scrollLeft;
    }

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
