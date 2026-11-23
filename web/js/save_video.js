import { app } from "../../../scripts/app.js";

const PREFIX_SETTING = "MNeMiC.SaveVideo.FilenamePrefix";

// ComfyUI resolves %date:...% and %Node.widget% only for its own save nodes,
// and its pattern pairs up the % of strftime codes like %Y-%m-%d. Resolve
// just those two token shapes here and leave strftime codes for the server.
const REPLACEMENT_TOKEN = /%(?:date:[^%]+|[^%.]+\.[^%.]+)%/g;

// Same as importing scripts/utils.js, without its internal-module console warning.
const applyTextReplacements = (value) => window.comfyAPI?.utils?.applyTextReplacements?.(app, value) ?? value;

const setting = (id) => app.extensionManager?.setting?.get?.(id) ?? app.ui?.settings?.getSettingValue?.(id);

app.registerExtension({
  name: "MNeMiC.SaveVideo",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "MNeMiC_SaveVideo") return;
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);
      const widget = this.widgets?.find((w) => w.name === "filename_prefix");
      if (!widget) return r;
      // Loaded and pasted nodes get their saved value back in configure, after this.
      const prefix = setting(PREFIX_SETTING);
      if (typeof prefix === "string" && prefix) widget.value = prefix;
      widget.serializeValue = () =>
        typeof widget.value === "string"
          ? widget.value.replace(REPLACEMENT_TOKEN, applyTextReplacements)
          : widget.value;
      return r;
    };
  },
});
