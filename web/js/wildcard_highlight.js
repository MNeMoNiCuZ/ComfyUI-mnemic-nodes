import { app } from "../../../scripts/app.js";
import {
    WildcardHighlighter,
    getWidgetTextarea,
    onWildcardHighlightRefresh,
    renderPreviewHTML,
    setWildcardHighlightOptionsProvider,
} from "./wildcard_highlight_core.js";

// Every node + text widget that accepts wildcard syntax. To add wildcard
// highlighting to another node, add its node id and widget name(s) here, or
// call attachWildcardHighlight(node, widgetName) from that node's own script.
export const WILDCARD_TEXT_WIDGETS = {
    MNeMiC_WildcardProcessor: ["wildcard_string"],
    MNeMiC_WildcardProcessorAdvanced: ["wildcard_string"],
    MNeMiC_BatchWildcardSampler: ["text", "negative"],
    MNeMiC_PromptPropertyExtractor: ["input_string"],
};

// Nodes that get a Preview section showing the resolved prompt, colored by
// where each part came from. Maps node id to the widget holding the template.
const PREVIEW_NODES = {
    MNeMiC_WildcardProcessor: "wildcard_string",
    MNeMiC_WildcardProcessorAdvanced: "wildcard_string",
};

const SETTING_PREFIX = "MNeMiC.WildcardHighlight.";

/** Read one of the MNeMiC.WildcardHighlight.* settings. */
function getSetting(name, fallback) {
    const id = SETTING_PREFIX + name;
    const value = app.extensionManager?.setting?.get?.(id) ?? app.ui?.settings?.getSettingValue?.(id);
    return value ?? fallback;
}

/** The current highlight options from the settings. */
function highlightOptions() {
    return {
        enabled: getSetting("Enabled", true),
        palette: getSetting("Palette", "Dark"),
        style: getSetting("Style", "Background"),
        coloring: getSetting("Coloring", "Each block"),
        intensity: getSetting("Intensity", 35),
        emphasizeSyntax: getSetting("EmphasizeSyntax", true),
        markErrors: getSetting("MarkErrors", true),
        customColors: getSetting("CustomColors", ""),
        tooltipLength: getSetting("TooltipLength", 800),
    };
}

setWildcardHighlightOptionsProvider(highlightOptions);

// ---------------------------------------------------------------------------
// Finding the textarea
// ---------------------------------------------------------------------------

/**
 * The <textarea> currently showing a node's widget. The classic canvas uses
 * the widget's own DOM element. The Vue node renderer ("Nodes 2.0") draws
 * its own <textarea> inside the node's element instead, linked to a <label>
 * with the widget's name, and leaves the widget's element unmounted.
 */
function findTextarea(node, widgetName) {
    const widget = node.widgets?.find((w) => w.name === widgetName);
    if (!widget) return null;

    const container = document.querySelector(`[data-node-id="${CSS.escape(String(node.id))}"]`);
    if (container) {
        const label = widget.label || widget.name;
        for (const el of container.querySelectorAll("label[for]")) {
            if (el.textContent.trim() !== label) continue;
            const target = document.getElementById(el.htmlFor);
            if (target instanceof HTMLTextAreaElement) return target;
        }
        // No label (some layouts hide it): match by order among the node's
        // multiline widgets.
        const areas = [...container.querySelectorAll("textarea")].filter((t) => !t.dataset.mnmProbe);
        const multiline = node.widgets.filter((w) => w.type === "customtext");
        const index = multiline.indexOf(widget);
        if (index !== -1 && areas.length === multiline.length) return areas[index];
    }

    const classic = getWidgetTextarea(widget);
    return classic?.isConnected ? classic : null;
}

// ---------------------------------------------------------------------------
// Attaching highlighters
// ---------------------------------------------------------------------------

const attachments = new Set();
let frame = 0;
let loopRunning = false;

/** Keep every highlighter on the right textarea and up to date. */
function tick() {
    frame++;
    for (const attachment of attachments) {
        const { node, widgetName } = attachment;
        if (!node.graph) {
            detach(attachment);
            continue;
        }
        // The textarea can be swapped (switching renderers, re-mounting);
        // look for it again a few times a second.
        if (!attachment.highlighter || frame % 15 === 0) {
            const textarea = findTextarea(node, widgetName);
            if (textarea !== attachment.textarea) {
                attachment.highlighter?.destroy();
                attachment.textarea = textarea;
                attachment.highlighter = textarea ? new WildcardHighlighter(textarea) : null;
            }
        }
        // Also catches values set from code, which fire no input event.
        attachment.highlighter?.update();
    }
    if (attachments.size) requestAnimationFrame(tick);
    else loopRunning = false;
}

/** Stop highlighting one widget. */
function detach(attachment) {
    attachment.highlighter?.destroy();
    attachments.delete(attachment);
}

/**
 * Attach wildcard highlighting to one multiline text widget of a node.
 * Safe to call more than once for the same widget.
 */
export function attachWildcardHighlight(node, widgetName) {
    for (const attachment of attachments) {
        if (attachment.node === node && attachment.widgetName === widgetName) return;
    }
    attachments.add({ node, widgetName, textarea: null, highlighter: null });
    if (!loopRunning) {
        loopRunning = true;
        requestAnimationFrame(tick);
    }
}

/** Stop highlighting every widget of a node. */
function detachNode(node) {
    for (const attachment of attachments) {
        if (attachment.node === node) detach(attachment);
    }
}

// ---------------------------------------------------------------------------
// Preview section
// ---------------------------------------------------------------------------

const PREVIEW_STYLE = `
.mnm-wildcard-preview { display: flex; flex-direction: column; flex: 0 0 auto !important; font-size: 12px; color: var(--input-text, #ddd); }
.mnm-wildcard-preview-header { all: unset; cursor: pointer; user-select: none; padding: 2px 4px; opacity: 0.8; }
.mnm-wildcard-preview-header:hover { opacity: 1; }
.mnm-wildcard-preview-body { flex: none; box-sizing: border-box; min-height: 40px; resize: vertical; overflow: auto; white-space: pre-wrap; overflow-wrap: break-word;
  font-family: monospace; line-height: 1.5; padding: 4px 6px; border-radius: 6px;
  background: var(--comfy-input-bg, rgba(0,0,0,0.25));
  /* Readable text, not part of the node's drag handle. */
  cursor: text; user-select: text; -webkit-user-select: text; }
.mnm-wildcard-preview-empty { opacity: 0.6; font-style: italic; }
.mnm-wildcard-source-tip { position: fixed; z-index: 10000; pointer-events: none; max-width: min(720px, 80vw); max-height: 80vh; overflow: hidden; padding: 5px 8px; border-radius: 6px;
  background: var(--comfy-menu-bg, #222); color: var(--fg-color, #ddd); border: 1px solid var(--border-color, #444); box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  font-size: 12px; line-height: 1.4; white-space: pre-wrap; overflow-wrap: anywhere; }
.mnm-wildcard-source-tip-kind { opacity: 0.65; font-size: 11px; }
.mnm-wildcard-source-tip-from { font-family: monospace; }
.mnm-wildcard-source-tip-file { margin-top: 3px; }
`;

let previewStyleAdded = false;

/** Add the preview's stylesheet once. */
function addPreviewStyle() {
    if (previewStyleAdded) return;
    previewStyleAdded = true;
    const style = document.createElement("style");
    style.textContent = PREVIEW_STYLE;
    document.head.appendChild(style);
}

let sourceTip = null;

/** Show where a Preview part came from, next to the cursor. */
function showSourceTip(span, x, y) {
    if (!sourceTip) {
        sourceTip = document.createElement("div");
        sourceTip.className = "mnm-wildcard-source-tip";
        document.body.appendChild(sourceTip);
    }
    if (sourceTip.mnmSpan !== span) {
        sourceTip.mnmSpan = span;
        const line = (name, text) => Object.assign(document.createElement("div"), { className: `mnm-wildcard-source-tip-${name}`, textContent: text });
        const { kind, from, file, line: number } = span.dataset;
        sourceTip.replaceChildren(line("kind", kind), line("from", from));
        if (file) sourceTip.append(line("file", number ? `File: ${file}, line ${number}` : `File: ${file}`));
    }
    sourceTip.style.display = "";
    const gap = 14;
    const { offsetWidth: width, offsetHeight: height } = sourceTip;
    sourceTip.style.left = `${Math.max(0, x + gap + width > innerWidth ? x - gap - width : x + gap)}px`;
    sourceTip.style.top = `${Math.max(0, y + gap + height > innerHeight ? y - gap - height : y + gap)}px`;
}

function hideSourceTip() {
    if (!sourceTip) return;
    sourceTip.style.display = "none";
    sourceTip.mnmSpan = null;
}

const HEADER_HEIGHT = 22;
const DEFAULT_BODY_HEIGHT = 100;

/** Add the expandable Preview section to a wildcard processor node. */
function addPreview(node) {
    addPreviewStyle();
    const element = document.createElement("div");
    element.className = "mnm-wildcard-preview";
    const header = document.createElement("button");
    header.className = "mnm-wildcard-preview-header";
    header.type = "button";
    const body = document.createElement("div");
    body.className = "mnm-wildcard-preview-body";
    element.append(header, body);

    node.properties ??= {};
    const state = { data: null };
    const isOpen = () => node.properties.mnmPreviewOpen === true;
    // The body keeps a fixed height, set by dragging its bottom edge, instead
    // of taking a share of the node's height.
    const bodyHeight = () => node.properties.mnmPreviewHeight ?? DEFAULT_BODY_HEIGHT;
    const height = () => HEADER_HEIGHT + (isOpen() ? bodyHeight() + 4 : 0);

    /** Make the node tall enough for the preview (classic canvas). */
    const fitNode = () => {
        const size = node.computeSize?.();
        if (size) node.setSize([node.size[0], Math.max(node.size[1], size[1])]);
        node.setDirtyCanvas?.(true, true);
    };

    const render = () => {
        hideSourceTip();
        header.textContent = `${isOpen() ? "▾" : "▸"} Preview`;
        body.style.display = isOpen() ? "" : "none";
        body.style.height = `${bodyHeight()}px`;
        if (!isOpen()) return;
        if (!state.data) {
            body.innerHTML = '<span class="mnm-wildcard-preview-empty">Run the workflow to see the result.</span>';
            return;
        }
        body.innerHTML = renderPreviewHTML(state.data.source, state.data.segments, highlightOptions());
    };

    const widget = node.addDOMWidget("wildcard_preview", "mnm_wildcard_preview", element, {
        serialize: false,
        hideOnZoom: false,
    });
    // Give the widget a fixed size so it never takes a share of the node's
    // spare height. A computeSize gives it a fixed row on the classic canvas;
    // without computeLayoutSize the Vue renderer sizes its row to content.
    widget.computeSize = (width) => [width ?? node.size[0], height()];
    widget.computeLayoutSize = undefined;
    element.addEventListener("pointerdown", (event) => event.stopPropagation());

    body.addEventListener("pointermove", (event) => {
        const span = event.target.closest?.(".mnm-wh-from");
        if (span) showSourceTip(span, event.clientX, event.clientY);
        else hideSourceTip();
    });
    body.addEventListener("pointerleave", hideSourceTip);
    body.addEventListener("scroll", hideSourceTip);
    // The node hands wheel events to the canvas, which zooms. Keep them while
    // the preview has something to scroll; Ctrl+wheel still zooms the canvas.
    body.addEventListener("wheel", (event) => {
        if (event.ctrlKey || event.metaKey) return;
        if (body.scrollHeight > body.clientHeight || body.scrollWidth > body.clientWidth) event.stopPropagation();
    }, { passive: true });

    header.addEventListener("click", () => {
        node.properties.mnmPreviewOpen = !isOpen();
        render();
        fitNode();
    });

    // Remember the height the user drags the body to.
    new ResizeObserver(() => {
        if (!isOpen() || !body.isConnected) return;
        if (body.offsetHeight && body.offsetHeight !== bodyHeight()) {
            node.properties.mnmPreviewHeight = body.offsetHeight;
            fitNode();
        }
    }).observe(body);

    // A loaded workflow restores the open state and height after creation.
    const onConfigure = node.onConfigure;
    node.onConfigure = function () {
        const result = onConfigure?.apply(this, arguments);
        render();
        return result;
    };

    node.mnmWildcardPreview = {
        widget,
        show(data) {
            state.data = data;
            render();
        },
        refresh: render,
    };
    render();
}

/** Re-render every open Preview, e.g. after a highlight setting changed. */
export function refreshWildcardPreviews() {
    for (const node of app.graph?._nodes ?? []) node.mnmWildcardPreview?.refresh();
}

onWildcardHighlightRefresh(refreshWildcardPreviews);

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

app.registerExtension({
    name: "MNeMiC.WildcardHighlight",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const widgetNames = WILDCARD_TEXT_WIDGETS[nodeData.name];
        if (!widgetNames) return;
        const hasPreview = nodeData.name in PREVIEW_NODES;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            for (const name of widgetNames) attachWildcardHighlight(this, name);
            if (hasPreview) addPreview(this);
            return result;
        };

        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            detachNode(this);
            if (hasPreview) hideSourceTip();
            return onRemoved?.apply(this, arguments);
        };

        if (hasPreview) {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecuted?.apply(this, arguments);
                const data = message?.mnm_wildcard_preview?.[0];
                if (data) this.mnmWildcardPreview?.show(data);
                return result;
            };
        }
    },
});
