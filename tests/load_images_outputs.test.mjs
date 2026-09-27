import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(new URL("../web/js/load_images.js", import.meta.url), "utf8");
const formats = ["full path with ext", "folder path without trailing /", "filename with ext", "folder path with trailing /"];
const aliases = {
    "full file path": formats[0],
    "path only": formats[1],
    "filename only": formats[2],
    "path only with trailing separator": formats[3],
    "folder path with trailing \\": formats[3],
};
const tooltips = Object.fromEntries(formats.map((format) => [format, `Tooltip for ${format}.`]));
let extension;
runInNewContext(source.replace(/^import .*;\r?\n/, ""), {
    app: { registerExtension(value) { extension = value; } },
});

class Node {
    constructor() {
        this.widgets = [
            { name: "seed", value: 0 },
            { name: "control_after_generate", value: "increment" },
            { name: "input_path", value: "images" },
            { name: "path_format", value: "full file path" },
            { name: "extra_path_formats", value: "[]" },
        ];
        this.outputs = ["image", "mask", "current_index", "total_count", "output1"]
            .map((name) => ({ name, links: null }));
        for (let index = 2; index <= 32; index++) this.outputs.push({ name: `output${index}`, links: null });
        this.size = [300, 500];
        this.onNodeCreated();
    }
    addWidget(type, name, value, callback, options) {
        const widget = { type, name, value, callback, options };
        this.widgets.push(widget);
        return widget;
    }
    addOutput(name, type) { this.outputs.push({ name, type, links: null }); }
    removeOutput(index) { this.outputs.splice(index, 1); }
    computeSize() { return [300, 100 + 20 * this.widgets.length]; }
    setSize(size) { this.size = size; }
    setDirtyCanvas() {}
    widget(name) { return this.widgets.find((widget) => widget.name === name); }
    click(name) { this.widget(name).callback(); }
    select(name, value) {
        const widget = this.widget(name);
        widget.value = value;
        widget.callback?.(value);
    }
    save() {
        return JSON.parse(JSON.stringify({
            outputs: this.outputs,
            widgets_values: this.widgets.filter((widget) => widget.serialize !== false).map((widget) => widget.value),
        }));
    }
    load(data) {
        this.outputs = data.outputs;
        this.widgets.filter((widget) => widget.serialize !== false).forEach((widget, index) => {
            if (index < data.widgets_values.length) widget.value = data.widgets_values[index];
        });
        this.onConfigure(data);
    }
}

extension.beforeRegisterNodeDef(Node, {
    name: "MNeMiC_LoadImagesFromPath",
    input: {
        required: { path_format: ["COMBO", { options: formats, format_aliases: aliases, format_tooltips: tooltips, tooltip: "Format of the first output." }] },
        optional: { extra_path_formats: ["STRING", { max_path_outputs: 32 }] },
    },
});

test("starts compact and adds independent path outputs without shifting original sockets", () => {
    const node = new Node();
    const original = node.outputs.slice();
    assert.equal(node.outputs.length, 5);
    assert.equal(node.widget("extra_path_formats").hidden, true);
    node.select("path_format", formats[3]);
    node.click("Add file/path output");
    node.click("Add file/path output");
    node.select("output3", formats[1]);
    assert.deepEqual(node.outputs.slice(0, 5), original);
    assert.deepEqual(node.outputs.map((output) => output.name), ["image", "mask", "current_index", "total_count", "output1", "output2", "output3"]);
    assert.equal(node.outputs[4].label, "output1");
    assert.equal(node.outputs[5].label, "output2");
    assert.equal(node.outputs[6].label, "output3");
    assert.equal(node.widget("path_format").label, "output1");
    assert.deepEqual(node.widget("output2").options.values, formats);
    assert.equal(node.widget("extra_path_formats").value, JSON.stringify([formats[2], formats[1]]));
});

test("workflow save/load preserves formats, links and socket positions", () => {
    const node = new Node();
    node.click("Add file/path output");
    node.select("output2", formats[1]);
    node.outputs[5].links = [17];
    const saved = node.save();
    assert.equal(saved.widgets_values.length, 5);
    const restored = new Node();
    restored.load(saved);
    restored.onConfigure(saved);
    assert.equal(restored.outputs.length, 6);
    assert.deepEqual(restored.outputs[5].links, [17]);
    assert.equal(restored.widget("output2").value, formats[1]);
    assert.equal(restored.widgets.filter((widget) => widget.name === "output2").length, 1);
    assert.deepEqual(restored.save(), saved);
});

test("older five-output workflows retain their first format", () => {
    const node = new Node();
    const saved = node.save();
    saved.widgets_values = [3, "increment", "images", "filename only"];
    saved.outputs = ["image", "mask", "path/file output", "current_index", "total_count"].map((name) => ({ name, links: null }));
    node.load(saved);
    assert.equal(node.outputs.length, 5);
    assert.equal(node.outputs[4].label, "output1");
    assert.equal(node.widget("path_format").value, formats[2]);
    assert.equal(node.outputs[2].name, "current_index");
});

test("removing an extra output keeps remaining links and permits adding it again", () => {
    const node = new Node();
    node.click("Add file/path output");
    node.outputs[5].links = [19];
    node.click("Add file/path output");
    node.click("Remove last file/path output");
    assert.deepEqual(node.outputs[5].links, [19]);
    node.click("Remove last file/path output");
    node.click("Remove last file/path output");
    assert.equal(node.outputs.length, 5);
    assert.equal(node.widget("extra_path_formats").value, "[]");
    node.click("Add file/path output");
    assert.equal(node.outputs[5].label, "output2");
});

test("output count stays inside the backend schema", () => {
    const node = new Node();
    for (let index = 0; index < 40; index++) node.click("Add file/path output");
    assert.equal(node.outputs.length, 36);
    assert.equal(JSON.parse(node.widget("extra_path_formats").value).length, 31);
});

test("legacy workflow links follow reordered outputs for array and object link formats", () => {
    for (const objectLinks of [false, true]) {
        const graph = {
            nodes: [{ id: 7, type: "MNeMiC_LoadImagesFromPath", outputs: [
                "image", "mask", "path/file output", "current_index", "total_count", "path/file output 2",
            ].map((name) => ({ name })) }],
            links: [2, 3, 4, 5].map((slot, index) => objectLinks
                ? { id: index, origin_id: 7, origin_slot: slot, target_id: 8, target_slot: index }
                : [index, 7, slot, 8, index, "STRING"]),
        };
        extension.beforeConfigureGraph(graph);
        extension.beforeConfigureGraph(graph);
        assert.equal(graph.nodes[0].outputs[4].name, "path/file output");
        assert.deepEqual(graph.links.map((link) => objectLinks ? link.origin_slot : link[2]), [4, 2, 3, 5]);
    }
});

test("pasted legacy node updates live connections when its outputs move", () => {
    const node = new Node();
    const links = new Map([[10, { origin_slot: 2 }], [11, { origin_slot: 3 }], [12, { origin_slot: 4 }]]);
    node.graph = { _links: links };
    const data = node.save();
    data.outputs = ["image", "mask", "path/file output", "current_index", "total_count"].map((name, index) => ({
        name, links: index >= 2 ? [index + 8] : null,
    }));
    node.load(data);
    assert.deepEqual([...links.values()].map((link) => link.origin_slot), [4, 2, 3]);
});

test("each format has its own tooltip on both first and added dropdowns", () => {
    const node = new Node();
    node.click("Add file/path output");
    for (const format of formats) {
        node.select("path_format", format);
        node.select("output2", format);
        assert.equal(node.widget("path_format").tooltip, tooltips[format]);
        assert.equal(node.widget("output2").tooltip, tooltips[format]);
    }
});

test("saved old labels and opposite-platform slashes normalize to current choices", () => {
    const node = new Node();
    node.click("Add file/path output");
    node.click("Add file/path output");
    const saved = node.save();
    saved.widgets_values[3] = "filename only";
    saved.widgets_values[4] = JSON.stringify(["path only with trailing separator", "folder path with trailing \\"]);
    node.load(saved);
    assert.equal(node.widget("path_format").value, formats[2]);
    assert.equal(node.widget("output2").value, formats[3]);
    assert.equal(node.widget("output3").value, formats[3]);
    assert.equal(node.widget("extra_path_formats").value, JSON.stringify([formats[3], formats[3]]));
});
