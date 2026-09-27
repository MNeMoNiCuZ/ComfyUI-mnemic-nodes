import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

const operationHelp = new Map();
const legacyCase = { Lowercase: "lowercase", Uppercase: "UPPERCASE" };
const normalizeStep = (step) => legacyCase[step?.operation]
    ? { ...step, operation: "Case", case_format: legacyCase[step.operation] }
    : step;

app.registerExtension({
    name: "mnemic.StringCleaning",
    beforeConfigureGraph(data) {
        function migrate(graph) {
            for (const node of graph.nodes ?? []) {
                if (node.type !== "MNeMiC_StringCleaning") continue;
                const values = node.widgets_values;
                const format = legacyCase[values?.[0]];
                if (format) {
                    values[0] = "Case";
                    values.splice(1, 0, format);
                }
                const steps = node.properties?.mnemicCleaningOperations;
                if (Array.isArray(steps)) node.properties.mnemicCleaningOperations = steps.map(normalizeStep);
            }
            for (const subgraph of graph.definitions?.subgraphs ?? []) migrate(subgraph);
        }
        migrate(data);
    },
    setup() {
        const style = document.createElement("style");
        style.textContent = `
            .mnemic-cleaning-menu.litecontextmenu {
                max-height: min(640px, 75vh) !important;
                overflow-y: auto !important;
            }
            .mnemic-cleaning-menu .p-select-list-container,
            .mnemic-cleaning-menu .p-dropdown-items-wrapper {
                max-height: min(640px, 75vh) !important;
            }
            .mnemic-cleaning-menu .p-virtualscroller,
            .mnemic-cleaning-menu [data-pc-name="virtualscroller"] {
                height: min(640px, 75vh) !important;
                max-height: min(640px, 75vh) !important;
            }
        `;
        document.head.appendChild(style);
        // Match option text rather than changing every combo menu in ComfyUI.
        const updateMenus = () => {
            for (const menu of document.querySelectorAll(".litecontextmenu, .p-select-overlay, .p-dropdown-panel")) {
                const entries = [...menu.querySelectorAll('[role="option"], .litemenu-entry')];
                const matching = entries.filter((entry) => operationHelp.has(entry.textContent.trim()));
                if (matching.length < 2) {
                    menu.classList.remove("mnemic-cleaning-menu");
                    continue;
                }
                const fresh = !menu.classList.contains("mnemic-cleaning-menu");
                menu.classList.add("mnemic-cleaning-menu");
                for (const entry of matching) entry.title = operationHelp.get(entry.textContent.trim());
                if (fresh) requestAnimationFrame(() => {
                    const rect = menu.getBoundingClientRect();
                    if (rect.bottom > window.innerHeight - 12) {
                        const scroll = getComputedStyle(menu).position === "fixed" ? 0 : window.scrollY;
                        menu.style.top = `${Math.max(12, window.innerHeight - rect.height - 12) + scroll}px`;
                    }
                });
            }
        };
        new MutationObserver(updateMenus).observe(document.body, { childList: true, subtree: true });
    },
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MNeMiC_StringCleaning") return;
        const config = nodeData.input.required.operation[1];
        const tooltips = config.operation_tooltips;
        const options = config.options;
        const names = options.map((option) => option.key);
        for (const name of names) operationHelp.set(name, tooltips[name]);
        const caseTooltips = config.case_tooltips ?? {};
        for (const [name, help] of Object.entries(caseTooltips)) operationHelp.set(name, help);

        function tooltip(widget, help = tooltips) {
            Object.defineProperty(widget, "tooltip", {
                configurable: true,
                enumerable: true,
                get() { return help[widget.value] ?? config.tooltip; },
                set() {},
            });
        }

        function setup(node) {
            const first = node.widgets.find((widget) => widget.name === "operation");
            const storage = node.widgets.find((widget) => widget.name === "extra_operations");
            if (!first || !storage) return;
            tooltip(first);
            function attachCaseTooltip() {
                for (const widget of node.widgets) {
                    if (widget.name === "operation.case_format" || widget.name === "case_format") tooltip(widget, caseTooltips);
                }
            }
            const firstCallback = first.callback;
            first.callback = function () {
                const result = firstCallback?.apply(this, arguments);
                attachCaseTooltip();
                return result;
            };
            storage.hidden = true;
            storage.type = "hidden";
            storage.computeSize = () => [0, -4];
            storage.draw = () => {};

            let steps = [];
            let dynamicWidgets = [];
            const buttons = [];

            function sync() {
                storage.value = JSON.stringify(steps);
                // Properties also preserve the list when native DynamicCombo
                // children change the positions of serialized widgets.
                node.properties ??= {};
                node.properties.mnemicCleaningOperations = JSON.parse(storage.value);
                node.setDirtyCanvas(true, true);
            }

            function resize() {
                node.setSize([node.size[0], node.computeSize()[1]]);
                node.setDirtyCanvas(true, true);
            }

            function clearWidgets() {
                for (const widget of dynamicWidgets) widget.onRemove?.();
                node.widgets = node.widgets.filter((widget) => !dynamicWidgets.includes(widget) && !buttons.includes(widget));
                dynamicWidgets = [];
            }

            function rebuild() {
                clearWidgets();
                steps.forEach((step, index) => {
                    const combo = node.addWidget("combo", `Operation ${index + 2}`, step.operation, (value) => {
                        step.operation = value;
                        sync();
                        rebuild();
                        resize();
                    }, { values: names, serialize: false });
                    combo.serialize = false;
                    tooltip(combo);
                    dynamicWidgets.push(combo);

                    const option = options.find((item) => item.key === step.operation);
                    if (!option) throw new Error(`Unknown cleaning operation: ${step.operation}`);
                    for (const [id, input] of Object.entries(option.inputs.required ?? {})) {
                        const details = input[1];
                        const widgetName = `cleaning_${index + 2}_${id}`;
                        const widget = input[0] === "BOOLEAN"
                            ? node.addWidget("toggle", widgetName, step[id] ?? details.default ?? false, null, { serialize: false })
                            : (input[0] === "COMBO" || Array.isArray(input[0]))
                            ? node.addWidget("combo", widgetName, step[id] ?? details.default, null, {
                                values: Array.isArray(input[0]) ? input[0] : details.options, serialize: false,
                            })
                            : ComfyWidgets.STRING(
                                node, widgetName,
                                ["STRING", { ...details, default: step[id] ?? details.default ?? "", socketless: true }],
                                app,
                            ).widget;
                        widget.label = details.display_name ?? id;
                        widget.tooltip = details.tooltip;
                        if (details.case_tooltips) tooltip(widget, details.case_tooltips);
                        widget.serialize = false;
                        widget.options ??= {};
                        widget.options.serialize = false;
                        const originalCallback = widget.callback;
                        widget.callback = function (value) {
                            originalCallback?.apply(this, arguments);
                            step[id] = value;
                            sync();
                        };
                        dynamicWidgets.push(widget);
                    }
                });
                node.widgets.push(...buttons);
            }

            function restore() {
                const saved = node.properties?.mnemicCleaningOperations ?? JSON.parse(storage.value || "[]");
                if (!Array.isArray(saved)) throw new Error("Invalid additional cleaning operations.");
                const normalized = saved.map(normalizeStep);
                if (normalized.some((step) => !step || !names.includes(step.operation))) {
                    throw new Error("Invalid additional cleaning operations.");
                }
                steps = JSON.parse(JSON.stringify(normalized));
                rebuild();
                attachCaseTooltip();
                sync();
            }

            const remove = node.addWidget("button", "Remove Last Operation", null, () => {
                if (!steps.length) return;
                node.graph?.beforeChange?.();
                steps.pop();
                rebuild();
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            remove.serialize = false;
            remove.tooltip = "Remove the last added step. Example: remove Collapse Spaces while keeping the earlier Trim Line Starts step.";
            buttons.push(remove);

            const add = node.addWidget("button", "Add Operation", null, () => {
                node.graph?.beforeChange?.();
                steps.push({ operation: "Collapse Spaces" });
                rebuild();
                sync();
                resize();
                node.graph?.afterChange?.();
            }, { serialize: false });
            add.serialize = false;
            add.tooltip = "Append a cleaning step. Example: remove a line prefix, then trim the remaining spaces.";
            buttons.push(add);

            node._restoreCleaningOperations = restore;
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
            this._restoreCleaningOperations?.();
            return result;
        };
    },
});
