import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const names = ["Collapse Spaces", "Remove All Spaces", "Remove Line Prefix", "Remove Bracketed Content", "Find and Replace", "Remove From Start Until", "Remove From End Until"];
const field = (display_name) => ["STRING", { display_name, default: "", multiline: true, tooltip: `Example for ${display_name}.` }];
const inputs = [{}, {}, { text: field("Text") }, { pairs: field("Character Pairs") }, { find: field("Find"), replace: field("Replace With") }];
for (const delimiter of ["/", "."]) inputs.push({
    delimiter: ["STRING", { default: delimiter, multiline: false, tooltip: "Example: photo.png becomes photo." }],
    keep_delimiter: ["BOOLEAN", { default: false, display_name: "Keep Delimiter", tooltip: "Example: keep '.' to get photo." }],
});
const caseFormats = ["lowercase", "UPPERCASE", "Title Case", "Sentence case", "camelCase", "PascalCase", "snake_case", "CONSTANT_CASE", "kebab-case", "Train-Case", "dot.case", "tOGGLE cASE"];
const caseHelp = Object.fromEntries(caseFormats.map((format) => [format, `Example for ${format}.`]));
names.push("Case");
inputs.push({ case_format: ["COMBO", { options: caseFormats, default: "lowercase", display_name: "Format", tooltip: "Choose a case format.", case_tooltips: caseHelp }] });
const config = {
    case_tooltips: caseHelp,
    tooltip: "Example: red   fox becomes red fox.",
    operation_tooltips: Object.fromEntries(names.map((name) => [name, `Example for ${name}.`])),
    options: names.map((key, index) => ({ key, inputs: { required: inputs[index] } })),
};
let extension;
let disposed = 0;
const source = readFileSync(new URL("../web/js/string_cleaning.js", import.meta.url), "utf8");
runInNewContext(source.replace(/^import .*;\r?\n/gm, ""), {
    app: { registerExtension(value) { extension = value; } },
    ComfyWidgets: { STRING(node, name, input) {
        const widget = node.addWidget("text", name, input[1].default, () => {}, input[1]);
        widget.onRemove = () => disposed++;
        return { widget };
    } },
});

class Node {
    constructor() {
        this.widgets = [{ name: "operation", value: "Collapse Spaces" }, { name: "extra_operations", value: "[]" }];
        this.properties = {};
        this.size = [300, 200];
        this.onNodeCreated();
    }
    addWidget(type, name, value, callback, options) {
        const widget = { type, name, value, callback, options };
        this.widgets.push(widget);
        return widget;
    }
    setDirtyCanvas() {}
    setSize(size) { this.size = size; }
    computeSize() { return [300, this.widgets.length * 30]; }
    widget(name) { return this.widgets.find((widget) => widget.name === name); }
    select(name, value) {
        const widget = this.widget(name);
        widget.value = value;
        widget.callback?.(value);
    }
    click(name) { this.widget(name).callback(); }
    steps() { return JSON.parse(this.widget("extra_operations").value); }
}
extension.beforeRegisterNodeDef(Node, { name: "MNeMiC_StringCleaning", input: { required: { operation: ["COMFY_DYNAMICCOMBO_V3", config] } } });

test("adds ordered steps and keeps Add Operation at the bottom", () => {
    const node = new Node();
    node.click("Add Operation");
    node.select("Operation 2", "Remove Line Prefix");
    node.select("cleaning_2_text", "Chapter ");
    node.click("Add Operation");
    node.select("Operation 3", "Remove All Spaces");
    assert.deepEqual(node.steps(), [
        { operation: "Remove Line Prefix", text: "Chapter " },
        { operation: "Remove All Spaces" },
    ]);
    assert.equal(node.widgets.at(-1).name, "Add Operation");
    assert.equal(node.widget("cleaning_2_text").value, "Chapter ");
    assert.equal(node.widget("Operation 2").serialize, false);
    assert.equal(node.widget("extra_operations").hidden, true);
});

test("switching operation replaces its fields and exposes example tooltips", () => {
    const node = new Node();
    node.click("Add Operation");
    node.select("Operation 2", "Remove Line Prefix");
    const before = disposed;
    node.select("Operation 2", "Remove Bracketed Content");
    assert.ok(disposed > before);
    assert.equal(node.widget("cleaning_2_text"), undefined);
    assert.equal(node.widget("cleaning_2_pairs").label, "Character Pairs");
    assert.match(node.widget("cleaning_2_pairs").tooltip, /Example/);
    for (const name of names) {
        node.select("Operation 2", name);
        node.select("operation", name);
        assert.equal(node.widget("Operation 2").tooltip, config.operation_tooltips[name]);
        assert.equal(node.widget("operation").tooltip, config.operation_tooltips[name]);
    }
});

test("save/load restores separate values for repeated operations", () => {
    const node = new Node();
    for (const [index, find, replace] of [[2, "cat", "dog"], [3, "dog", "fox"]]) {
        node.click("Add Operation");
        node.select(`Operation ${index}`, "Find and Replace");
        node.select(`cleaning_${index}_find`, find);
        node.select(`cleaning_${index}_replace`, replace);
    }
    const restored = new Node();
    restored.properties = JSON.parse(JSON.stringify(node.properties));
    restored.onConfigure();
    restored.onConfigure();
    assert.deepEqual(restored.steps(), node.steps());
    assert.equal(restored.widget("cleaning_2_find").value, "cat");
    assert.equal(restored.widget("cleaning_3_find").value, "dog");
    assert.equal(restored.widgets.filter((widget) => widget.name === "Operation 2").length, 1);
    restored.click("Remove Last Operation");
    assert.equal(restored.steps().length, 1);
    assert.equal(restored.widget("Operation 3"), undefined);
});

test("delimiter operations create a toggle and preserve false and true across restoration", () => {
    const node = new Node();
    node.click("Add Operation");
    node.select("Operation 2", "Remove From End Until");
    assert.equal(node.widget("cleaning_2_delimiter").value, ".");
    assert.equal(node.widget("cleaning_2_keep_delimiter").type, "toggle");
    assert.equal(node.widget("cleaning_2_keep_delimiter").value, false);
    for (const keep of [true, false]) {
        node.select("cleaning_2_keep_delimiter", keep);
        node.select("cleaning_2_delimiter", "::");
        const restored = new Node();
        restored.properties = JSON.parse(JSON.stringify(node.properties));
        restored.onConfigure();
        assert.equal(restored.widget("cleaning_2_keep_delimiter").value, keep);
        assert.equal(restored.widget("cleaning_2_delimiter").value, "::");
        assert.equal(restored.steps()[0].keep_delimiter, keep);
        assert.match(restored.widget("cleaning_2_keep_delimiter").tooltip, /Example/);
    }
});

test("taller menus and option examples are limited to cleaning operations", () => {
    let registered;
    let observeMenus;
    let css;
    const menu = (labels) => {
        const classes = new Set();
        return {
            entries: labels.map((textContent) => ({ textContent })),
            classList: { contains: (name) => classes.has(name), add: (name) => classes.add(name), remove: (name) => classes.delete(name) },
            style: {},
            querySelectorAll() { return this.entries; },
            getBoundingClientRect() { return { bottom: 1000, height: 640 }; },
        };
    };
    const cleaning = menu(["Collapse Spaces", "Remove All Spaces"]);
    const unrelated = menu(["model A", "model B"]);
    runInNewContext(source.replace(/^import .*;\r?\n/gm, ""), {
        app: { registerExtension(value) { registered = value; } },
        ComfyWidgets: {},
        document: {
            createElement() { return {}; },
            head: { appendChild(style) { css = style.textContent; } },
            body: {}, querySelectorAll() { return [cleaning, unrelated]; },
        },
        MutationObserver: class { constructor(callback) { observeMenus = callback; } observe() {} },
        requestAnimationFrame: (callback) => callback(),
        getComputedStyle: () => ({ position: "fixed" }),
        window: { innerHeight: 800, scrollY: 0 },
    });
    registered.beforeRegisterNodeDef(class {}, { name: "MNeMiC_StringCleaning", input: { required: { operation: ["COMFY_DYNAMICCOMBO_V3", config] } } });
    registered.setup();
    observeMenus();
    assert.match(css, /640px, 75vh/);
    assert.equal(cleaning.classList.contains("mnemic-cleaning-menu"), true);
    assert.equal(unrelated.classList.contains("mnemic-cleaning-menu"), false);
    assert.equal(cleaning.entries[0].title, config.operation_tooltips["Collapse Spaces"]);
    assert.equal(cleaning.style.top, "148px");
    cleaning.entries = unrelated.entries;
    observeMenus();
    assert.equal(cleaning.classList.contains("mnemic-cleaning-menu"), false);
});

test("Case exposes every format as a nested combo with its own tooltip", () => {
    const node = new Node();
    node.click("Add Operation");
    node.select("Operation 2", "Case");
    const field = node.widget("cleaning_2_case_format");
    assert.equal(field.type, "combo");
    assert.deepEqual(field.options.values, caseFormats);
    for (const format of caseFormats) {
        node.select("cleaning_2_case_format", format);
        assert.equal(field.tooltip, caseHelp[format]);
        assert.equal(node.steps()[0].case_format, format);
    }
    const restored = new Node();
    restored.properties = JSON.parse(JSON.stringify(node.properties));
    restored.onConfigure();
    assert.equal(restored.widget("cleaning_2_case_format").value, "tOGGLE cASE");
});

test("old Lowercase and Uppercase steps migrate into Case without losing their format", () => {
    const graph = { nodes: [{
        type: "MNeMiC_StringCleaning",
        widgets_values: ["Uppercase", "[]"],
        properties: { mnemicCleaningOperations: [{ operation: "Lowercase" }, { operation: "Uppercase" }] },
    }] };
    extension.beforeConfigureGraph(graph);
    extension.beforeConfigureGraph(graph);
    assert.deepEqual(graph.nodes[0].widgets_values, ["Case", "UPPERCASE", "[]"]);
    const node = new Node();
    node.properties = graph.nodes[0].properties;
    node.onConfigure();
    assert.deepEqual(node.steps(), [
        { operation: "Case", case_format: "lowercase" },
        { operation: "Case", case_format: "UPPERCASE" },
    ]);
});
