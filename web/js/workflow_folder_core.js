// Path and state helpers shared by the sidebar and its regression checks.
export const WORKFLOW_PREFIX = "workflows/";

export function validateName(name) {
    if (typeof name !== "string" || !name || name === "." || name === ".."
        || /[<>:"/\\|?*\x00-\x1f]/.test(name) || /[ .]$/.test(name)
        || /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(name)) {
        throw new Error("Choose a valid name without slashes or special filename characters.");
    }
    return name;
}

export function joinPath(parent, name) {
    return parent ? `${parent}/${name}` : name;
}

export function parentPath(path) {
    const index = path.lastIndexOf("/");
    return index < 0 ? "" : path.slice(0, index);
}

export function basename(path) {
    return path.slice(path.lastIndexOf("/") + 1);
}

export function isWithin(path, folder) {
    return path === folder || path.startsWith(`${folder}/`);
}

export function nativeFolderPaths(workflows) {
    const folders = new Set();
    for (const workflow of workflows) {
        if (!workflow.path?.startsWith(WORKFLOW_PREFIX)) continue;
        let path = parentPath(workflow.path.slice(WORKFLOW_PREFIX.length));
        while (path) {
            folders.add(path);
            path = parentPath(path);
        }
    }
    return folders;
}

export function planWorkflowMove(workflows, source, destination, folder) {
    const from = WORKFLOW_PREFIX + source;
    const to = WORKFLOW_PREFIX + destination;
    const moves = workflows.filter(w => folder ? isWithin(w.path, from) : w.path === from)
        .map(workflow => ({ workflow, oldPath: workflow.path, newPath: to + workflow.path.slice(from.length) }));
    const moving = new Set(moves.map(move => move.workflow));
    const occupied = new Set(workflows.filter(w => !moving.has(w)).map(w => w.path.toLocaleLowerCase()));
    for (const move of moves) {
        if (occupied.has(move.newPath.toLocaleLowerCase())) {
            throw new Error(`A workflow is already open at ${move.newPath}. Close or rename it first.`);
        }
        if (typeof move.workflow.updatePath !== "function" || typeof move.workflow.rename !== "function") {
            throw new Error("This ComfyUI frontend does not expose the workflow move API.");
        }
    }
    return moves;
}

export async function reconcileWorkflowMove(store, moves) {
    // The backend has already moved the file/directory. Let the native store
    // migrate tabs, dirty drafts, bookmarks and thumbnails, while replacing
    // only this instance's disk rename for the duration of that call.
    // Other workflows and the shared HTTP API remain untouched.
    const failures = [];
    for (const { workflow, oldPath, newPath } of moves) {
        const descriptor = Object.getOwnPropertyDescriptor(workflow, "rename");
        try {
            if (workflow.path !== oldPath) {
                throw new Error(`The workflow path changed during the move: ${oldPath}`);
            }
            workflow.rename = async function (requestedPath) {
                if (requestedPath !== newPath) throw new Error("An overlapping workflow rename was interrupted.");
                this.updatePath(requestedPath);
                return this;
            };
            await store.renameWorkflow(workflow, newPath);
        } catch (error) {
            failures.push(error);
        } finally {
            if (descriptor) Object.defineProperty(workflow, "rename", descriptor);
            else delete workflow.rename;
        }
    }
    if (failures.length) {
        throw new Error(`Files moved, but ComfyUI could not update every tab/bookmark. ${failures.map(e => e.message).join(" ")}`);
    }
}
