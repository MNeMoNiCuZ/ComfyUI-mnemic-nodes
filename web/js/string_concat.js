import { app } from "../../../scripts/app.js";

const MIN_STRING_INPUTS = 2;

app.registerExtension({
    name: "mnemic.StringConcat",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const isStringConcat = nodeData.name === "StringConcat" ||
            nodeData.name === "🔗 String Concat / Append" ||
            nodeData.name.includes("String Concat");

        if (isStringConcat) {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                this.addStringInput();
                return result;
            };

            nodeType.prototype.getStringInputs = function () {
                return this.inputs.filter(i => i.name.startsWith("string_"));
            };

            nodeType.prototype.addStringInput = function () {
                const stringInputs = this.getStringInputs();
                const nextIndex = stringInputs.length;
                this.addInput(`string_${nextIndex}`, "STRING");
            };

            nodeType.prototype.removeUnusedInputsFromEnd = function () {
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    const input = this.inputs[i];
                    if (!input.name.startsWith("string_")) continue;

                    const stringInputCount = this.getStringInputs().length;
                    if (stringInputCount <= MIN_STRING_INPUTS) break;

                    if (!input.link) {
                        this.removeInput(i);
                        continue;
                    }
                    break;
                }
            };

            nodeType.prototype.stabilizeInputs = function () {
                this.removeUnusedInputsFromEnd();

                const stringInputs = this.getStringInputs();
                const lastStringInput = stringInputs[stringInputs.length - 1];

                if (lastStringInput && lastStringInput.link) {
                    this.addStringInput();
                }
            };

            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, slotIndex, isConnected, linkInfo, ioSlot) {
                onConnectionsChange?.apply(this, arguments);

                if (type === 1) {
                    this.stabilizeInputs();
                }
            };

            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (config) {
                onConfigure?.apply(this, arguments);

                setTimeout(() => {
                    this.stabilizeInputs();
                }, 100);
            };
        }
    }
});
