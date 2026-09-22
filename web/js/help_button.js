import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// Adds a "?" to the title bar of every pack node. Clicking it shows the node's
// web/docs/<node_id>.md page in a panel, rendered with the frontend's own
// markdown renderer. Works in both the classic canvas and Vue nodes modes.

const CATEGORY = "⚡ MNeMiC Nodes";
const DOCS_URL = "/extensions/ComfyUI-mnemic-nodes/docs/";
const ICON_SIZE = 16;
const ICON_MARGIN = 6;

const helpNodeIds = new Set();
const pageCache = new Map();
let panel = null;
let panelNodeId = null;

async function fetchPage(nodeId) {
    if (!pageCache.has(nodeId)) {
        const res = await fetch(api.fileURL(`${DOCS_URL}${nodeId}.md`));
        pageCache.set(nodeId, res.ok ? await res.text() : `No help page found for \`${nodeId}\`.`);
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
    `;
    document.head.appendChild(style);
}

function closePanel() {
    panel?.remove();
    panel = null;
    panelNodeId = null;
}

async function toggleHelp(node) {
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
    button.title = "Show help";
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
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && panel) closePanel();
        });
    },
});
