import { app } from "../../../scripts/app.js";

// ─── Wide tooltips for MNeMiC nodes ───
//
// ComfyUI renders node/widget tooltips two different ways, and both of them turn
// a long tooltip (like the Wildcard Processor's syntax help) into a narrow,
// screens-tall strip:
//
//   * Vue nodes (new node UI): a PrimeVue tooltip, whose theme caps the text at
//     12.5rem (~200px) and renders it with `leading-none`.
//   * Classic canvas nodes: `div.node-tooltip`, which is absolutely positioned
//     with no width, so it shrink-to-fits into whatever space is left between the
//     cursor and the right edge of the window.
//
// Both are single shared elements used by every node in every pack, so the width
// override is gated behind a marker attribute on <body> that is only set while
// the cursor is over a node from this pack. Tooltips belonging to other nodes,
// the sidebar, menus, etc. are never touched.

const MARKER_ATTR = "data-mnemic-tooltip";
const MAX_WIDTH = "min(540px, 70vw)";

const TOOLTIP_CSS = `
  body[${MARKER_ATTR}] .node-tooltip {
    width: max-content !important;
    max-width: ${MAX_WIDTH} !important;
    line-height: 1.45 !important;
  }
  body[${MARKER_ATTR}] .p-tooltip {
    max-width: ${MAX_WIDTH} !important;
  }
  body[${MARKER_ATTR}] .p-tooltip .p-tooltip-text {
    width: max-content !important;
    max-width: ${MAX_WIDTH} !important;
    white-space: pre-wrap !important;
    line-height: 1.45 !important;
    text-align: left !important;
  }
`;

function isMnemicNode(node) {
  if (!node) return false;
  const def = node.constructor?.nodeData;
  const pythonModule = def?.python_module;
  if (typeof pythonModule === "string" && pythonModule.includes("ComfyUI-mnemic-nodes")) {
    return true;
  }
  const category = def?.category ?? node.constructor?.category ?? "";
  return typeof category === "string" && category.includes("MNeMiC");
}

// Vue nodes are real DOM: the node root is .lg-node[data-node-id].
function nodeFromDom(target) {
  const nodeEl = target?.closest?.(".lg-node[data-node-id]");
  const id = nodeEl?.dataset?.nodeId;
  if (id == null) return null;
  const graph = app.canvas?.graph ?? app.graph;
  return graph?.getNodeById?.(Number(id)) ?? graph?.getNodeById?.(id) ?? null;
}

let markerActive = false;

function onPointerMove(event) {
  // Over the canvas litegraph tracks the hovered node itself; anywhere else the
  // only meaningful hover is a Vue node's DOM. Never fall back to node_over off
  // the canvas, or a stale value would widen unrelated UI tooltips.
  const overCanvas = event.target instanceof HTMLCanvasElement;
  const node = overCanvas ? app.canvas?.node_over : nodeFromDom(event.target);
  const wanted = isMnemicNode(node);

  if (wanted === markerActive) return;
  markerActive = wanted;
  if (wanted) {
    document.body.setAttribute(MARKER_ATTR, "");
  } else {
    document.body.removeAttribute(MARKER_ATTR);
  }
}

app.registerExtension({
  name: "MNeMiC.TooltipWidth",
  setup() {
    const style = document.createElement("style");
    style.id = "mnemic-tooltip-width";
    style.textContent = TOOLTIP_CSS;
    document.head.appendChild(style);

    // Capture phase so the marker is up to date before either tooltip renders.
    window.addEventListener("pointermove", onPointerMove, { capture: true, passive: true });
  },
});
