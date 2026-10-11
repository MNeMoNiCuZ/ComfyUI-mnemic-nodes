import { app } from "../../../scripts/app.js";

const NODE_ID = "MNeMiC_DownloadImageFromURL";
const LEGACY_ID = "🖼️ Download Image from URL";
const SAVE_SETTINGS = new Set(["name", "path", "save_location", "overwrite", "file_format", "quality"]);
const RENAMED_INPUTS = { save_file_name_override: "name", save_path: "path" };

app.registerExtension({
    name: "mnemic.DownloadImageFromURL",
    beforeConfigureGraph(data) {
        function migrate(graph) {
            for (const node of graph.nodes ?? []) {
                if (node.type !== NODE_ID && node.type !== LEGACY_ID) continue;
                const values = node.widgets_values;
                if (!Array.isArray(values) || typeof values[1] === "boolean") continue;
                // Optional widgets may have been grouped after required widgets.
                const grouped = values.length >= 5 && ["input", "output"].includes(values[1]) && typeof values[2] === "boolean";
                const [url = "", name = "", path = "", location = "input", overwrite = false] = grouped
                    ? [values[0], values[3], values[4], values[1], values[2]]
                    : values;
                node.widgets_values = [url, Boolean(path), name, path, location, overwrite, "png", 100];
                node.type = NODE_ID;
                for (const input of node.inputs ?? []) {
                    input.name = RENAMED_INPUTS[input.name] ?? input.name;
                    if (input.widget) input.widget.name = RENAMED_INPUTS[input.widget.name] ?? input.widget.name;
                }
            }
            for (const subgraph of graph.definitions?.subgraphs ?? []) migrate(subgraph);
        }
        migrate(data);
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        function addPlaceholders(node) {
            for (const widget of node.widgets ?? []) {
                const placeholder = nodeData.input?.required?.[widget.name]?.[1]?.placeholder;
                if (!placeholder) continue;
                // Single-line string widgets currently drop the schema placeholder.
                // Forward it for Vue nodes, and draw it for canvas nodes.
                widget.options ??= {};
                widget.options.placeholder = placeholder;
                if (widget.element) widget.element.placeholder = placeholder;
                const draw = widget.drawWidget;
                if (typeof draw !== "function") continue;
                widget.drawWidget = function (ctx, options) {
                    const result = draw.apply(this, arguments);
                    if (this.value !== "" || this.hidden || options.showText === false) return result;
                    ctx.save();
                    ctx.fillStyle = this.secondary_text_color ?? "#888";
                    ctx.textAlign = "right";
                    ctx.textBaseline = "middle";
                    const left = 32 + ctx.measureText(this.displayName ?? this.name).width;
                    const right = options.width - 20;
                    ctx.beginPath();
                    ctx.rect(left, this.y, Math.max(0, right - left), this.height);
                    ctx.clip();
                    ctx.fillText(placeholder, right, this.y + this.height / 2);
                    ctx.restore();
                    return result;
                };
            }
        }

        function setup(node) {
            const save = node.widgets?.find(widget => widget.name === "save");
            if (!save || node.mnemicDownloadSaveSettings) return;
            addPlaceholders(node);
            const format = node.widgets.find(widget => widget.name === "file_format");
            const originals = new Map(node.widgets.filter(widget => SAVE_SETTINGS.has(widget.name)).map(widget => [
                widget, { type: widget.type, computeSize: widget.computeSize },
            ]));

            function update(resize = false) {
                for (const [widget, original] of originals) {
                    const hidden = !save.value || (widget.name === "quality" && format?.value === "png");
                    widget.hidden = hidden;
                    widget.type = hidden ? "hidden" : original.type;
                    if (hidden) widget.computeSize = () => [0, -4];
                    else if (original.computeSize) widget.computeSize = original.computeSize;
                    else delete widget.computeSize;
                }
                if (resize) node.setSize([node.size[0], node.computeSize()[1]]);
                node.setDirtyCanvas(true, true);
            }

            for (const widget of [save, format].filter(Boolean)) {
                const callback = widget.callback;
                widget.callback = function () {
                    const result = callback?.apply(this, arguments);
                    update(true);
                    return result;
                };
            }
            node.mnemicDownloadSaveSettings = update;
            update(true);
        }

        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onCreated?.apply(this, arguments);
            setup(this);
            return result;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            setup(this);
            this.mnemicDownloadSaveSettings?.();
            return result;
        };
    },
});
