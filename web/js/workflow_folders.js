import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import {
    WORKFLOW_PREFIX, basename, isWithin, joinPath, nativeFolderPaths,
    parentPath, planWorkflowMove, reconcileWorkflowMove, validateName,
} from "./workflow_folder_core.js";

// Enhance only the native Workflows tab. No Vue component replacement, bundle
// imports, global drag interception, or changes to ComfyUI's source files.
// DOM selectors are isolated here because the sidebar has no folder extension
// hook. The supported state API is app.extensionManager.workflow.
const SETTING = "MNeMiC.WorkflowFolders.Enabled";
const PANEL = '[data-testid="workflows-sidebar"].workflows-sidebar-tab';
const BROWSE = ".comfyui-workflows-browse";
const ROW = ".p-tree-node-content";
const NODE = '.tree-node[data-testid^="tree-node-root/"]';
const MIME = "application/x-mnemic-workflow-path";
const ENDPOINT = "/mnemic/workflows/folders";
let controller = null;
let mountObserver = null;
let unsubscribe = null;
let mountFrame = 0;

function enabled() {
    return app.extensionManager?.setting?.get(SETTING) !== false;
}

function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function button(label, icon, action, text = "") {
    const node = element("button", "mnm-wf-button", text);
    node.type = "button";
    node.title = label;
    node.setAttribute("aria-label", label);
    if (icon) node.prepend(element("i", `pi ${icon}`));
    node.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        action(event);
    });
    return node;
}

function addStyles() {
    if (document.getElementById("mnm-workflow-folder-styles")) return;
    const style = element("style");
    style.id = "mnm-workflow-folder-styles";
    style.textContent = `
        .mnm-wf-tools { display: inline-flex; align-items: center; flex: none; margin-left: auto; padding-right: 16px; }
        .mnm-wf-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px;
            padding: 6px 8px; border: 0; border-radius: 5px; background: transparent;
            color: inherit; cursor: pointer; font: inherit; font-size: 12px; }
        .mnm-wf-button:hover, .mnm-wf-button:focus-visible { background: var(--p-content-hover-background, #80808025); }
        .mnm-wf-button:focus-visible { outline: 1px solid var(--p-primary-color, #7ba9d4); }
        .mnm-wf-button:disabled { opacity: .45; cursor: default; }
        .mnm-wf-drop { outline: 1px solid var(--p-primary-color, #7ba9d4); background: #7ba9d420; }
        .mnm-wf-folder-action { padding: 3px 6px; margin-left: auto; opacity: .45; }
        [data-testid="workflows-sidebar"] .tree-folder .node-actions:has(> .mnm-wf-folder-action) { opacity: 1 !important; }
        .p-tree-node-content:hover .mnm-wf-folder-action, .mnm-wf-folder-action:focus-visible { opacity: 1; }
        .mnm-wf-extra-tree { padding: 0 8px; }
        @media (min-width: 1536px) { .mnm-wf-extra-tree { padding: 0 16px; } }
        .mnm-wf-extra-tree > ul { list-style: none; padding: 0; margin: 0; }
        .mnm-wf-extra .p-tree-node-content { cursor: pointer; }
        .mnm-wf-extra .p-tree-node-toggle-button { padding: 0; font-size: 14px; flex: none;
            width: var(--p-tree-node-toggle-button-size, 28px); height: var(--p-tree-node-toggle-button-size, 28px);
            color: var(--p-tree-node-toggle-button-color, #a1a1aa); }
        .mnm-wf-extra .tree-explorer-node-label { display: flex; align-items: center; flex: 1; min-width: 0;
            margin-left: var(--p-tree-node-gap, 4px); }
        .mnm-wf-extra .tree-node { display: flex; align-items: center; justify-content: space-between; width: 100%; }
        .mnm-wf-extra .p-tree-node-children { padding: var(--p-tree-node-children-padding, 0 0 0 16px); list-style: none; }
        .mnm-wf-menu { position: fixed; z-index: 10020; min-width: 190px; padding: 5px;
            background: var(--p-menu-background, var(--comfy-menu-bg, #252525));
            color: var(--p-menu-color, var(--fg-color, #ddd));
            border: 1px solid #80808060; border-radius: 6px; box-shadow: 0 4px 18px #0006; }
        .mnm-wf-menu .mnm-wf-button { width: 100%; justify-content: flex-start; font-size: 13px;
            padding: 8px 10px; color: var(--p-menu-color, var(--fg-color, #ddd)); }
        .mnm-wf-menu .mnm-wf-button > i { width: 16px; flex: none; }
        .mnm-wf-dialog { width: 380px; max-width: calc(100vw - 32px); border: 1px solid #80808060;
            border-radius: 8px; background: var(--p-content-background, var(--comfy-menu-bg, #252525));
            color: var(--p-content-color, var(--fg-color, #ddd)); padding: 20px; }
        .mnm-wf-dialog::backdrop { background: #0007; }
        .mnm-wf-dialog h3 { margin: 0 0 16px; font-size: 17px; }
        .mnm-wf-dialog label { display: block; margin: 12px 0 5px; font-size: 13px; }
        .mnm-wf-dialog input, .mnm-wf-dialog select { width: 100%; box-sizing: border-box; padding: 8px;
            background: var(--comfy-input-bg, #171717); color: inherit; border: 1px solid #80808080; border-radius: 4px; }
        .mnm-wf-dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
        .mnm-wf-dialog-actions .mnm-wf-button { border: 1px solid #80808060; }
        .mnm-wf-dialog-error { margin-top: 8px; color: var(--p-red-400, #f08080); font-size: 12px; }
    `;
    document.head.append(style);
}

class WorkflowFolders {
    constructor(panel) {
        this.panel = panel;
        this.user = api.user;
        this.info = { path: "", folders: [], can_open: false };
        this.folders = new Set();
        this.expanded = new Set();
        this.originalDraggable = new Map();
        this.events = new AbortController();
        this.alive = true;
        this.busy = false;
        this.infoRevision = 0;
        this.frame = 0;
        this.refreshTimer = 0;
        this.tools = element("div", "mnm-wf-tools");
        this.tools.setAttribute("aria-label", "Workflow folder tools");
        this.tools.append(button("Create workflow folder", "pi-folder-plus", () => this.createDialog("")));
        // Status is kept for operation errors, while notifications use native
        // toasts. No persistent toolbar/status row takes space above Browse.
        this.status = element("div");
        this.observer = new MutationObserver(() => this.schedule());
        this.observer.observe(panel, { childList: true, subtree: true, attributes: true, attributeFilter: ["aria-expanded"] });
        for (const [event, handler] of Object.entries({
            click: e => {
                if (e.target instanceof Element && e.target.closest('[data-testid="workflows-refresh-button"]') && !this.busy) {
                    // Refresh directories independently of the native file-only
                    // store action, including empty directories at the root.
                    clearTimeout(this.refreshTimer);
                    this.refreshInfo();
                }
            },
            contextmenu: e => this.onContextMenu(e),
            dragstart: e => this.onDragStart(e),
            dragover: e => this.onDragOver(e),
            dragleave: e => this.onDragLeave(e),
            drop: e => this.onDrop(e),
            dragend: () => this.clearDrag(),
        })) panel.addEventListener(event, handler, { capture: true, signal: this.events.signal });
        this.schedule();
        this.refreshInfo();
    }

    get store() { return app.extensionManager?.workflow; }

    setStatus(message = "", error = false) {
        this.status.textContent = message;
        this.status.dataset.error = String(error);
        if (message && message !== this.lastMessage && this.alive) {
            app.extensionManager?.toast?.add?.({
                severity: error ? "error" : "info", summary: "Workflow folders",
                detail: message, life: error ? 6000 : 2500,
            });
        }
        this.lastMessage = message;
    }

    async request(action, body) {
        const response = await api.fetchApi(action ? `${ENDPOINT}/${action}` : ENDPOINT, action ? {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
        } : { cache: "no-store" });
        if (response.status === 404 && !action) {
            throw new Error("Restart ComfyUI to enable workflow folder tools.");
        }
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `Folder operation failed (${response.status}).`);
        return data;
    }

    async refreshInfo() {
        const revision = ++this.infoRevision;
        try {
            const info = await this.request();
            if (!this.alive || revision !== this.infoRevision || this.user !== api.user) return false;
            if (!Array.isArray(info.folders) || typeof info.path !== "string") {
                throw new Error("The server returned an invalid workflow folder listing.");
            }
            this.info = info;
            if (!this.busy) this.setStatus();
            this.schedule();
            return true;
        } catch (error) {
            if (this.alive && revision === this.infoRevision) this.setStatus(error.message, true);
            return false;
        }
    }

    queueRefresh() {
        if (this.busy) return; // The operation refreshes after all tabs are reconciled.
        clearTimeout(this.refreshTimer);
        this.refreshTimer = setTimeout(() => this.refreshInfo(), 150);
    }

    schedule() {
        if (this.frame || !this.alive) return;
        this.frame = requestAnimationFrame(() => {
            this.frame = 0;
            try { this.decorate(); }
            catch (error) { this.setStatus(`Workflow folder tools: ${error.message}`, true); }
        });
    }

    pathFor(node) {
        return node?.getAttribute("data-testid")?.slice("tree-node-root/".length) ?? null;
    }

    rowAt(target) {
        if (!(target instanceof Element)) return null;
        const row = target.closest(ROW);
        if (!row || !row.closest(BROWSE) || !this.panel.contains(row)) return null;
        const node = row.querySelector(NODE);
        if (!node) return null;
        return { row, node, path: this.pathFor(node), folder: node.classList.contains("tree-folder") };
    }

    decorate() {
        const browse = this.panel.querySelector(BROWSE);
        if (!browse || !this.store) return;
        const browseRow = browse.firstElementChild;
        if (browseRow && this.tools.parentElement !== browseRow) browseRow.append(this.tools);
        const nativePaths = nativeFolderPaths(this.store.persistedWorkflows ?? []);
        // Existing native folders are real paths too, including directory links
        // which older backend listings omitted. Give every native row actions.
        const folders = this.folders = new Set([...this.info.folders, ...nativePaths]);
        // If native workflows have appeared in an injected folder, remove its
        // old empty-folder row; Vue owns the replacement and its children.
        for (const extra of browse.querySelectorAll(".mnm-wf-extra")) {
            if (!folders.has(extra.dataset.path) || nativePaths.has(extra.dataset.path)) extra.remove();
        }
        // Prefer Vue's tree if an empty-root fallback from an earlier render
        // is still present. Both may coexist for one observer tick.
        let root = browse.querySelector('.tree-explorer ul[role="tree"]')
            ?? browse.querySelector('.mnm-wf-extra-tree ul[role="tree"]');
        if (!root && folders.size) {
            let extraTree = browse.querySelector(".mnm-wf-extra-tree");
            if (!extraTree) {
                extraTree = element("div", "mnm-wf-extra-tree");
                root = element("ul", "p-tree-root-children");
                root.setAttribute("role", "tree");
                root.setAttribute("aria-label", "Workflow folders");
                extraTree.append(root);
                browse.append(extraTree);
            } else root = extraTree.querySelector("ul");
        }
        // Remove an empty-root fallback after a native tree has mounted.
        const fallback = browse.querySelector(".mnm-wf-extra-tree");
        if (fallback && (!folders.size || (root && !fallback.contains(root)))) fallback.remove();
        if (!root) return;
        const rows = new Map();
        for (const node of browse.querySelectorAll(`${NODE}.tree-folder`)) {
            rows.set(this.pathFor(node), node.closest('li[role="treeitem"]'));
        }
        const ensureFolder = path => {
            if (rows.has(path)) return rows.get(path);
            // A native folder can be missing from the DOM because its parent
            // is collapsed. Never replace that native branch with a fake one.
            if (nativePaths.has(path)) return null;
            const parent = parentPath(path);
            let group = root;
            if (parent) {
                const parentItem = ensureFolder(parent);
                if (!parentItem || parentItem.getAttribute("aria-expanded") !== "true") return null;
                group = parentItem.querySelector(':scope > ul[role="group"]');
                if (!group) return null;
            }
            const item = this.emptyFolder(path);
            // Sort only new rows; preserve native workflow ordering and state.
            const before = [...group.children].find(child => {
                const folderNode = child.querySelector(":scope > .p-tree-node-content .tree-folder");
                return !folderNode || basename(this.pathFor(folderNode)).localeCompare(basename(path), undefined, { sensitivity: "base" }) > 0;
            });
            group.insertBefore(item, before ?? null);
            rows.set(path, item);
            return item;
        };
        for (const path of [...folders].sort((a, b) => a.split("/").length - b.split("/").length || a.localeCompare(b))) ensureFolder(path);
        for (const [path, item] of rows) {
            if (!item || !folders.has(path)) continue;
            const row = item.querySelector(`:scope > ${ROW}`);
            if (!row) continue;
            if (!this.originalDraggable.has(row)) {
                this.originalDraggable.set(row, row.getAttribute("draggable"));
                row.draggable = true;
            }
            if (!row.querySelector(".mnm-wf-folder-action")) {
                const action = button(`Actions for folder ${path}`, "pi-ellipsis-v", event => {
                    const box = event.currentTarget.getBoundingClientRect();
                    this.folderMenu(path, box.left, box.bottom);
                });
                action.classList.add("mnm-wf-folder-action");
                const node = row.querySelector(NODE);
                (node?.querySelector(".node-actions") ?? node ?? row).append(action);
            }
        }
        // Prune detached nodes retained after Vue collapses/rebuilds a branch.
        for (const row of this.originalDraggable.keys()) if (!row.isConnected) this.originalDraggable.delete(row);
    }

    emptyFolder(path) {
        const item = element("li", "p-tree-node mnm-wf-extra");
        item.dataset.path = path;
        item.setAttribute("role", "treeitem");
        item.setAttribute("aria-label", basename(path));
        item.setAttribute("aria-level", String(path.split("/").length));
        item.tabIndex = 0;
        const row = element("div", "p-tree-node-content");
        const toggle = button(`Expand folder ${path}`, "pi-angle-right", () => changeExpanded());
        toggle.classList.add("p-tree-node-toggle-button");
        const icon = element("span", "p-tree-node-icon pi pi-folder");
        const label = element("span", "p-tree-node-label tree-explorer-node-label");
        const node = element("div", "tree-node tree-folder");
        node.dataset.testid = `tree-node-root/${path}`;
        node.append(element("span", "node-label", basename(path)));
        label.append(node);
        row.append(toggle, icon, label);
        const group = element("ul", "p-tree-node-children");
        group.setAttribute("role", "group");
        const changeExpanded = (expand = !this.expanded.has(path)) => {
            if (expand) this.expanded.add(path); else this.expanded.delete(path);
            item.setAttribute("aria-expanded", String(expand));
            group.hidden = !expand;
            toggle.title = `${expand ? "Collapse" : "Expand"} folder ${path}`;
            toggle.setAttribute("aria-label", toggle.title);
            toggle.firstChild.className = `pi pi-angle-${expand ? "down" : "right"}`;
            icon.className = `p-tree-node-icon pi pi-folder${expand ? "-open" : ""}`;
            this.schedule();
        };
        row.addEventListener("click", event => {
            if (!event.target.closest("button")) changeExpanded();
        });
        item.addEventListener("keydown", event => {
            if (event.target !== item) return;
            if (["Enter", " ", "ArrowRight", "ArrowLeft"].includes(event.key)) {
                event.preventDefault();
                changeExpanded(event.key === "ArrowRight" ? true : event.key === "ArrowLeft" ? false : undefined);
            } else if (event.key === "F2") {
                event.preventDefault();
                this.renameDialog(path);
            } else if (event.key === "F10" && event.shiftKey) {
                event.preventDefault();
                const box = row.getBoundingClientRect();
                this.folderMenu(path, box.left, box.bottom);
            }
        });
        item.append(row, group);
        changeExpanded(this.expanded.has(path));
        return item;
    }

    onContextMenu(event) {
        const data = this.rowAt(event.target);
        if (data && (!data.folder || !this.folders.has(data.path))) return;
        const root = !data && this.dropTarget(event.target);
        if (!data && !root) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        this.folderMenu(data?.path ?? "", event.clientX, event.clientY);
    }

    closeMenu() {
        this.menu?.remove();
        this.menuEvents?.abort();
        this.menu = null;
    }

    folderMenu(path, x, y) {
        this.closeMenu();
        const menu = this.menu = element("div", "mnm-wf-menu");
        menu.setAttribute("role", "menu");
        const choices = [
            [path ? "New subfolder" : "New folder", "pi-folder-plus", () => this.createDialog(path)],
            ...(path ? [
                ["Rename folder", "pi-pencil", () => this.renameDialog(path)],
                ["Move folder to…", "pi-arrow-right", () => this.moveDialog(path)],
            ] : []),
            ["Open folder", "pi-folder-open", () => this.openFolder(path)],
            ["Copy folder path", "pi-copy", () => this.copyPath(path)],
        ];
        for (const [label, icon, action] of choices) {
            const choice = button(label, icon, () => { this.closeMenu(); action(); }, label);
            choice.setAttribute("role", "menuitem");
            choice.disabled = this.busy || (label === "Open folder" && !this.info.can_open);
            menu.append(choice);
        }
        document.body.append(menu);
        const box = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(4, Math.min(x, innerWidth - box.width - 4))}px`;
        menu.style.top = `${Math.max(4, Math.min(y, innerHeight - box.height - 4))}px`;
        menu.querySelector("button:not(:disabled)")?.focus();
        this.menuEvents = new AbortController();
        const signal = this.menuEvents.signal;
        document.addEventListener("pointerdown", event => { if (!menu.contains(event.target)) this.closeMenu(); }, { capture: true, signal });
        document.addEventListener("keydown", event => {
            if (event.key === "Escape") { event.preventDefault(); this.closeMenu(); }
            if (["ArrowDown", "ArrowUp"].includes(event.key)) {
                event.preventDefault();
                const buttons = [...menu.querySelectorAll("button:not(:disabled)")];
                const index = buttons.indexOf(document.activeElement);
                buttons[(index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
            }
        }, { signal });
    }

    dialog(title, fields, submit, submitLabel = "Save") {
        if (this.busy) return;
        this.dialogNode?.close();
        const dialog = this.dialogNode = element("dialog", "mnm-wf-dialog");
        const form = element("form");
        const heading = element("h3", "", title);
        heading.id = "mnm-wf-dialog-title";
        dialog.setAttribute("aria-labelledby", heading.id);
        form.append(heading);
        const controls = {};
        for (const field of fields) {
            const label = element("label", "", field.label);
            const input = element(field.options ? "select" : "input");
            input.id = `mnm-wf-${field.id}`;
            label.htmlFor = input.id;
            if (field.options) for (const value of field.options) {
                const option = element("option", "", value || "Workflow folder (root)");
                option.value = value;
                input.append(option);
            }
            else { input.type = "text"; input.required = true; }
            input.value = field.value ?? "";
            controls[field.id] = input;
            form.append(label, input);
        }
        const error = element("div", "mnm-wf-dialog-error");
        error.setAttribute("role", "alert");
        const actions = element("div", "mnm-wf-dialog-actions");
        const cancel = button("Cancel", "", () => dialog.close(), "Cancel");
        const save = element("button", "mnm-wf-button", submitLabel);
        save.type = "submit";
        actions.append(cancel, save);
        form.append(error, actions);
        form.addEventListener("submit", async event => {
            event.preventDefault();
            save.disabled = true;
            cancel.disabled = true;
            error.textContent = "";
            try {
                await submit(Object.fromEntries(Object.entries(controls).map(([key, control]) => [key, control.value])));
                dialog.close();
            } catch (problem) { error.textContent = problem.message; }
            finally { save.disabled = false; cancel.disabled = false; }
        });
        dialog.addEventListener("cancel", event => { if (this.busy) event.preventDefault(); });
        dialog.addEventListener("close", () => {
            dialog.remove();
            if (this.dialogNode === dialog) this.dialogNode = null;
        });
        dialog.append(form);
        document.body.append(dialog);
        dialog.showModal();
        const first = Object.values(controls)[0];
        first?.focus();
        if (first instanceof HTMLInputElement) first.select();
    }

    folderOptions(exclude = null) {
        return ["", ...[...this.folders].filter(path => !exclude || !isWithin(path, exclude)).sort((a, b) => a.localeCompare(b))];
    }

    createDialog(parent) {
        this.dialog("New workflow folder", [
            { id: "name", label: "Name" },
            { id: "parent", label: "Parent folder", options: this.folderOptions(), value: parent },
        ], async values => {
            const path = joinPath(values.parent, validateName(values.name));
            await this.operation(async () => { await this.request("create", { path }); });
            this.expanded.add(values.parent);
        }, "Create");
    }

    renameDialog(path) {
        this.dialog("Rename workflow folder", [{ id: "name", label: "Name", value: basename(path) }],
            values => this.move(path, joinPath(parentPath(path), validateName(values.name)), true), "Rename");
    }

    moveDialog(path) {
        this.dialog(`Move ${basename(path)}`, [
            { id: "parent", label: "Destination folder", options: this.folderOptions(path), value: parentPath(path) },
        ], values => this.move(path, joinPath(values.parent, basename(path)), true), "Move");
    }

    async operation(action) {
        if (!this.alive || this.user !== api.user) throw new Error("The active user changed. Reopen the workflow sidebar.");
        if (this.busy || this.store?.isBusy) throw new Error("Wait for the current workflow operation to finish.");
        this.busy = true;
        this.setStatus();
        for (const control of this.tools.querySelectorAll("button")) control.disabled = true;
        try {
            await action();
            if (this.user !== api.user) throw new Error("The operation completed for the previous user. Reopen the workflow sidebar for the current user.");
            try {
                await this.store?.syncWorkflows?.();
                if (!await this.refreshInfo()) throw new Error(this.status.textContent || "Folder listing is unavailable.");
            } catch (error) {
                throw new Error(`Changes saved, but the workflow list could not refresh. ${error.message}`);
            }
            this.setStatus();
        } catch (error) {
            this.setStatus(error.message, true);
            throw error;
        } finally {
            this.busy = false;
            for (const control of this.tools.querySelectorAll("button")) control.disabled = false;
            this.schedule();
        }
    }

    async move(source, destination, folder) {
        if (source === destination) return;
        if (folder && isWithin(destination, source)) throw new Error("A folder cannot be moved inside itself.");
        if (typeof this.store?.renameWorkflow !== "function") throw new Error("This frontend does not expose the workflow move API.");
        const store = this.store;
        const moves = planWorkflowMove(store.workflows, source, destination, folder);
        await this.operation(async () => {
            await this.request("move", { source, destination });
            if (this.user !== api.user) throw new Error("Files moved for the previous user. Switch back to that user to refresh its workflows.");
            await reconcileWorkflowMove(store, moves);
            const changed = [...this.expanded].filter(path => isWithin(path, source));
            for (const path of changed) {
                this.expanded.delete(path);
                this.expanded.add(destination + path.slice(source.length));
            }
            this.expanded.add(parentPath(destination));
        });
    }

    async openFolder(path) {
        try { await this.request("open", { path }); }
        catch (error) { this.setStatus(error.message, true); }
    }

    async copyPath(path) {
        try {
            if (!this.info.path) await this.refreshInfo();
            if (!this.info.path) throw new Error("The workflow folder path is unavailable. Restart ComfyUI and try again.");
            const separator = this.info.path.includes("\\") ? "\\" : "/";
            const absolute = this.info.folder_paths?.[path]
                ?? this.info.path + (path ? separator + path.split("/").join(separator) : "");
            try { await navigator.clipboard.writeText(absolute); }
            catch {
                // Clipboard API may be unavailable on plain HTTP remote hosts.
                const text = element("textarea");
                text.value = absolute;
                text.style.position = "fixed";
                text.style.opacity = "0";
                document.body.append(text);
                text.select();
                try { if (!document.execCommand("copy")) throw new Error("Clipboard access was denied."); }
                finally { text.remove(); }
            }
            this.setStatus("Folder path copied.");
        } catch (error) { this.setStatus(error.message, true); }
    }

    onDragStart(event) {
        const data = this.rowAt(event.target);
        if (!data || !event.dataTransfer || this.busy) return;
        if (data.folder ? !this.folders.has(data.path) : !this.store?.getWorkflowByPath?.(WORKFLOW_PREFIX + data.path)) return;
        this.drag = { path: data.path, folder: data.folder, user: this.user };
        event.dataTransfer.setData(MIME, JSON.stringify(this.drag));
        // Preserve native workflow-to-canvas dragging.
        event.dataTransfer.effectAllowed = "copyMove";
    }

    dropTarget(target) {
        if (!(target instanceof Element)) return null;
        const data = this.rowAt(target);
        if (data) return data.folder && this.folders.has(data.path) ? { element: data.row, path: data.path } : null;
        const browse = target.closest(BROWSE);
        if (browse && this.panel.contains(browse)) {
            // The heading and bare tree background are the root drop target.
            // Highlight only during a drag; no extra row or label is needed.
            const heading = browse.firstElementChild;
            return { element: heading?.contains(target) ? heading : browse, path: "" };
        }
        // The scroll area may extend below the last tree row. Its empty space
        // belongs to the root, but other sidebar sections keep their behavior.
        const body = target.closest(".comfy-vue-side-bar-body");
        const root = this.panel.querySelector(BROWSE);
        if (body && root && !target.closest(".comfyui-workflows-open, .comfyui-workflows-bookmarks, .comfyui-workflows-search-panel")) {
            return { element: root, path: "" };
        }
        return null;
    }

    onDragOver(event) {
        const target = this.dropTarget(event.target);
        if (!target || !this.drag || this.busy) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const destination = joinPath(target.path, basename(this.drag.path));
        const invalid = this.drag.folder && isWithin(destination, this.drag.path);
        event.dataTransfer.dropEffect = invalid ? "none" : "move";
        if (this.dropElement !== target.element) {
            this.dropElement?.classList.remove("mnm-wf-drop");
            this.dropElement = target.element;
        }
        target.element.classList.toggle("mnm-wf-drop", !invalid);
    }

    onDragLeave(event) {
        if (this.dropElement && !this.dropElement.contains(event.relatedTarget)) {
            this.dropElement.classList.remove("mnm-wf-drop");
            this.dropElement = null;
        }
    }

    onDrop(event) {
        const target = this.dropTarget(event.target);
        if (!target || !this.drag) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const drag = this.drag;
        this.clearDrag();
        if (drag.user !== api.user) return;
        this.move(drag.path, joinPath(target.path, basename(drag.path)), drag.folder)
            .catch(error => this.setStatus(error.message, true));
    }

    clearDrag() {
        this.dropElement?.classList.remove("mnm-wf-drop");
        this.dropElement = null;
        this.drag = null;
    }

    dispose() {
        this.alive = false;
        this.infoRevision++;
        this.observer.disconnect();
        this.events.abort();
        cancelAnimationFrame(this.frame);
        clearTimeout(this.refreshTimer);
        this.closeMenu();
        this.dialogNode?.close();
        this.clearDrag();
        this.tools.remove();
        for (const extra of this.panel.querySelectorAll(".mnm-wf-extra-tree, .mnm-wf-extra, .mnm-wf-folder-action")) extra.remove();
        for (const [row, original] of this.originalDraggable) {
            if (original === null) row.removeAttribute("draggable"); else row.setAttribute("draggable", original);
        }
        this.originalDraggable.clear();
    }
}

function mount() {
    const panel = enabled() ? document.querySelector(PANEL) : null;
    if (controller?.panel === panel && controller?.user === api.user) return;
    controller?.dispose();
    controller = panel ? new WorkflowFolders(panel) : null;
}

function scheduleMount() {
    if (mountFrame) return;
    mountFrame = requestAnimationFrame(() => { mountFrame = 0; mount(); });
}

function updateEnabled() {
    cancelAnimationFrame(mountFrame);
    mountFrame = 0;
    mountObserver?.disconnect();
    mountObserver = null;
    unsubscribe?.();
    unsubscribe = null;
    if (!enabled()) {
        controller?.dispose();
        controller = null;
        return;
    }
    mountObserver = new MutationObserver(scheduleMount);
    mountObserver.observe(document.getElementById("vue-app") ?? document.body, { childList: true, subtree: true });
    unsubscribe = app.extensionManager?.workflow?.$onAction?.(({ name, after }) => {
        if (["syncWorkflows", "loadWorkflows", "saveWorkflow", "renameWorkflow", "deleteWorkflow"].includes(name)) {
            after(() => controller?.queueRefresh());
        }
    }, true);
    scheduleMount();
}

app.registerExtension({
    name: "MNeMiC.WorkflowFolders",
    setup() {
        addStyles();
        // The pack's shared settings extension owns registration/persistence.
        // Its native Settings toggle updates this feature through this event.
        window.removeEventListener("mnemic-workflow-folders-changed", updateEnabled);
        window.addEventListener("mnemic-workflow-folders-changed", updateEnabled);
        updateEnabled();
    },
});
