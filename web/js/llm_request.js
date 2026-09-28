import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// ✨ LLM Request — node UI.
//
// Adds a panel to the node with the endpoint's status (where it runs, whether
// its key/address is set), a searchable model browser, a connection test, a
// preset viewer, and a live view of the reply as it streams in.
//
// Nothing here is saved into the workflow except the per-endpoint model
// memory in node.properties (endpoint and model names only). The panel widget
// is not serialized, and the backend never sends a key, a header value or
// anything else from .env to the browser.

const NODE_ID = "MNeMiC_LLMAPI";
const DEFAULT_PRESET = "Use [system_message] and [user_input]";
const STREAM_EVENT = "mnemic.llm.stream";
const MODEL_MEMORY = "mnemic_llm_models";
const OUT_HEIGHT_PROPERTY = "mnemic_llm_out_height";
const OUT_HEIGHT_SETTING = "MNeMiC.LLM.PreviewHeight";
const FALLBACK_OUT_HEIGHT = 240;

// The default height for a node that hasn't been resized yet, from Settings
// → ⚡MNeMiC Nodes → LLM Request → Preview Height.
function defaultOutHeight() {
    const value = app.extensionManager?.setting?.get?.(OUT_HEIGHT_SETTING) ?? app.ui?.settings?.getSettingValue?.(OUT_HEIGHT_SETTING);
    return value ?? FALLBACK_OUT_HEIGHT;
}

const LOCATION_LABEL = {
    local: "This PC",
    network: "Network",
    cloud: "Cloud",
    unknown: "Not configured",
};

const panels = new Set();
let endpointCache = { at: 0, byName: new Map(), promise: null };
let presetCache = null;
const modelCache = new Map();

// --------------------------------------------------------------------------
// Data
// --------------------------------------------------------------------------

async function fetchJSON(path) {
    const res = await api.fetchApi(path);
    return res.json();
}

async function getEndpoints(force = false) {
    if (!force && endpointCache.promise && Date.now() - endpointCache.at < 15000) return endpointCache.promise;
    endpointCache.at = Date.now();
    endpointCache.promise = fetchJSON("/mnemic/llm/endpoints")
        .then((data) => {
            endpointCache.byName = new Map((data.endpoints ?? []).map((e) => [e.name, e]));
            return endpointCache.byName;
        })
        .catch(() => endpointCache.byName);
    return endpointCache.promise;
}

// Presets can change on disk (R refreshes the dropdown), so a name the cache
// doesn't know triggers one refetch.
async function getPresets(name) {
    presetCache ??= fetchJSON("/mnemic/llm/presets").then((d) => d.presets ?? {}).catch(() => ({}));
    let presets = await presetCache;
    if (name && !(name in presets)) {
        presetCache = fetchJSON("/mnemic/llm/presets").then((d) => d.presets ?? {}).catch(() => ({}));
        presets = await presetCache;
    }
    return presets;
}

async function getModels(endpoint, force = false, customId = "") {
    const key = `${endpoint}\u0000${customId}`;
    const cached = modelCache.get(key);
    if (!force && cached && Date.now() - cached.at < 60000) return cached.data;
    const query = `endpoint=${encodeURIComponent(endpoint)}${customId ? `&custom=${encodeURIComponent(customId)}` : ""}`;
    const data = await fetchJSON(`/mnemic/llm/models?${query}`).catch((e) => ({
        ok: false,
        error: `ComfyUI did not answer: ${e}`,
        models: [],
    }));
    if (data.ok) modelCache.set(key, { at: Date.now(), data });
    return data;
}

// Reasoning models served raw put their thoughts inline as <think>…</think>.
// The backend separates them in the final result; this does the same while
// the reply is still streaming, including a block that is not closed yet.
function splitInlineThinking(text) {
    const head = text.trimStart().toLowerCase();
    if (head && ["<think>", "<thinking>", "<reasoning>"].some((tag) => tag.startsWith(head))) return ["", ""];
    const m = text.match(/^\s*<(think|thinking|reasoning)>([\s\S]*?)(<\/\1>|$)/i);
    if (!m) return [text, ""];
    return [text.slice(m[0].length).trimStart(), m[2].trim()];
}

// --------------------------------------------------------------------------
// Styles
// --------------------------------------------------------------------------

function addStylesheet() {
    const style = document.createElement("style");
    style.textContent = `
        .mnemic-llm { display:flex; flex-direction:column; gap:6px; width:100%; height:100%; box-sizing:border-box;
            padding:6px 8px 8px; font:12px/1.4 system-ui, sans-serif; color:var(--fg-color); overflow:hidden; }
        .mnemic-llm-status { display:flex; align-items:center; gap:6px; min-height:20px; }
        .mnemic-llm-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; background:#888; }
        .mnemic-llm-dot.ok { background:#3fb950; box-shadow:0 0 6px #3fb95088; }
        .mnemic-llm-dot.warn { background:#d29922; }
        .mnemic-llm-dot.err { background:#f85149; }
        .mnemic-llm-dot.busy { background:#58a6ff; animation:mnemic-llm-pulse 1s ease-in-out infinite; }
        @keyframes mnemic-llm-pulse { 50% { opacity:.3; transform:scale(.8); } }
        .mnemic-llm-chip { padding:1px 7px; border-radius:10px; background:var(--comfy-input-bg); border:1px solid var(--border-color);
            white-space:nowrap; font-size:11px; }
        .mnemic-llm-chip.bad { border-color:#d29922; color:#d29922; }
        .mnemic-llm-host { flex:1; opacity:.6; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
        .mnemic-llm-btn.mnemic-llm-test { flex:0 0 auto; min-width:0; margin-left:auto; padding:2px 8px; }
        .mnemic-llm-pickrow { display:flex; gap:6px; }
        .mnemic-llm-pick { flex:1; min-width:0; display:flex; align-items:center; gap:4px; padding:3px 6px; border-radius:5px;
            background:var(--comfy-input-bg); color:var(--fg-color); border:1px solid var(--border-color); cursor:pointer; }
        .mnemic-llm-pick:hover { border-color:#58a6ff; }
        .mnemic-llm-pickrow > [data-act="endpoints"] { flex:0 0 calc((100% - 6px) / 3); box-sizing:border-box; }
        .mnemic-llm-pick.mnemic-llm-pick-combo { padding:0; cursor:default; }
        .mnemic-llm-pick-value { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:left; font-size:11.5px; }
        .mnemic-llm-pick-input { flex:1; min-width:0; padding:3px 0 3px 6px; border:none; background:none; color:var(--fg-color); font-size:11.5px; }
        .mnemic-llm-pick-input:focus { outline:none; }
        .mnemic-llm-arrow { opacity:.6; font-size:10px; flex:0 0 auto; }
        .mnemic-llm-arrow-btn { flex:0 0 auto; padding:3px 6px; border:none; border-left:1px solid var(--border-color);
            background:none; color:var(--fg-color); cursor:pointer; }
        .mnemic-llm-arrow-btn:hover .mnemic-llm-arrow { opacity:1; }
        .mnemic-llm-buttons { display:flex; gap:4px; flex-wrap:wrap; }
        .mnemic-llm-btn { flex:1; min-width:60px; padding:3px 6px; border-radius:5px; cursor:pointer; font-size:11.5px;
            background:var(--comfy-input-bg); color:var(--fg-color); border:1px solid var(--border-color); white-space:nowrap; }
        .mnemic-llm-btn:hover { border-color:#58a6ff; }
        .mnemic-llm-btn:disabled { opacity:.45; cursor:default; }
        .mnemic-llm-custom { display:flex; flex-direction:column; gap:5px; padding:6px; border-radius:6px;
            border:1px solid #d29922; background:#d2992214; }
        .mnemic-llm-custom[hidden] { display:none; }
        .mnemic-llm-warn { font-size:11px; line-height:1.35; color:var(--fg-color); }
        .mnemic-llm-warn b { color:#d29922; }
        .mnemic-llm-row { display:flex; gap:4px; }
        .mnemic-llm-row input, .mnemic-llm-row select { flex:1; min-width:0; padding:3px 6px; border-radius:5px; font-size:11.5px;
            background:var(--comfy-input-bg); color:var(--fg-color); border:1px solid var(--border-color); }
        .mnemic-llm-row select { flex:0 0 auto; }
        .mnemic-llm-custom-status { font-size:11px; opacity:.8; }
        .mnemic-llm-custom-status.err { color:#f85149; opacity:1; }
        .mnemic-llm-out { flex:none; box-sizing:border-box; min-height:40px; resize:vertical; overflow:auto; padding:6px 8px; border-radius:6px; white-space:pre-wrap; word-break:break-word;
            background:var(--comfy-input-bg); border:1px solid var(--border-color); user-select:text; cursor:text; }
        .mnemic-llm-out.empty { opacity:.5; font-style:italic; }
        .mnemic-llm-out.err { color:#f85149; }
        .mnemic-llm-out details { margin-bottom:6px; opacity:.75; }
        .mnemic-llm-out summary { cursor:pointer; user-select:none; font-style:italic; }
        .mnemic-llm-thinking { white-space:pre-wrap; font-size:11px; border-left:2px solid var(--border-color); padding-left:6px; margin-top:4px; }
        .mnemic-llm-caret::after { content:"▍"; animation:mnemic-llm-pulse .8s steps(2) infinite; }
        .mnemic-llm-stats { font-size:11px; opacity:.7; display:flex; gap:8px; flex-wrap:wrap; }
        .mnemic-llm-pop { position:fixed; z-index:10000; width:420px; max-width:calc(100vw - 24px); max-height:60vh; display:flex; flex-direction:column;
            background:var(--comfy-menu-bg); color:var(--fg-color); border:1px solid var(--border-color); border-radius:8px;
            box-shadow:0 10px 30px rgba(0,0,0,.55); font:12.5px/1.4 system-ui, sans-serif; overflow:hidden; }
        .mnemic-llm-pop-head { display:flex; align-items:center; gap:8px; padding:8px 10px; border-bottom:1px solid var(--border-color); font-weight:600; }
        .mnemic-llm-pop-head span { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .mnemic-llm-pop-close, .mnemic-llm-pop-refresh { cursor:pointer; opacity:.7; font-weight:normal; }
        .mnemic-llm-pop-close:hover, .mnemic-llm-pop-refresh:hover { opacity:1; }
        .mnemic-llm-pop input { margin:8px 10px 4px; padding:5px 8px; border-radius:5px; background:var(--comfy-input-bg); color:var(--fg-color);
            border:1px solid var(--border-color); outline:none; }
        .mnemic-llm-pop input:focus { border-color:#58a6ff; }
        .mnemic-llm-list { overflow:auto; padding:4px 0 6px; }
        .mnemic-llm-item { display:flex; align-items:baseline; gap:8px; padding:4px 12px; cursor:pointer; }
        .mnemic-llm-item.active { background:#58a6ff33; }
        .mnemic-llm-item.current .mnemic-llm-item-id::before { content:"✓ "; color:#3fb950; }
        .mnemic-llm-item-id { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#9198a1; }
        .mnemic-llm-item-tags { flex:0 0 auto; display:flex; gap:8px; font-size:11px; }
        .mnemic-llm-loaded { color:#3fb950; }
        .mnemic-llm-vision { color:#d29922; }
        .mnemic-llm-video { color:#58a6ff; }
        .mnemic-llm-note { padding:6px 12px; opacity:.75; font-size:11.5px; }
        .mnemic-llm-note.err { color:#f85149; opacity:1; }
        .mnemic-llm-pop pre { margin:0; padding:10px 12px; overflow:auto; white-space:pre-wrap; word-break:break-word; font:12px/1.45 ui-monospace, monospace; }
    `;
    document.head.appendChild(style);
}

// --------------------------------------------------------------------------
// Popups
// --------------------------------------------------------------------------

let openPopup = null;

function closePopup() {
    openPopup?.remove();
    openPopup = null;
}

function createPopup(anchor, title) {
    closePopup();
    const pop = document.createElement("div");
    pop.className = "mnemic-llm-pop";
    pop.innerHTML = `<div class="mnemic-llm-pop-head"><span></span><b class="mnemic-llm-pop-close" title="Close (Esc)">✕</b></div>`;
    pop.querySelector("span").textContent = title;
    pop.querySelector(".mnemic-llm-pop-close").addEventListener("click", closePopup);
    for (const type of ["pointerdown", "wheel", "keydown", "contextmenu"]) {
        pop.addEventListener(type, (e) => e.stopPropagation());
    }
    document.body.appendChild(pop);

    const rect = anchor.getBoundingClientRect();
    const width = Math.min(420, window.innerWidth - 24);
    const left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12));
    const below = window.innerHeight - rect.bottom;
    if (below > 260 || below > rect.top) {
        pop.style.top = `${rect.bottom + 4}px`;
        pop.style.maxHeight = `${Math.max(180, below - 16)}px`;
    } else {
        pop.style.bottom = `${window.innerHeight - rect.top + 4}px`;
        pop.style.maxHeight = `${Math.max(180, rect.top - 16)}px`;
    }
    pop.style.left = `${left}px`;
    openPopup = pop;
    return pop;
}

function showModelPicker(panel, anchor) {
    const endpoint = panel.widget("endpoint")?.value;
    const pop = createPopup(anchor, `Models · ${endpoint}`);
    const headTitle = pop.querySelector(".mnemic-llm-pop-head span");
    const refresh = document.createElement("b");
    refresh.className = "mnemic-llm-pop-refresh";
    refresh.title = "Refresh: ask the endpoint for its model list again, instead of using the last one fetched (cached for 1 minute)";
    refresh.textContent = "⟳";
    pop.querySelector(".mnemic-llm-pop-head").insertBefore(refresh, pop.querySelector(".mnemic-llm-pop-close"));

    const search = document.createElement("input");
    search.placeholder = "Search…";
    const note = document.createElement("div");
    note.className = "mnemic-llm-note";
    note.hidden = true;
    const list = document.createElement("div");
    list.className = "mnemic-llm-list";
    pop.append(search, note, list);
    search.focus();

    let models = [];
    let shown = [];
    let active = 0;
    const current = panel.widget("model")?.value ?? "";

    const choose = (id) => {
        panel.setModel(id);
        closePopup();
    };

    const render = () => {
        const q = search.value.trim().toLowerCase();
        const terms = q.split(/\s+/).filter(Boolean);
        shown = models.filter((m) => terms.every((t) => `${m.id} ${m.detail ?? ""}`.toLowerCase().includes(t)));
        const items = [...shown];
        if (q && !models.some((m) => m.id.toLowerCase() === q)) {
            items.push({ id: search.value.trim(), label: `Use “${search.value.trim()}”` });
        }
        shown = items;
        active = Math.min(active, items.length - 1);
        list.replaceChildren(
            ...items.map((m, i) => {
                const row = document.createElement("div");
                row.className = "mnemic-llm-item";
                if (i === active) row.classList.add("active");
                if (m.id === current) row.classList.add("current");
                const id = document.createElement("span");
                id.className = "mnemic-llm-item-id";
                id.textContent = m.label ?? m.id;
                id.title = m.id;
                row.append(id);
                const tags = document.createElement("span");
                tags.className = "mnemic-llm-item-tags";
                if (m.loaded) {
                    const loaded = document.createElement("span");
                    loaded.className = "mnemic-llm-loaded";
                    loaded.textContent = "in memory";
                    tags.append(loaded);
                }
                if (m.vision) {
                    const vision = document.createElement("span");
                    vision.className = "mnemic-llm-vision";
                    vision.textContent = "vision";
                    tags.append(vision);
                }
                if (m.video) {
                    const video = document.createElement("span");
                    video.className = "mnemic-llm-video";
                    video.textContent = "video";
                    tags.append(video);
                }
                if (tags.childNodes.length) row.append(tags);
                row.addEventListener("mousemove", () => {
                    if (active === i) return;
                    list.querySelector(".active")?.classList.remove("active");
                    row.classList.add("active");
                    active = i;
                });
                row.addEventListener("click", () => choose(m.id));
                return row;
            })
        );
    };

    const load = async (force) => {
        const data = await getModels(endpoint, force, panel.customId());
        if (openPopup !== pop) return;
        models = data.models ?? [];
        const isStatic = models.length > 0 && models.every((m) => m.static);
        headTitle.textContent = `Models · ${endpoint}${isStatic ? " *" : ""} (${models.length})`;
        headTitle.title = isStatic ? "* a fixed list built into this pack, not fetched live from the endpoint" : "";
        if (data.ok) {
            note.hidden = true;
        } else {
            note.hidden = false;
            note.className = "mnemic-llm-note err";
            note.textContent = `${data.error}${models.length ? " Showing models from the config instead." : ""}`;
        }
        render();
    };

    search.addEventListener("input", () => {
        active = 0;
        render();
    });
    search.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            active = (active + (e.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length;
            render();
            list.querySelector(".active")?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter") {
            e.preventDefault();
            const pick = shown[active];
            if (pick) choose(pick.id);
        } else if (e.key === "Escape") {
            closePopup();
        }
    });
    refresh.addEventListener("click", () => load(true));
    render();
    load(false);
}

function showEndpointPicker(panel, anchor) {
    const widget = panel.widget("endpoint");
    const names = widget?.options?.values ?? [];
    const current = widget?.value ?? "";
    const pop = createPopup(anchor, "Endpoints");

    const search = document.createElement("input");
    search.placeholder = "Search…";
    const list = document.createElement("div");
    list.className = "mnemic-llm-list";
    pop.append(search, list);
    search.focus();

    const choose = (name) => {
        panel.setEndpoint(name);
        closePopup();
    };

    let shown = [];
    let active = 0;

    const render = () => {
        const q = search.value.trim().toLowerCase();
        shown = names.filter((name) => !q || name.toLowerCase().includes(q));
        active = Math.min(active, shown.length - 1);
        list.replaceChildren(
            ...shown.map((name, i) => {
                const row = document.createElement("div");
                row.className = "mnemic-llm-item";
                if (i === active) row.classList.add("active");
                if (name === current) row.classList.add("current");
                const id = document.createElement("span");
                id.className = "mnemic-llm-item-id";
                id.textContent = name;
                row.append(id);
                row.addEventListener("mousemove", () => {
                    if (active === i) return;
                    list.querySelector(".active")?.classList.remove("active");
                    row.classList.add("active");
                    active = i;
                });
                row.addEventListener("click", () => choose(name));
                return row;
            })
        );
    };

    search.addEventListener("input", () => {
        active = 0;
        render();
    });
    search.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            active = (active + (e.key === "ArrowDown" ? 1 : -1) + shown.length) % shown.length;
            render();
            list.querySelector(".active")?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter") {
            e.preventDefault();
            const pick = shown[active];
            if (pick) choose(pick);
        } else if (e.key === "Escape") {
            closePopup();
        }
    });

    render();
}

// --------------------------------------------------------------------------
// The panel
// --------------------------------------------------------------------------

class LLMPanel {
    constructor(node) {
        this.node = node;
        this.state = "idle";
        this.result = null;
        this.el = document.createElement("div");
        this.el.className = "mnemic-llm";
        this.el.innerHTML = `
            <div class="mnemic-llm-status">
                <span class="mnemic-llm-dot"></span>
                <span class="mnemic-llm-chip" data-role="where"></span>
                <span class="mnemic-llm-chip" data-role="key"></span>
                <span class="mnemic-llm-host"></span>
                <button class="mnemic-llm-btn mnemic-llm-test" data-act="test" title="Check that the endpoint answers">Test</button>
            </div>
            <div class="mnemic-llm-pickrow">
                <button class="mnemic-llm-pick" data-act="endpoints" title="Endpoint - click to choose">
                    <span class="mnemic-llm-pick-value" data-role="endpoint-value"></span>
                    <span class="mnemic-llm-arrow">▾</span>
                </button>
                <span class="mnemic-llm-pick mnemic-llm-pick-combo">
                    <input class="mnemic-llm-pick-input" data-role="model-input" placeholder="Model" title="Model - type a name, or click ▾ to browse" spellcheck="false" autocomplete="off">
                    <button class="mnemic-llm-arrow-btn" data-act="models" title="Browse the models this endpoint offers"><span class="mnemic-llm-arrow">▾</span></button>
                </span>
            </div>
            <div class="mnemic-llm-custom" hidden>
                <div class="mnemic-llm-warn"><b>Custom endpoint.</b> The address and key you enter are stored on this
                    ComfyUI machine only (nodes/llm/CustomEndpoints.local.json, plain text) and never in the workflow:
                    the workflow keeps just a random id, so shared workflows and images don't carry them.
                    Changing the address or protocol clears the saved key.
                    <b>Risks:</b> anyone who can open this ComfyUI can use a saved endpoint and make the server connect
                    to any address; prompts and images go to whatever server you enter, so only use one you trust.
                    For a permanent setup, prefer a named endpoint in UserEndpoints.json with its key in .env.</div>
                <div class="mnemic-llm-row">
                    <select data-f="provider" title="Protocol the server speaks">
                        <option value="openai">OpenAI-compatible</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="ollama">Ollama</option>
                    </select>
                    <input data-f="url" placeholder="http://host:port/v1" spellcheck="false" autocomplete="off">
                </div>
                <div class="mnemic-llm-row">
                    <input data-f="key" type="password" placeholder="API key (optional)" autocomplete="new-password">
                    <button class="mnemic-llm-btn" data-act="custom-save" style="flex:0 0 auto">Save</button>
                </div>
                <div class="mnemic-llm-custom-status"></div>
            </div>
            <div class="mnemic-llm-out empty">No reply yet.</div>
            <div class="mnemic-llm-stats"></div>
        `;
        this.dot = this.el.querySelector(".mnemic-llm-dot");
        this.where = this.el.querySelector('[data-role="where"]');
        this.key = this.el.querySelector('[data-role="key"]');
        this.host = this.el.querySelector(".mnemic-llm-host");
        this.endpointValue = this.el.querySelector('[data-role="endpoint-value"]');
        this.modelInput = this.el.querySelector('[data-role="model-input"]');
        this.out = this.el.querySelector(".mnemic-llm-out");
        this.stats = this.el.querySelector(".mnemic-llm-stats");
        this.custom = this.el.querySelector(".mnemic-llm-custom");
        this.customStatus = this.el.querySelector(".mnemic-llm-custom-status");
        this.customField = (f) => this.custom.querySelector(`[data-f="${f}"]`);
        // Unsaved edits are never overwritten by a status refresh.
        this.customDirty = false;
        for (const f of ["provider", "url"]) {
            this.customField(f).addEventListener("input", () => (this.customDirty = true));
            this.customField(f).addEventListener("change", () => (this.customDirty = true));
        }
        // Typing in these fields must not trigger ComfyUI shortcuts.
        for (const type of ["keydown", "keyup", "keypress", "pointerdown", "wheel"]) {
            this.custom.addEventListener(type, (e) => e.stopPropagation());
            this.modelInput.addEventListener(type, (e) => e.stopPropagation());
        }
        this.modelInput.addEventListener("input", () => {
            const w = this.widget("model");
            if (!w) return;
            w.value = this.modelInput.value;
            w.callback?.(w.value);
        });

        this.el.addEventListener("pointerdown", (e) => {
            if (e.target.closest("button, input, .mnemic-llm-out")) e.stopPropagation();
        });
        this.out.addEventListener("wheel", (e) => {
            if (this.out.scrollHeight > this.out.clientHeight) e.stopPropagation();
        }, { passive: true });
        this.el.querySelectorAll("button").forEach((b) => b.addEventListener("click", (e) => {
            e.stopPropagation();
            this.onButton(b.dataset.act, b);
        }));

        const contentHeight = () => this.el.scrollHeight || 150;
        this.domWidget = node.addDOMWidget("llm_panel", "mnemic_llm_panel", this.el, {
            serialize: false,
            hideOnZoom: false,
            getMinHeight: contentHeight,
            getValue: () => "",
            setValue: () => {},
        });
        this.domWidget.serialize = false;
        // The panel is exactly as tall as its content: without this it is
        // treated as a widget that claims any spare node height, and the
        // fixed-height reply box then leaves that space empty below it.
        this.domWidget.computeSize = (width) => [width ?? this.node.size[0], contentHeight()];
        this.domWidget.computeLayoutSize = undefined;
        this.applyOutHeight();

        this.hideRawWidgets();
        this.syncEndpointValue();
        this.syncModelInput();

        // Dragging the reply preview's resize handle persists the chosen
        // height on this node and resizes the node to match.
        new ResizeObserver(() => {
            if (!this.out.isConnected) return;
            if (this.out.offsetHeight && this.out.offsetHeight !== this.outHeight()) {
                this.node.properties ??= {};
                this.node.properties[OUT_HEIGHT_PROPERTY] = this.out.offsetHeight;
                this.fitNode();
            }
        }).observe(this.out);
    }

    // The endpoint and model widgets keep their value (workflows still store
    // just the name/model string) but are never drawn: the pick button and
    // the model input above are the only way to change them now.
    hideRawWidgets() {
        for (const name of ["endpoint", "model"]) {
            const w = this.widget(name);
            if (!w) continue;
            w.hidden = true;
            w.computeSize = () => [0, -4];
            if (w.type !== "hidden") {
                w.origType = w.origType || w.type;
                w.type = "hidden";
            }
        }
    }

    syncEndpointValue() {
        if (this.endpointValue) this.endpointValue.textContent = this.widget("endpoint")?.value ?? "";
    }

    syncModelInput() {
        const w = this.widget("model");
        if (w && this.modelInput && this.modelInput.value !== (w.value ?? "")) this.modelInput.value = w.value ?? "";
    }

    outHeight() {
        return this.node.properties?.[OUT_HEIGHT_PROPERTY] ?? defaultOutHeight();
    }

    applyOutHeight() {
        this.out.style.height = `${this.outHeight()}px`;
    }

    // Snaps the node to exactly the height its widgets need, shrinking away
    // any stale extra space as well as growing for a taller reply box.
    fitNode() {
        const [w] = this.node.size;
        this.node.setSize([w, this.node.computeSize()[1]]);
        this.node.setDirtyCanvas(true, true);
    }

    widget(name) {
        return this.node.widgets?.find((w) => w.name === name);
    }

    customId() {
        return this.widget("custom_endpoint")?.value ?? "";
    }

    setCustomVisible(visible) {
        if (this.custom.hidden === !visible) return;
        this.custom.hidden = !visible;
        // Height depends on the section's rendered size: measure after layout.
        requestAnimationFrame(() => this.fitNode());
        this.fitNode();
    }

    // The custom endpoint's status comes from what is stored on this
    // machine under the node's id; the key itself is never sent back.
    async refreshCustom(info) {
        this.setCustomVisible(true);
        const id = this.customId();
        const data = id ? await fetchJSON(`/mnemic/llm/custom?id=${encodeURIComponent(id)}`).catch(() => ({ ok: false })) : { ok: false };
        if (this.widget("endpoint")?.value !== info.name || this.customId() !== id) return;
        info.ok = !!data.ok;
        info.location = data.location ?? "unknown";
        info.provider = data.provider ?? "custom";
        info.key_set = !!data.key_set;
        info.host = data.ok ? "custom endpoint" : "not saved yet";
        info.problems = data.ok ? [] : ["Enter the server's address (and key, if it needs one) and press Save."];
        if (data.ok) {
            // Fill the fields from what is saved only for a newly shown id,
            // or when the user hasn't started editing them.
            if (this.customLoadedId !== id || !this.customDirty) {
                this.customField("provider").value = data.provider;
                this.customField("url").value = data.base_url ?? "";
                this.customDirty = false;
            }
            this.customLoadedId = id;
            this.customField("key").placeholder = data.key_set
                ? "API key saved (changing the address clears it)" : "API key (optional)";
        }
    }

    async saveCustom() {
        const url = this.customField("url").value.trim();
        const key = this.customField("key").value;
        const body = { id: this.customId(), provider: this.customField("provider").value, base_url: url };
        if (key) body.api_key = key;  // empty field: keep the saved key
        this.customStatus.className = "mnemic-llm-custom-status";
        this.customStatus.textContent = "Saving…";
        let data;
        try {
            const res = await api.fetchApi("/mnemic/llm/custom", {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
            });
            data = await res.json();
        } catch (e) {
            data = { ok: false, error: String(e) };
        }
        if (!data.ok) {
            this.customStatus.className = "mnemic-llm-custom-status err";
            this.customStatus.textContent = data.error ?? "Could not save.";
            return;
        }
        this.customField("key").value = "";
        this.customDirty = false;
        const w = this.widget("custom_endpoint");
        if (w && w.value !== data.id) {
            w.value = data.id;
            w.callback?.(data.id);
        }
        modelCache.clear();
        this.customStatus.textContent = "✓ Saved on this machine.";
        this.refreshStatus();
    }

    matches(id) {
        const own = String(this.node.id);
        const s = String(id);
        return s === own || s.endsWith(`:${own}`);
    }

    // ---- endpoint status ------------------------------------------------

    async refreshStatus(force = false) {
        let byName = await getEndpoints(force);
        const name = this.widget("endpoint")?.value;
        // An endpoint added since the last fetch (edit + R): ask again once.
        if (!byName.has(name) && !force) byName = await getEndpoints(true);
        if (this.widget("endpoint")?.value !== name) return;
        const info = byName.has(name) ? { ...byName.get(name) } : undefined;
        if (info?.is_custom) {
            await this.refreshCustom(info);
            if (this.widget("endpoint")?.value !== name) return;
        } else {
            this.setCustomVisible(false);
        }
        this.info = info;
        if (!info) {
            this.setChip(this.where, "Unknown endpoint", true);
            this.setChip(this.key, "", false);
            this.host.textContent = "";
            if (this.state === "idle") this.setDot("warn");
            return;
        }
        const label = LOCATION_LABEL[info.location] ?? LOCATION_LABEL.unknown;
        this.setChip(this.where, `${label} · ${info.provider}`, info.location === "unknown");
        if (info.is_custom) {
            this.setChip(this.key, info.key_set ? "key saved" : "no key", false);
        } else if (info.key_env) {
            this.setChip(this.key, info.key_set ? "key set" : info.key_optional ? "no key" : `${info.key_env} missing`, !info.key_set && !info.key_optional);
        } else {
            this.setChip(this.key, "no key needed", false);
        }
        this.host.title = [info.description, ...info.problems].filter(Boolean).join("\n\n");
        this.updateModelHint();
        if (this.state === "idle") {
            // Green once configured; ⚡ Test checks that it actually answers.
            this.setDot(info.ok ? "ok" : "warn");
            if (!info.ok && !this.result) this.showNote(info.problems.join(" "), false);
            else if (info.ok && !this.result) this.showNote("No reply yet.", false);
        }
    }

    setChip(el, text, bad) {
        el.textContent = text;
        el.style.display = text ? "" : "none";
        el.classList.toggle("bad", !!bad);
    }

    setDot(kind) {
        this.dot.className = `mnemic-llm-dot ${kind}`;
    }

    // Shown in the status line: the model field is a canvas widget with no
    // placeholder of its own.
    updateModelHint() {
        if (!this.info) return;
        const model = this.widget("model")?.value ?? "";
        let hint = "";
        if (!model && this.info.model_optional) {
            hint = this.info.is_cli ? "model: CLI default" : "model: server default";
        } else if (!model) {
            hint = this.info.default_model
                ? `model: ${this.info.default_model} (default)`
                : this.info.provider === "ollama" ? "model: one in memory, else first installed"
                : ["local", "network"].includes(this.info.location) ? "model: first the server lists"
                : "no model chosen";
        }
        // The where-chip already names the CLI (e.g. "This PC · claude_cli");
        // info.host would just repeat that in different words.
        const hostPart = this.info.is_cli ? "" : this.info.host;
        this.host.textContent = [hostPart, hint].filter(Boolean).join(" · ");
    }

    // ---- presets --------------------------------------------------------

    // Picking a preset copies its text into system_message once, then resets
    // the preset dropdown to default: a one-shot insert, not a persistent
    // mode, so the field stays freely editable afterward.
    async applyPreset() {
        const w = this.widget("preset");
        const name = w?.value;
        if (!name || name === DEFAULT_PRESET) return;
        const text = (await getPresets(name))[name] ?? "";
        if (w.value !== name) return; // changed again while this was loading
        const sys = this.widget("system_message");
        const current = (sys?.value ?? "").trim();
        if (current && current !== text.trim() && !window.confirm(`Replace the current system message with the "${name}" preset?`)) {
            w.value = DEFAULT_PRESET;
            w.callback?.(DEFAULT_PRESET);
            return;
        }
        if (sys) {
            sys.value = text;
            sys.callback?.(text);
        }
        w.value = DEFAULT_PRESET;
        w.callback?.(DEFAULT_PRESET);
        this.node.setDirtyCanvas(true, true);
    }

    // ---- endpoints --------------------------------------------------------

    setEndpoint(name) {
        const w = this.widget("endpoint");
        if (!w || w.value === name) return;
        w.value = name;
        w.callback?.(name);
        this.node.setDirtyCanvas(true, true);
    }

    // ---- models ---------------------------------------------------------

    setModel(id) {
        const w = this.widget("model");
        if (!w) return;
        w.value = id;
        w.callback?.(id);
        this.rememberModel();
        this.syncModelInput();
        this.node.setDirtyCanvas(true, true);
    }

    rememberModel(endpoint = this.widget("endpoint")?.value) {
        const model = this.widget("model")?.value ?? "";
        if (!endpoint) return;
        const memory = { ...(this.node.properties?.[MODEL_MEMORY] ?? {}) };
        if (model) memory[endpoint] = model;
        else delete memory[endpoint];
        this.node.properties ??= {};
        this.node.properties[MODEL_MEMORY] = memory;
    }

    onEndpointChanged(previous) {
        // Each endpoint remembers the model last used with it on this node.
        if (previous) this.rememberModel(previous);
        const endpoint = this.widget("endpoint")?.value;
        const remembered = this.node.properties?.[MODEL_MEMORY]?.[endpoint] ?? "";
        const w = this.widget("model");
        if (w && w.value !== remembered) {
            w.value = remembered;
            this.node.setDirtyCanvas(true, true);
        }
        this.syncEndpointValue();
        this.syncModelInput();
        this.result = null;
        this.stats.textContent = "";
        this.refreshStatus();
    }

    // ---- buttons --------------------------------------------------------

    async onButton(act, button) {
        if (act === "custom-save") return this.saveCustom();
        if (act === "endpoints") return showEndpointPicker(this, button);
        if (act === "models") return showModelPicker(this, button);
        if (act === "test") {
            button.disabled = true;
            const runId = this.runId;
            await this.refreshStatus(true);
            this.setDot("busy");
            const endpoint = this.widget("endpoint")?.value;
            const data = await getModels(endpoint, true, this.customId());
            button.disabled = false;
            // A slow test must not paint over a newer endpoint or a running reply.
            if (this.widget("endpoint")?.value !== endpoint || this.state === "running" || this.runId !== runId) return;
            if (data.ok) {
                this.setDot("ok");
                this.showNote(`✓ ${endpoint} answered in ${data.ms} ms with ${data.models.length} model${data.models.length === 1 ? "" : "s"}.`, false);
            } else {
                this.setDot("err");
                this.showNote(data.error, true);
            }
        }
    }

    // ---- output ---------------------------------------------------------

    showNote(text, isError) {
        this.out.className = `mnemic-llm-out empty${isError ? " err" : ""}`;
        this.out.textContent = text;
    }

    renderReply(text, thinking, streaming) {
        this.out.className = "mnemic-llm-out";
        const pinned = this.out.scrollHeight - this.out.scrollTop - this.out.clientHeight < 24;
        const wasOpen = this.out.querySelector("details")?.open ?? false;
        this.out.replaceChildren();
        if (thinking) {
            const details = document.createElement("details");
            details.open = wasOpen || (streaming && !text);
            const summary = document.createElement("summary");
            summary.textContent = `💭 Thinking${streaming && !text ? "…" : ""} (${thinking.length.toLocaleString()} chars)`;
            const body = document.createElement("div");
            body.className = "mnemic-llm-thinking";
            body.textContent = thinking;
            details.append(summary, body);
            this.out.append(details);
        }
        const reply = document.createElement("span");
        reply.textContent = text;
        if (streaming) reply.classList.add("mnemic-llm-caret");
        this.out.append(reply);
        if (pinned || streaming) this.out.scrollTop = this.out.scrollHeight;
    }

    onStream(msg) {
        if (msg.phase === "start") {
            this.runId = (this.runId ?? 0) + 1;
            this.result = null;
            this.partial = { text: "", thinking: "" };
            this.state = "running";
            this.startedAt = performance.now();
            this.setDot("busy");
            this.showNote(`Waiting for ${msg.model} on ${msg.endpoint}…`, false);
            this.stats.textContent = "";
        } else if (msg.phase === "stream") {
            this.state = "running";
            this.setDot("busy");
            const [text, inline] = splitInlineThinking(msg.text ?? "");
            this.partial = { text, thinking: [msg.thinking, inline].filter(Boolean).join("\n\n") };
            this.renderReply(this.partial.text, this.partial.thinking, true);
            const secs = (performance.now() - (this.startedAt ?? performance.now())) / 1000;
            this.stats.textContent = `streaming · ${secs.toFixed(1)} s · ${(msg.text ?? "").length.toLocaleString()} chars`;
        } else if (msg.phase === "error") {
            this.state = "idle";
            this.result = null;
            this.setDot("err");
            this.showNote(msg.error, true);
            this.stats.textContent = "";
        }
    }

    onResult(summary) {
        this.runId = (this.runId ?? 0) + 1;
        this.state = "idle";
        if (!summary.ok) {
            this.result = null;
            this.setDot("err");
            this.showNote(summary.error ?? summary.status, true);
            this.stats.textContent = "";
            return;
        }
        this.result = summary;
        this.setDot("ok");
        this.renderReply(summary.text, summary.thinking, false);
        const parts = [`✓ ${summary.model}`];
        if (summary.input_tokens != null || summary.output_tokens != null) {
            parts.push(`${summary.input_tokens ?? "?"} in / ${summary.output_tokens ?? "?"} out`);
        }
        parts.push(`${summary.seconds.toFixed(1)} s`);
        if (summary.output_tokens && summary.seconds > 0) parts.push(`${Math.round(summary.output_tokens / summary.seconds)} tok/s`);
        if (summary.status && summary.status !== "200 OK") parts.push(summary.status.replace(/^200 OK /, ""));
        this.stats.textContent = parts.join(" · ");
        // .env may have changed since the panel last looked (e.g. a key added).
        this.refreshStatus(true);
    }

    onInterrupted() {
        if (this.state !== "running") return;
        this.state = "idle";
        this.setDot("warn");
        // Keep what arrived, without the streaming caret.
        if (this.partial?.text || this.partial?.thinking) this.renderReply(this.partial.text, this.partial.thinking, false);
        this.stats.textContent = "interrupted";
    }
}

// --------------------------------------------------------------------------
// Wiring
// --------------------------------------------------------------------------

// Panels whose node is still in a graph; drops any that were detached
// without an onRemoved.
function livePanels() {
    for (const panel of panels) if (!panel.node.graph) panels.delete(panel);
    return [...panels];
}

function chainCallback(widget, fn) {
    if (!widget) return;
    const original = widget.callback;
    widget.callback = function (value, ...rest) {
        const previous = widget._mnemicLast;
        widget._mnemicLast = value;
        const r = original?.apply(this, [value, ...rest]);
        fn(value, previous);
        return r;
    };
    widget._mnemicLast = widget.value;
}

app.registerExtension({
    name: "MNeMiC.LLMRequest",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);
            const panel = new LLMPanel(this);
            this.mnemicLLM = panel;

            chainCallback(panel.widget("endpoint"), (_value, previous) => panel.onEndpointChanged(previous));
            chainCallback(panel.widget("preset"), () => panel.applyPreset());
            chainCallback(panel.widget("model"), () => {
                panel.rememberModel();
                panel.syncModelInput();
                panel.updateModelHint();
            });

            const [w, h] = this.size;
            this.setSize([Math.max(w, 400), Math.max(h, this.computeSize()[1])]);
            requestAnimationFrame(() => panel.refreshStatus());
            return r;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = onConfigure?.apply(this, arguments);
            const panel = this.mnemicLLM;
            if (panel) {
                for (const name of ["endpoint", "preset", "model"]) {
                    const w = panel.widget(name);
                    if (w) w._mnemicLast = w.value;
                }
                panel.hideRawWidgets();
                panel.syncEndpointValue();
                panel.syncModelInput();
                requestAnimationFrame(() => {
                    // Undo/redo and tab switches rebuild the node, and
                    // onExecuted is not replayed: restore the last reply.
                    const outputs = app.nodeOutputs ?? {};
                    const key = Object.keys(outputs).find((k) => panel.matches(k) && outputs[k]?.mnemic_llm?.[0]);
                    if (key && !panel.result) panel.onResult(outputs[key].mnemic_llm[0]);
                    panel.refreshStatus();
                    // A node saved before the reply box got a fixed height
                    // may carry a stale, oversized node height: correct it.
                    panel.fitNode();
                });
            }
            return r;
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            const r = onExecuted?.apply(this, arguments);
            const summary = message?.mnemic_llm?.[0];
            if (summary) this.mnemicLLM?.onResult(summary);
            return r;
        };

        // Registered only once the node is in a graph: copy/paste and
        // convert-to-subgraph build throwaway clones that are never added,
        // and so never removed either.
        const onAdded = nodeType.prototype.onAdded;
        nodeType.prototype.onAdded = function () {
            const r = onAdded?.apply(this, arguments);
            if (this.mnemicLLM) panels.add(this.mnemicLLM);
            return r;
        };

        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            if (this.mnemicLLM) panels.delete(this.mnemicLLM);
            return onRemoved?.apply(this, arguments);
        };
    },

    setup() {
        addStylesheet();
        api.addEventListener(STREAM_EVENT, ({ detail }) => {
            if (!detail?.node) return;
            for (const panel of livePanels()) if (panel.matches(detail.node)) panel.onStream(detail);
        });
        api.addEventListener("execution_interrupted", () => livePanels().forEach((p) => p.onInterrupted()));
        api.addEventListener("execution_error", () => livePanels().forEach((p) => p.state === "running" && p.onInterrupted()));
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && openPopup) closePopup();
        });
        document.addEventListener("pointerdown", (e) => {
            if (openPopup && !openPopup.contains(e.target) && !e.target.closest?.(".mnemic-llm-btn")) closePopup();
        }, true);
    },
});
