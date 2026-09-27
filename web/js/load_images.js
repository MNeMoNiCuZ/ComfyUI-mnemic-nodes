import { app } from "../../../scripts/app.js";

const EXTRA_WIDGET = "extra_path_formats";

function moveLegacyOutput(outputs) {
    if (!["image_path", "path/file output"].includes(outputs?.[2]?.name)) return false;
    outputs.splice(4, 0, outputs.splice(2, 1)[0]);
    return true;
}

app.registerExtension({
    name: "mnemic.LoadImagesFromPath",
    beforeConfigureGraph(data) {
        function migrate(graph) {
            for (const node of graph.nodes ?? []) {
                if (node.type !== "MNeMiC_LoadImagesFromPath" || !moveLegacyOutput(node.outputs)) continue;
                for (const link of graph.links ?? []) {
                    const origin = Array.isArray(link) ? link[1] : link.origin_id;
                    if (String(origin) !== String(node.id)) continue;
                    const slot = Array.isArray(link) ? link[2] : link.origin_slot;
                    const mapped = slot === 2 ? 4 : slot === 3 ? 2 : slot === 4 ? 3 : slot;
                    if (Array.isArray(link)) link[2] = mapped;
                    else link.origin_slot = mapped;
                }
            }
            for (const subgraph of graph.definitions?.subgraphs ?? []) migrate(subgraph);
        }
        migrate(data);
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MNeMiC_LoadImagesFromPath") return;
        const formatInput = nodeData.input.required.path_format;
        const formats = Array.isArray(formatInput[0]) ? formatInput[0] : formatInput[1].options;
        const aliases = formatInput[1].format_aliases ?? {};
        const tooltips = formatInput[1].format_tooltips ?? {};
        const normalizeFormat = (value) => aliases[value] ?? value;
        const maxOutputs = nodeData.input.optional[EXTRA_WIDGET][1].max_path_outputs;

        function attachTooltip(widget) {
            Object.defineProperty(widget, "tooltip", {
                configurable: true,
                enumerable: true,
                get() { return tooltips[normalizeFormat(widget.value)] ?? formatInput[1].tooltip; },
                set() {},
            });
        }

        function setup(node) {
            const first = node.widgets.find((widget) => widget.name === "path_format");
            const storage = node.widgets.find((widget) => widget.name === EXTRA_WIDGET);
            if (!first || !storage) return;

            // Keep schema widget order for saved workflows and API prompts.
            // Only the extra dropdowns and buttons are excluded from serialization.
            storage.hidden = true;
            storage.type = "hidden";
            storage.computeSize = () => [0, -4];
            storage.draw = () => {};
            first.label = "output1";
            attachTooltip(first);

            const controls = [];
            const buttons = [];
            const outputIndex = (index) => index + 4;

            function resize() {
                node.setSize([node.size[0], node.computeSize()[1]]);
                node.setDirtyCanvas(true, true);
            }

            function sync() {
                storage.value = JSON.stringify(controls.map((widget) => widget.value));
                const values = [first.value, ...controls.map((widget) => widget.value)];
                values.forEach((value, index) => {
                    const output = node.outputs[outputIndex(index)];
                    if (output) output.name = output.label = `output${index + 1}`;
                });
                node.setDirtyCanvas(true, true);
            }

            function addControl(value) {
                const number = controls.length + 2;
                const widget = node.addWidget("combo", `output${number}`, value, sync, {
                    values: formats, serialize: false,
                });
                widget.serialize = false;
                attachTooltip(widget);
                controls.push(widget);
                // Keep the Add button after the format dropdowns.
                node.widgets = node.widgets.filter((item) => !buttons.includes(item));
                node.widgets.push(...buttons);
            }

            function restore() {
                const saved = JSON.parse(storage.value || "[]");
                if (!Array.isArray(saved) || saved.length >= maxOutputs) {
                    throw new Error("Invalid path/file output formats.");
                }
                const values = saved.map(normalizeFormat);
                first.value = normalizeFormat(first.value);
                if (values.some((value) => !formats.includes(value))) {
                    throw new Error("Invalid path/file output formats.");
                }
                node.widgets = node.widgets.filter((item) => !controls.includes(item));
                controls.length = 0;
                const count = 5 + values.length;
                while (node.outputs.length > count) node.removeOutput(node.outputs.length - 1);
                while (node.outputs.length < count) {
                    node.addOutput(`output${node.outputs.length - 3}`, "STRING");
                }
                values.forEach(addControl);
                sync();
            }

            const originalCallback = first.callback;
            first.callback = function () {
                const result = originalCallback?.apply(this, arguments);
                sync();
                return result;
            };

            const add = node.addWidget("button", "Add file/path output", null, () => {
                if (controls.length + 1 >= maxOutputs) return;
                node.graph?.beforeChange?.();
                node.addOutput(`output${controls.length + 2}`, "STRING");
                addControl(normalizeFormat("filename only"));
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            add.serialize = false;
            add.tooltip = `Add another path or filename output, up to ${maxOutputs} in total.`;
            buttons.push(add);

            const remove = node.addWidget("button", "Remove last file/path output", null, () => {
                if (!controls.length) return;
                node.graph?.beforeChange?.();
                const widget = controls.pop();
                node.widgets = node.widgets.filter((item) => item !== widget);
                node.removeOutput(node.outputs.length - 1);
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            remove.serialize = false;
            remove.tooltip = "Remove the last additional path/file output and its connections.";
            buttons.push(remove);

            node._restorePathOutputs = restore;
            restore();
            resize();
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
            // Also handle pasted or cloned nodes, which bypass graph loading.
            if (moveLegacyOutput(this.outputs)) {
                this.outputs.forEach((output, index) => {
                    for (const id of output.links ?? []) {
                        const link = this.graph?._links?.get?.(id) ?? this.graph?.links?.[id];
                        if (link) link.origin_slot = index;
                    }
                });
            }
            this._restorePathOutputs?.();
            return result;
        };
    },
});
