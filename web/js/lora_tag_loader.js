import { app } from "../../../scripts/app.js";

const NODE_IDS = new Set(["MNeMiC_LoraTagLoader", "🏷️ LoRA Loader Prompt Tags"]);
const INPUT_ORDER = ["MODEL", "CLIP", "STRING"];

function orderInputs(node) {
    if (!node.inputs) return;

    // ComfyUI groups required inputs before optional inputs, putting CLIP last
    // despite the schema order. Move the existing slots to retain their metadata.
    const ordered = INPUT_ORDER.map(name => node.inputs.find(input => input.name === name));
    if (ordered.some(input => !input)) return;
    ordered.push(...node.inputs.filter(input => !INPUT_ORDER.includes(input.name)));
    if (ordered.every((input, index) => input === node.inputs[index])) return;

    node.inputs.splice(0, node.inputs.length, ...ordered);
    // Loaded workflows store target_slot by index. Keep each connection on the
    // same named input after moving its slot.
    for (let index = 0; index < node.inputs.length; index++) {
        const linkId = node.inputs[index].link;
        if (linkId == null) continue;
        const link = node.graph?.links?.[linkId];
        if (link) link.target_slot = index;
    }
    node.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "mnemic.LoraTagLoaderInputOrder",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!NODE_IDS.has(nodeData.name)) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            orderInputs(this);
            return result;
        };
    },
    loadedGraphNode(node) {
        if (NODE_IDS.has(node.comfyClass) || NODE_IDS.has(node.type)) {
            orderInputs(node);
        }
    },
});
