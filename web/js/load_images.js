import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const EXTRA_WIDGET = "extra_path_formats";
const formatHelp = new Map();

function addImagePreview(node, kind = "images") {
    const isPair = kind.startsWith("pair_");
    const container = document.createElement("div");
    // Keep image dimensions out of DOM layout measurement. The node owns the
    // available rectangle; the image fits inside it without changing node size.
    container.style.cssText = "position:relative; height:100%; width:100%; min-width:0; min-height:0; overflow:hidden; contain:size layout;";
    const image = document.createElement("img");
    image.alt = "Selected image";
    image.title = "Image selected by the current seed.";
    image.style.cssText = "position:absolute; inset:0; width:100%; height:100%; object-fit:contain; object-position:center; display:none;";
    container.append(image);
    const widget = node.addDOMWidget("image_preview", "mnemic_image_preview", container, {
        serialize: false, hideOnZoom: false,
        getMinHeight: () => 120,
        getValue: () => "", setValue: () => {},
    });
    widget.serialize = false;
    const widgets = [widget];
    const caption = isPair ? document.createElement("div") : null;
    let captionObserver;
    if (caption) {
        node.properties ??= {};
        const textHeight = () => node.properties.mnmPairTextPreviewHeight ?? 120;
        const textContainer = document.createElement("div");
        textContainer.style.cssText = "display:flex; flex-direction:column; flex:0 0 auto; width:100%; font-size:12px; color:var(--input-text, #ddd);";
        const header = document.createElement("div");
        header.textContent = "text_preview";
        header.title = "Text for the selected image.";
        header.style.cssText = "height:22px; box-sizing:border-box; padding:2px 4px; opacity:.8;";
        caption.title = "Text for the selected image.";
        caption.setAttribute("aria-label", "text_preview");
        caption.style.cssText = "flex:none; box-sizing:border-box; min-height:40px; resize:vertical; overflow:auto; white-space:pre-wrap; overflow-wrap:break-word; font-family:monospace; line-height:1.5; padding:4px 6px; border-radius:6px; background:var(--comfy-input-bg, rgba(0,0,0,.25));";
        caption.style.height = `${textHeight()}px`;
        textContainer.append(header, caption);
        textContainer.addEventListener("pointerdown", (event) => event.stopPropagation());
        const textWidget = node.addDOMWidget("text_preview", "mnemic_text_preview", textContainer, {
            serialize: false, hideOnZoom: false,
        });
        textWidget.serialize = false;
        // Match the wildcard/LLM text panels: a fixed widget row with a separately resizable body.
        textWidget.computeSize = (width) => [width ?? node.size[0], 22 + textHeight()];
        textWidget.computeLayoutSize = undefined;
        widgets.push(textWidget);
        captionObserver = new ResizeObserver(() => {
            if (!caption.isConnected || !caption.offsetHeight || caption.offsetHeight === textHeight()) return;
            node.properties.mnmPairTextPreviewHeight = caption.offsetHeight;
            node.setDirtyCanvas?.(true, true);
        });
        captionObserver.observe(caption);
        const onConfigure = node.onConfigure;
        node.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            caption.style.height = `${textHeight()}px`;
            return result;
        };
    }

    let previous;
    let controller;
    let objectUrl;
    let revision = 0;
    const clear = () => {
        image.style.display = "none";
        image.removeAttribute("src");
        if (caption) caption.textContent = "";
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = undefined;
    };
    async function update() {
        const pathName = "input_path";
        const names = [pathName, "seed", "include_subfolders", "text_format_extension", "force_reload"];
        const values = Object.fromEntries(names.map((name) => [name, node.widgets.find((item) => item.name === name)?.value]));
        values.input_path = values[pathName];
        values.kind = kind;
        for (const name of Object.keys(values)) if (values[name] === undefined) delete values[name];
        // Connected values are not available until execution; do not show a stale widget selection.
        const connected = (name) => node.inputs?.some((input) => input.name === name && input.link != null);
        const directImages = connected("image_input") && (!kind.startsWith("pair_") || connected("text_input"));
        const linked = directImages || names.some(connected);
        const key = JSON.stringify([values, linked]);
        if (key === previous) return;
        previous = key;
        const current = ++revision;
        controller?.abort();
        clear();
        if (linked || !values.input_path || !Number.isFinite(Number(values.seed))) return;
        controller = new AbortController();
        try {
            const query = new URLSearchParams(values);
            const response = await api.fetchApi(`/mnemic/load-images/preview?${query}`, { signal: controller.signal });
            if (!response.ok) return;
            if (isPair) {
                const data = await response.json();
                if (current !== revision) return;
                caption.textContent = data.text ?? "";
                if (data.image) {
                    image.src = data.image;
                    image.style.display = "block";
                }
                return;
            }
            const blob = await response.blob();
            if (current !== revision) return;
            objectUrl = URL.createObjectURL(blob);
            image.src = objectUrl;
            image.style.display = "block";
        } catch (error) {
            if (error.name !== "AbortError") console.warn("Image preview failed", error);
        }
    }
    // Observe programmatic seed increments as well as direct widget edits.
    const timer = setInterval(update, 300);
    if (kind !== "images") {
        const onExecuted = node.onExecuted;
        node.onExecuted = function (message) {
            const result = onExecuted?.call(this, { ...message, images: [] });
            node.imgs = null;
            const names = ["input_path", "seed", "image_input", "text_input"];
            if (node.inputs?.some((input) => names.includes(input.name) && input.link != null)) {
                ++revision;
                controller?.abort();
                clear();
                if (caption) caption.textContent = message.pair_text?.[0] ?? "";
                const preview = message.images?.[0];
                if (preview) {
                    image.src = api.apiURL(`/view?${new URLSearchParams(preview)}`);
                    image.style.display = "block";
                }
            } else {
                previous = undefined;
                void update();
            }
            return result;
        };
    }
    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
        clearInterval(timer);
        captionObserver?.disconnect();
        ++revision;
        controller?.abort();
        clear();
        return onRemoved?.apply(this, arguments);
    };
    return widgets;
}

function moveLegacyOutput(outputs) {
    if (!["image_path", "path/file output"].includes(outputs?.[2]?.name)) return false;
    outputs.splice(4, 0, outputs.splice(2, 1)[0]);
    return true;
}

app.registerExtension({
    name: "mnemic.LoadImagesFromPath",
    setup() {
        const updateMenus = () => {
            for (const menu of document.querySelectorAll(".litecontextmenu, .p-select-overlay, .p-dropdown-panel")) {
                const entries = [...menu.querySelectorAll('[role="option"], .litemenu-entry')];
                for (const entry of entries) {
                    const help = formatHelp.get(entry.textContent.trim());
                    if (help) entry.title = help;
                }
            }
        };
        new MutationObserver(updateMenus).observe(document.body, { childList: true, characterData: true, subtree: true });
    },
    beforeConfigureGraph(data) {
        function migrate(graph) {
            for (const node of graph.nodes ?? []) {
                if (["MNeMiC_LoadTextImagePairSingle", "MNeMiC_LoadTextImagePairsList"].includes(node.type)) {
                    for (const input of node.inputs ?? []) {
                        if (input.name === "folder_path") input.name = "input_path";
                    }
                }
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
        const previewKind = {
            MNeMiC_LoadTextImagePairSingle: "pair_single",
            MNeMiC_LoadTextImagePairsList: "pair_list",
            MNeMiC_MetadataExtractorSingle: "metadata_single",
            MNeMiC_MetadataExtractorList: "metadata_list",
        }[nodeData.name];
        if (previewKind) {
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                for (const input of this.inputs ?? []) {
                    if (input.name === "folder_path") input.name = "input_path";
                }
                return onConfigure?.apply(this, arguments);
            };
            const onCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onCreated?.apply(this, arguments);
                addImagePreview(this, previewKind);
                return result;
            };
            return;
        }
        if (nodeData.name !== "MNeMiC_LoadImagesFromPath") return;
        const formatInput = nodeData.input.required.path_format;
        const formats = Array.isArray(formatInput[0]) ? formatInput[0] : formatInput[1].options;
        const aliases = formatInput[1].format_aliases ?? {};
        const tooltips = formatInput[1].format_tooltips ?? {};
        for (const [format, help] of Object.entries(tooltips)) formatHelp.set(format, help);
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
                node.setSize([node.size[0], Math.max(node.size[1], node.computeSize()[1])]);
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

            buttons.push(...addImagePreview(node));

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
