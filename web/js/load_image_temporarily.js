import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const loadedNodes = new Set();

app.registerExtension({
    name: "mnemic.LoadImageTemporarily",
    loadedGraphNode(node) {
        if (node.comfyClass === "MNeMiC_LoadImageTemporarily") {
            loadedNodes.add(node);
        }
    },
    async afterConfigureGraph() {
        const nodes = [...loadedNodes];
        loadedNodes.clear();
        await Promise.all(nodes.map(async (node) => {
            const widget = node.widgets?.find((widget) => widget.name === "image");
            const value = widget?.value;
            if (typeof value !== "string" || !value) return;
            if (value.endsWith("[input]") || value.endsWith("[output]")) return;

            const path = (value.endsWith(" [temp]") ? value.slice(0, -7) : value).replaceAll("\\", "/");
            const separator = path.lastIndexOf("/");
            const params = new URLSearchParams({
                filename: path.slice(separator + 1),
                subfolder: separator < 0 ? "" : path.slice(0, separator),
                type: "temp",
            });
            try {
                const response = await api.fetchApi(`/view?${params}`, { method: "HEAD" });
                // Temp files can disappear between sessions. Clear the stale selection
                // before the frontend scans the restored graph for missing media.
                if (response.status === 404 && widget.value === value && !node.isUploading) {
                    widget.value = "";
                    node.imgs = null;
                    node.setDirtyCanvas(true, true);
                }
            } catch {
                // Keep the selection when the server could not verify the file.
            }
        }));
    },
});
