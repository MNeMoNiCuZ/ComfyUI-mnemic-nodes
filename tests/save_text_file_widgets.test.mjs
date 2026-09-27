import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

let extension;
const source = readFileSync(new URL("../web/js/save_text_file.js", import.meta.url), "utf8");
runInNewContext(source.replace(/^import .*;\r?\n/, ""), {
    app: { registerExtension(value) { extension = value; } },
});
const plain = (value) => JSON.parse(JSON.stringify(value));

test("old numbered settings preserve filename, extension and suffix positions", () => {
    const node = { type: "MNeMiC_SaveTextFile", widgets_values: ["folder", "notes.md", "-", 3, "final", "txt"] };
    const graph = { nodes: [node] };
    extension.beforeConfigureGraph(graph);
    assert.deepEqual(plain(node.widgets_values), ["folder", "notes.md", "final", "txt", "increment filename", "hyphen", "001"]);
    extension.beforeConfigureGraph(graph);
    assert.deepEqual(plain(node.widgets_values), ["folder", "notes.md", "final", "txt", "increment filename", "hyphen", "001"]);
});

test("old settings without a counter select overwrite", () => {
    const node = { type: "MNeMiC_SaveTextFile", widgets_values: ["folder", "notes", "_", 0, "", "txt"] };
    extension.beforeConfigureGraph({ nodes: [node] });
    assert.deepEqual(plain(node.widgets_values), ["folder", "notes", "", "txt", "overwrite"]);
});

test("new settings and unrelated nodes are unchanged", () => {
    const graph = { nodes: [
        { type: "MNeMiC_SaveTextFile", widgets_values: ["folder", "notes.md", "", "", "ignore"] },
        { type: "OtherNode", widgets_values: ["folder", "notes", "_", 3, "", "txt"] },
    ] };
    const original = plain(graph);
    extension.beforeConfigureGraph(graph);
    assert.deepEqual(plain(graph), original);
});
