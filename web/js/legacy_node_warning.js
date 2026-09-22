import { app } from "../../../scripts/app.js";

// Nodes whose extra input slots are added at runtime by JS (string_2, string_3,
// ... / region_0, region_1, ...) rather than declared in the Python schema.
//
// ComfyUI's node replacement rebuilds the node from the new schema and only
// reconnects inputs that the replacement mapping names. Schema-declared inputs
// survive; these runtime-added slots do not exist on the fresh node, so their
// links are dropped. Warn before the user clicks Replace.
const DYNAMIC_INPUT_NODES = {
    "🔗 String Concat / Append": {
        name: "String Concat / Append",
        slots: "string_2 and above",
    },
    "🧩 Ideogram 4 Prompt Builder w. String Inputs": {
        name: "Ideogram 4 Prompt Builder",
        slots: "the region_N inputs",
    },
};

function warnAboutLostConnections(graphData) {
    const affected = new Map();

    for (const node of graphData?.nodes ?? []) {
        const info = DYNAMIC_INPUT_NODES[node?.type];
        if (!info) continue;

        // Only warn when there is something to lose: a link on a slot that the
        // new node will not have.
        const atRisk = (node.inputs ?? []).filter(
            (input) =>
                input?.link != null &&
                /^(string_(\d+)|region_(\d+))$/.test(input.name ?? "") &&
                Number((input.name.match(/(\d+)$/) ?? [])[1]) >= (input.name.startsWith("string_") ? 2 : 0)
        ).length;

        if (atRisk > 0) {
            affected.set(info.name, (affected.get(info.name) ?? 0) + atRisk);
        }
    }

    if (affected.size === 0) return;

    const detail = [...affected.entries()]
        .map(([name, count]) => `${name}: ${count} connection${count > 1 ? "s" : ""}`)
        .join(", ");

    if (app.extensionManager?.toast) {
        app.extensionManager.toast.add({
            severity: "warn",
            summary: "Replacing these nodes will drop connections",
            detail:
                `${detail}. These input slots are created on the fly and are not part of the ` +
                `node definition, so ComfyUI cannot carry them across a replacement. ` +
                `Reconnect them after replacing, or leave the nodes as they are.`,
            life: 15000,
        });
    }
    console.warn(`[⚡ MNeMiC Nodes] Node replacement will drop dynamic input connections — ${detail}`);
}

app.registerExtension({
    name: "mnemic.LegacyNodeWarning",
    beforeConfigureGraph(graphData) {
        try {
            warnAboutLostConnections(graphData);
        } catch (err) {
            console.error("[⚡ MNeMiC Nodes] legacy node warning failed", err);
        }
    },
});
