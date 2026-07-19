import { app } from "../../../scripts/app.js";

app.registerExtension({
  name: "MNeMiC.Settings",
  settings: [
    {
      id: "MNeMiC.FuzzySearch",
      name: "Enable fuzzy search",
      category: ["⚡MNeMiC Nodes", "General", "Fuzzy Search"],
      tooltip: "Allow LoRA Tag Loader, Wildcard Processor and Batch Wildcard Sampler to fall back to fuzzy (partial/reordered word) filename matching when no exact match is found. Disabled by default so only exact, base, numbered and prefix/contains matches are used.",
      type: "boolean",
      defaultValue: false,
    },
  ],
});
