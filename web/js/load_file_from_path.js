import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const STORAGE = "files";
// name, current_index and total_count come before the file outputs.
const FIXED_OUTPUTS = 3;
const EXTENSION_HELP = "Extension of the file for this output, e.g. png. List several, like png, jpg, webp, to use whichever exists.";
const MISMATCH_COLOR = "#e5c07b";
const EMPTY_COLOR = "#ff4d4f";

app.registerExtension({
    name: "mnemic.LoadFileFromPath",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MNeMiC_LoadFileFromPath") return;
        const config = nodeData.input.optional[STORAGE][1];
        const types = config.file_types;
        const typeHelp = config.type_tooltips;
        const maxOutputs = config.max_file_outputs;

        function setup(node) {
            const storage = node.widgets.find((widget) => widget.name === STORAGE);
            if (!storage) return;
            storage.hidden = true;
            storage.type = "hidden";
            storage.computeSize = () => [0, -4];
            storage.draw = () => {};

            let rows = [];
            let rowWidgets = [];
            let extensionWidgets = [];
            const buttons = [];
            // File counts per row for the current path, from the server.
            let counts = null;
            let complete = 0;

            function resize() {
                node.setSize([node.size[0], Math.max(node.size[1], node.computeSize()[1])]);
                node.setDirtyCanvas(true, true);
            }

            function sync() {
                storage.value = JSON.stringify(rows);
                rows.forEach((row, index) => {
                    const slot = FIXED_OUTPUTS + index;
                    const output = node.outputs[slot];
                    if (!output) return;
                    if (output.type !== types[row.type]) {
                        // Links made for the old type would fail on the next run.
                        if (output.links?.length) node.disconnectOutput(slot);
                        output.type = types[row.type];
                    }
                    output.name = `output${index + 1}`;
                    output.label = `${row.type} (${row.extension || "?"})`;
                });
                node.setDirtyCanvas(true, true);
            }

            /**
             * Show each row's file count in its label, marked 🔴 at 0 and 🟡 when
             * the rows' counts differ. Set through the widget's own label setter:
             * Nodes 2.0 reads labels from the widget store that setter writes to.
             */
            function showCounts() {
                const mismatch = !!counts && new Set(counts).size > 1;
                extensionWidgets.forEach((widget, index) => {
                    const count = counts?.[index];
                    const mark = count === 0 ? " 🔴" : mismatch ? " 🟡" : "";
                    widget.label = count === undefined ? `extension ${index + 1}` : `extension ${index + 1} (${count})${mark}`;
                });
                node.setDirtyCanvas(true, true);
            }

            /** On the classic canvas the label text is also coloured: red at 0, yellow when the counts differ. */
            function decorateExtension(widget, index) {
                const base = Object.getPrototypeOf(widget);
                Object.defineProperty(widget, "secondary_text_color", {
                    configurable: true,
                    get() {
                        const count = counts?.[index];
                        if (count === 0) return EMPTY_COLOR;
                        if (count !== undefined && new Set(counts).size > 1) return MISMATCH_COLOR;
                        return Reflect.get(base, "secondary_text_color", widget);
                    },
                });
                Object.defineProperty(widget, "tooltip", {
                    configurable: true,
                    enumerable: true,
                    get() {
                        if (!counts) return EXTENSION_HELP;
                        const line = rows.map((row, i) => `${row.extension || "?"}: ${counts[i] ?? "?"}`).join(", ");
                        return `${EXTENSION_HELP}\nFiles found: ${line}. ${complete} of the first output's ${counts[0]} files have every file; the others get empty outputs for their missing files.`;
                    },
                    set() {},
                });
            }

            let countsKey;
            let countsRequest;
            async function updateCounts() {
                const value = (name) => node.widgets.find((widget) => widget.name === name)?.value;
                // A connected path is only known when the workflow runs.
                const linked = node.inputs?.some((input) => ["input_path", "include_subfolders"].includes(input.name) && input.link != null);
                const inputPath = linked ? "" : String(value("input_path") ?? "");
                const query = new URLSearchParams({
                    input_path: inputPath,
                    include_subfolders: String(!!value("include_subfolders")),
                    extensions: JSON.stringify(rows.map((row) => row.extension)),
                });
                const key = query.toString();
                if (key === countsKey) return;
                countsKey = key;
                countsRequest?.abort();
                counts = null;
                showCounts();
                if (!inputPath.trim()) return;
                countsRequest = new AbortController();
                try {
                    const response = await api.fetchApi(`/mnemic/load-file/counts?${query}`, { signal: countsRequest.signal });
                    if (!response.ok || key !== countsKey) return;
                    ({ counts, complete } = await response.json());
                    showCounts();
                } catch (error) {
                    if (error.name !== "AbortError") console.warn("[MNeMiC] Load File From Path: file count failed", error);
                }
            }

            function rebuild() {
                node.widgets = node.widgets.filter((widget) => !rowWidgets.includes(widget) && !buttons.includes(widget));
                rowWidgets = [];
                extensionWidgets = [];
                rows.forEach((row, index) => {
                    const extension = node.addWidget("text", `extension ${index + 1}`, row.extension, (value) => {
                        row.extension = value;
                        sync();
                    }, { serialize: false });
                    extension.serialize = false;
                    decorateExtension(extension, index);
                    const type = node.addWidget("combo", `type ${index + 1}`, row.type, (value) => {
                        row.type = value;
                        sync();
                    }, { values: Object.keys(types), serialize: false });
                    type.serialize = false;
                    Object.defineProperty(type, "tooltip", {
                        configurable: true,
                        enumerable: true,
                        get() { return typeHelp[type.value]; },
                        set() {},
                    });
                    rowWidgets.push(extension, type);
                    extensionWidgets.push(extension);
                });
                node.widgets.push(...buttons);
                showCounts();
            }

            function restore() {
                const saved = JSON.parse(storage.value || "[]");
                if (!Array.isArray(saved) || !saved.length || saved.length > maxOutputs
                    || saved.some((row) => typeof row?.extension !== "string" || !(row.type in types))) {
                    throw new Error("Invalid file outputs.");
                }
                rows = saved.map((row) => ({ extension: row.extension, type: row.type }));
                const count = FIXED_OUTPUTS + rows.length;
                while (node.outputs.length > count) node.removeOutput(node.outputs.length - 1);
                while (node.outputs.length < count) node.addOutput(`output${node.outputs.length - FIXED_OUTPUTS + 1}`, "*");
                rebuild();
                sync();
            }

            const add = node.addWidget("button", "Add file output", null, () => {
                if (rows.length >= maxOutputs) return;
                node.graph?.beforeChange?.();
                rows.push({ extension: "txt", type: "text" });
                node.addOutput(`output${rows.length}`, "*");
                rebuild();
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            add.serialize = false;
            add.tooltip = `Add another file output, up to ${maxOutputs} in total.`;
            buttons.push(add);

            const remove = node.addWidget("button", "Remove last file output", null, () => {
                if (rows.length <= 1) return;
                node.graph?.beforeChange?.();
                rows.pop();
                node.removeOutput(node.outputs.length - 1);
                rebuild();
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            remove.serialize = false;
            remove.tooltip = "Remove the last file output and its connections.";
            buttons.push(remove);

            node._restoreFileOutputs = restore;
            restore();
            resize();

            // Poll widget values so typed paths and programmatic changes both update the counts.
            const timer = setInterval(updateCounts, 500);
            // Count again on every run, so files added since then show up.
            const recount = () => { countsKey = undefined; };
            api.addEventListener("execution_start", recount);
            const onRemoved = node.onRemoved;
            node.onRemoved = function () {
                clearInterval(timer);
                api.removeEventListener("execution_start", recount);
                countsRequest?.abort();
                return onRemoved?.apply(this, arguments);
            };
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
            // Also covers pasted and cloned nodes.
            this._restoreFileOutputs?.();
            return result;
        };
    },
});
