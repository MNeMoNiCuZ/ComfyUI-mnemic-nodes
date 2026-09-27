import { app } from "../../../scripts/app.js";

function migrateWidgets(node) {
    const values = node.widgets_values;
    if (!Array.isArray(values) || values.length !== 6 || typeof values[3] !== "number") return;
    const [path, filename, separator, digits, suffix, extension] = values;
    node.widgets_values = [path, filename, suffix, extension, digits > 0 ? "increment filename" : "overwrite"];
    if (digits > 0) {
        const separators = { "_": "underscore", "-": "hyphen", " ": "space", "": "none" };
        node.widgets_values.push(separators[separator] ?? separator, "1".padStart(Math.min(digits, 4), "0"));
    }
}

app.registerExtension({
    name: "mnemic.SaveTextFile",
    beforeConfigureGraph(data) {
        function migrate(graph) {
            for (const node of graph.nodes ?? []) {
                if (node.type === "MNeMiC_SaveTextFile") migrateWidgets(node);
            }
            for (const subgraph of graph.definitions?.subgraphs ?? []) migrate(subgraph);
        }
        migrate(data);
    },
});
