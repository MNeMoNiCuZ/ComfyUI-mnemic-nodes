export async function copyText(value) {
    try {
        await navigator.clipboard.writeText(value);
    } catch {
        // Remote ComfyUI sessions over plain HTTP may lack the Clipboard API.
        const previousFocus = document.activeElement;
        const field = document.createElement("textarea");
        field.value = value;
        field.style.cssText = "position:fixed;opacity:0;pointer-events:none";
        document.body.append(field);
        try {
            field.select();
            if (!document.execCommand("copy")) throw new Error("Clipboard access was denied.");
        } finally {
            field.remove();
            previousFocus?.focus?.({ preventScroll: true });
        }
    }
}

export function copyOutputButton(getOutput) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Copy Output";
    button.style.cssText = "flex:none;margin-left:auto;padding:1px 6px;border:1px solid var(--border-color,#555);border-radius:4px;background:var(--comfy-input-bg,#292929);color:var(--fg-color,#ddd);font:11px/1.4 system-ui;white-space:nowrap;cursor:pointer";
    let reset;
    button.addEventListener("click", async event => {
        event.stopPropagation();
        const output = getOutput();
        if (!output) return;
        try {
            await copyText(output);
            button.textContent = "Copied";
        } catch {
            button.textContent = "Copy failed";
        }
        clearTimeout(reset);
        reset = setTimeout(() => { button.textContent = "Copy Output"; }, 1500);
    });
    return button;
}
