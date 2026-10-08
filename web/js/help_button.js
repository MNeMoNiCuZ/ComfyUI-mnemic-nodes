import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// Adds a "?" to the title bar of every pack node. Clicking it shows the node's
// web/docs/<node_id>.md page in a panel, rendered with the frontend's own
// markdown renderer. Works in both the classic canvas and Vue nodes modes.

const CATEGORY = "⚡ MNeMiC Nodes";
const DOCS_URL = "/extensions/ComfyUI-mnemic-nodes/docs/";
const ICON_SIZE = 16;
const ICON_MARGIN = 6;
const WILDCARD_IDS = new Set(["MNeMiC_WildcardProcessor", "MNeMiC_WildcardProcessorAdvanced"]);

const helpNodeIds = new Set();
const pageCache = new Map();
let panel = null;
let panelNodeId = null;
let helpTooltip = null;
let hoverNode = null;
let hoverTimer = null;
let hideTimer = null;

async function fetchPage(nodeId) {
    if (!pageCache.has(nodeId)) {
        const res = await fetch(api.fileURL(`${DOCS_URL}${nodeId}.md`));
        let markdown = res.ok ? await res.text() : `No help page found for \`${nodeId}\`.`;
        if (res.ok && WILDCARD_IDS.has(nodeId)) {
            const reference = await fetch(api.fileURL(`${DOCS_URL}wildcard_reference.md`));
            if (reference.ok) markdown += `\n\n${await reference.text()}`;
        }
        pageCache.set(nodeId, markdown);
    }
    return pageCache.get(nodeId);
}

function addStylesheet() {
    const style = document.createElement("style");
    style.textContent = `
        .mnemic-help-panel {
            position: fixed;
            top: 60px;
            right: 16px;
            width: 520px;
            max-width: calc(100vw - 32px);
            height: 70vh;
            min-width: 280px;
            min-height: 160px;
            display: flex;
            flex-direction: column;
            background: var(--comfy-menu-bg);
            color: var(--fg-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
            resize: both;
            overflow: hidden;
            z-index: 1000;
        }
        .mnemic-help-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            font-weight: bold;
        }
        .mnemic-help-panel-close {
            cursor: pointer;
            padding: 0 4px;
            opacity: 0.7;
        }
        .mnemic-help-panel-close:hover {
            opacity: 1;
        }
        .mnemic-help-panel-body {
            flex: 1;
            overflow: auto;
            padding: 4px 16px 16px;
            font-size: 13px;
            line-height: 1.5;
        }
        .mnemic-help-panel-body pre {
            background: var(--comfy-input-bg);
            padding: 8px;
            border-radius: 4px;
            overflow-x: auto;
        }
        .mnemic-help-panel-body code {
            background: var(--comfy-input-bg);
            padding: 0 3px;
            border-radius: 3px;
        }
        .mnemic-help-panel-body pre code {
            padding: 0;
        }
        .mnemic-help-panel-body table {
            border-collapse: collapse;
        }
        .mnemic-help-panel-body th,
        .mnemic-help-panel-body td {
            border: 1px solid var(--border-color);
            padding: 2px 6px;
        }
        .mnemic-help-panel-body img {
            max-width: 100%;
        }
        .mnemic-help-btn {
            color: orange;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            flex-shrink: 0;
            padding: 0 4px;
            line-height: 1;
            user-select: none;
        }
        .mnemic-help-tooltip {
            position: fixed;
            box-sizing: border-box;
            width: 600px;
            max-width: calc(100vw - 24px);
            max-height: min(75vh, 760px);
            overflow: auto;
            background: var(--comfy-menu-bg, #222);
            color: var(--fg-color, #ddd);
            border: 1px solid var(--border-color, #555);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
            z-index: 1001;
        }
        .mnemic-help-tooltip h1 { font-size: 20px; }
        .mnemic-help-tooltip h2 { font-size: 17px; margin-top: 20px; }
        .mnemic-help-tooltip h3 { font-size: 14px; margin-top: 16px; }
        .mnemic-help-tooltip p, .mnemic-help-tooltip li { overflow-wrap: anywhere; }
        .mnemic-help-tooltip table { width: 100%; }
        body[data-mnemic-help-hover] .node-tooltip,
        body[data-mnemic-help-hover] .p-tooltip { display: none !important; }
    `;
    document.head.appendChild(style);
}

function closePanel() {
    panel?.remove();
    panel = null;
    panelNodeId = null;
}

function closeHelpTooltip() {
    clearTimeout(hoverTimer);
    clearTimeout(hideTimer);
    hoverNode = null;
    helpTooltip?.remove();
    helpTooltip = null;
    document.body.removeAttribute("data-mnemic-help-hover");
}

function leaveHelpButton() {
    if (!helpTooltip) {
        closeHelpTooltip();
        return;
    }
    clearTimeout(hoverTimer);
    clearTimeout(hideTimer);
    // Give the pointer time to travel from the button into the scrollable help.
    hideTimer = setTimeout(closeHelpTooltip, 250);
}

function scheduleHelpTooltip(node, clientX, clientY) {
    clearTimeout(hideTimer);
    if (hoverNode === node) return;
    closeHelpTooltip();
    hoverNode = node;
    document.body.setAttribute("data-mnemic-help-hover", "");
    hoverTimer = setTimeout(async () => {
        helpTooltip = document.createElement("div");
        helpTooltip.className = "mnemic-help-tooltip mnemic-help-panel-body";
        helpTooltip.setAttribute("role", "tooltip");
        helpTooltip.textContent = "Loading…";
        helpTooltip.addEventListener("pointerenter", () => clearTimeout(hideTimer));
        helpTooltip.addEventListener("pointerleave", leaveHelpButton);
        document.body.appendChild(helpTooltip);
        const tooltip = helpTooltip;
        const position = () => {
            tooltip.style.left = `${Math.max(12, Math.min(clientX + 12, window.innerWidth - tooltip.offsetWidth - 12))}px`;
            tooltip.style.top = `${Math.max(12, Math.min(clientY + 12, window.innerHeight - tooltip.offsetHeight - 12))}px`;
        };
        position();
        try {
            const markdown = await fetchPage(node.comfyClass);
            if (helpTooltip !== tooltip) return;
            tooltip.innerHTML = app.extensionManager.renderMarkdownToHtml(markdown, api.fileURL(DOCS_URL));
        } catch {
            if (helpTooltip !== tooltip) return;
            tooltip.textContent = "Could not load help. Click ? to try again.";
        }
        position();
    }, 400);
}

async function toggleHelp(node) {
    closeHelpTooltip();
    const nodeId = node.comfyClass;
    if (panel && panelNodeId === nodeId) {
        closePanel();
        return;
    }
    if (!panel) {
        panel = document.createElement("div");
        panel.className = "mnemic-help-panel";
        panel.innerHTML = `
            <div class="mnemic-help-panel-header">
                <span class="mnemic-help-panel-title"></span>
                <span class="mnemic-help-panel-close" title="Close">✕</span>
            </div>
            <div class="mnemic-help-panel-body"></div>
        `;
        panel.querySelector(".mnemic-help-panel-close").addEventListener("click", closePanel);
        document.body.appendChild(panel);
    }
    panelNodeId = nodeId;
    panel.querySelector(".mnemic-help-panel-title").textContent = node.constructor.title ?? nodeId;
    const body = panel.querySelector(".mnemic-help-panel-body");
    body.textContent = "Loading…";
    const markdown = await fetchPage(nodeId);
    if (panelNodeId !== nodeId) return;
    body.innerHTML = app.extensionManager.renderMarkdownToHtml(markdown, api.fileURL(DOCS_URL));
    body.scrollTop = 0;
}

// Classic canvas: draw the "?" in the title bar and catch clicks on it.
function addCanvasButton(nodeType) {
    const iconBounds = (node) => [
        node.size[0] - ICON_SIZE - ICON_MARGIN,
        -(LiteGraph.NODE_TITLE_HEIGHT + ICON_SIZE) / 2,
    ];

    const onDrawForeground = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (ctx) {
        const r = onDrawForeground?.apply(this, arguments);
        if (this.flags.collapsed) return r;
        const [x, y] = iconBounds(this);
        ctx.save();
        ctx.font = `bold ${ICON_SIZE}px sans-serif`;
        ctx.fillStyle = "orange";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("?", x + ICON_SIZE / 2, y + ICON_SIZE / 2);
        ctx.restore();
        return r;
    };

    const onMouseDown = nodeType.prototype.onMouseDown;
    nodeType.prototype.onMouseDown = function (e, localPos) {
        if (!this.flags.collapsed) {
            const [x, y] = iconBounds(this);
            if (localPos[0] >= x && localPos[0] <= x + ICON_SIZE && localPos[1] >= y && localPos[1] <= y + ICON_SIZE) {
                toggleHelp(this);
                return true;
            }
        }
        return onMouseDown?.apply(this, arguments);
    };
}

// Vue nodes: inject a "?" into each pack node's header as it appears.
function injectVueButton(header) {
    const nodeEl = header.closest("[data-node-id]");
    if (!nodeEl) return;
    const node = app.graph?.getNodeById(nodeEl.dataset.nodeId);
    if (!node || !helpNodeIds.has(node.comfyClass)) return;
    const container = header.querySelector(":scope > div");
    if (!container) return;

    const button = document.createElement("span");
    button.className = "mnemic-help-btn";
    button.textContent = "?";
    if (WILDCARD_IDS.has(node.comfyClass)) {
        button.tabIndex = 0;
        button.setAttribute("role", "button");
        button.setAttribute("aria-label", "Wildcard documentation");
        button.addEventListener("pointerenter", (e) => scheduleHelpTooltip(node, e.clientX, e.clientY));
        button.addEventListener("pointerleave", leaveHelpButton);
        button.addEventListener("focus", () => {
            const bounds = button.getBoundingClientRect();
            scheduleHelpTooltip(node, bounds.right, bounds.bottom);
        });
        button.addEventListener("blur", leaveHelpButton);
        button.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                toggleHelp(node);
            }
        });
    } else {
        button.title = "Show help";
    }
    button.addEventListener("pointerdown", (e) => e.stopPropagation());
    button.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleHelp(node);
    });
    container.appendChild(button);
}

function observeVueHeaders() {
    const scan = () => document.querySelectorAll(".lg-node-header:not(:has(.mnemic-help-btn))").forEach(injectVueButton);
    scan();
    let pending = false;
    new MutationObserver(() => {
        if (pending) return;
        pending = true;
        requestAnimationFrame(() => {
            pending = false;
            scan();
        });
    }).observe(document.body, { childList: true, subtree: true });
}

app.registerExtension({
    name: "MNeMiC.HelpButton",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.category !== CATEGORY) return;
        helpNodeIds.add(nodeData.name);
        addCanvasButton(nodeType);
    },
    setup() {
        addStylesheet();
        observeVueHeaders();
        window.addEventListener("pointermove", (e) => {
            if (e.target.closest?.(".mnemic-help-tooltip, .mnemic-help-btn")) return;
            if (e.target === app.canvas?.canvas) {
                const node = app.canvas.node_over;
                if (WILDCARD_IDS.has(node?.comfyClass) && !node.flags.collapsed) {
                    const pos = app.canvas.convertEventToCanvasOffset(e);
                    const x = node.pos[0] + node.size[0] - ICON_SIZE - ICON_MARGIN;
                    const y = node.pos[1] - (LiteGraph.NODE_TITLE_HEIGHT + ICON_SIZE) / 2;
                    if (pos[0] >= x && pos[0] <= x + ICON_SIZE && pos[1] >= y && pos[1] <= y + ICON_SIZE) {
                        scheduleHelpTooltip(node, e.clientX, e.clientY);
                        return;
                    }
                }
            }
            if (hoverNode) leaveHelpButton();
        }, { passive: true });
        window.addEventListener("blur", closeHelpTooltip);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                closeHelpTooltip();
                closePanel();
            }
        });
    },
});
