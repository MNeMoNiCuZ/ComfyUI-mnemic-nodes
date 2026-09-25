import { app } from "../../../scripts/app.js";
import {
    WildcardHighlighter,
    getWidgetTextarea,
    setWildcardHighlightOptionsProvider,
} from "./wildcard_highlight_core.js";

// Every node + text widget that accepts wildcard syntax. To add wildcard
// highlighting to another node, add its node id and widget name(s) here, or
// call attachWildcardHighlight(node, widgetName) from that node's own script.
export const WILDCARD_TEXT_WIDGETS = {
    MNeMiC_WildcardProcessor: ["wildcard_string"],
    MNeMiC_WildcardProcessorAdvanced: ["wildcard_string"],
    MNeMiC_BatchWildcardSampler: ["text", "negative"],
    MNeMiC_PromptPropertyExtractor: ["input_string"],
};

const SETTING_PREFIX = "MNeMiC.WildcardHighlight.";

function getSetting(name, fallback) {
    const id = SETTING_PREFIX + name;
    const value = app.extensionManager?.setting?.get?.(id) ?? app.ui?.settings?.getSettingValue?.(id);
    return value ?? fallback;
}

setWildcardHighlightOptionsProvider(() => ({
    enabled: getSetting("Enabled", true),
    palette: getSetting("Palette", "Pastel"),
    style: getSetting("Style", "Background"),
    coloring: getSetting("Coloring", "Each block"),
    intensity: getSetting("Intensity", 35),
    emphasizeSyntax: getSetting("EmphasizeSyntax", true),
    markErrors: getSetting("MarkErrors", true),
    customColors: getSetting("CustomColors", ""),
}));

/**
 * Attach wildcard highlighting to one multiline text widget of a node.
 * Safe to call more than once for the same widget.
 */
export function attachWildcardHighlight(node, widgetName) {
    node.__mnmWildcardHighlighters ??= new Map();
    if (node.__mnmWildcardHighlighters.has(widgetName)) return;
    const widget = node.widgets?.find((w) => w.name === widgetName);
    const textarea = getWidgetTextarea(widget);
    if (!textarea) return;
    node.__mnmWildcardHighlighters.set(widgetName, new WildcardHighlighter(textarea));

    if (node.__mnmWildcardHighlightHooked) return;
    node.__mnmWildcardHighlightHooked = true;

    // The textarea is mounted lazily and its value can be set from code
    // (loading a workflow, pasting nodes), so re-check on every node draw.
    const onDrawForeground = node.onDrawForeground;
    node.onDrawForeground = function () {
        for (const highlighter of this.__mnmWildcardHighlighters.values()) highlighter.update();
        return onDrawForeground?.apply(this, arguments);
    };

    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
        for (const highlighter of this.__mnmWildcardHighlighters.values()) highlighter.destroy();
        this.__mnmWildcardHighlighters.clear();
        return onRemoved?.apply(this, arguments);
    };
}

app.registerExtension({
    name: "MNeMiC.WildcardHighlight",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const widgetNames = WILDCARD_TEXT_WIDGETS[nodeData.name];
        if (!widgetNames) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            for (const name of widgetNames) attachWildcardHighlight(this, name);
            return result;
        };
    },
});
