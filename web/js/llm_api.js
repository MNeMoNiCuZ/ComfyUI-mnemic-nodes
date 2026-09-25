import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// ✨🧠 Universal LLM API — node UI.
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

const LOCATION_LABEL = {
    local: ["🖥", "This PC"],
    network: ["🏠", "Network"],
    cloud: ["☁", "Cloud"],
    unknown: ["❔", "Not set"],
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

async function getModels(endpoint, force = false) {
    const cached = modelCache.get(endpoint);
    if (!force && cached && Date.now() - cached.at < 60000) return cached.data;
    const data = await fetchJSON(`/mnemic/llm/models?endpoint=${encodeURIComponent(endpoint)}`).catch((e) => ({
        ok: false,
        error: `ComfyUI did not answer: ${e}`,
        models: [],
    }));
    if (data.ok) modelCache.set(endpoint, { at: Date.now(), data });
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

// navigator.clipboard only exists in secure contexts; ComfyUI opened over
// http://<LAN IP> is not one, so fall back to the old selection copy.
async function copyText(text) {
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // fall through to the fallback
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
        ok = document.execCommand("copy");
    } catch {
        ok = false;
    }
    area.remove();
    return ok;
}

// --------------------------------------------------------------------------
// Styles
// --------------------------------------------------------------------------

function addStylesheet() {
    const style = document.createElement("style");
    style.textContent = `
        .mnemic-llm { display:flex; flex-direction:column; gap:6px; width:100%; height:100%; box-sizing:border-box;
            padding:6px 8px 8px; font:12px/1.4 system-ui, sans-serif; color:var(--fg-color); overflow:hidden; }
        .mnemic-llm-status { display:flex; align-items:center; gap:6px; flex-wrap:wrap; min-height:20px; }
        .mnemic-llm-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; background:#888; }
        .mnemic-llm-dot.ok { background:#3fb950; box-shadow:0 0 6px #3fb95088; }
        .mnemic-llm-dot.warn { background:#d29922; }
        .mnemic-llm-dot.err { background:#f85149; }
        .mnemic-llm-dot.busy { background:#58a6ff; animation:mnemic-llm-pulse 1s ease-in-out infinite; }
        @keyframes mnemic-llm-pulse { 50% { opacity:.3; transform:scale(.8); } }
        .mnemic-llm-chip { padding:1px 7px; border-radius:10px; background:var(--comfy-input-bg); border:1px solid var(--border-color);
            white-space:nowrap; font-size:11px; }
        .mnemic-llm-chip.bad { border-color:#d29922; color:#d29922; }
        .mnemic-llm-host { opacity:.6; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; flex:1; }
        .mnemic-llm-buttons { display:flex; gap:4px; flex-wrap:wrap; }
        .mnemic-llm-btn { flex:1; min-width:60px; padding:3px 6px; border-radius:5px; cursor:pointer; font-size:11.5px;
            background:var(--comfy-input-bg); color:var(--fg-color); border:1px solid var(--border-color); white-space:nowrap; }
        .mnemic-llm-btn:hover { border-color:#58a6ff; }
        .mnemic-llm-btn:disabled { opacity:.45; cursor:default; }
        .mnemic-llm-out { flex:1; min-height:40px; overflow:auto; padding:6px 8px; border-radius:6px; white-space:pre-wrap; word-break:break-word;
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
        .mnemic-llm-item-id { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .mnemic-llm-item-detail { opacity:.55; font-size:11px; white-space:nowrap; }
        .mnemic-llm-loaded { color:#3fb950; font-size:10px; }
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
    const refresh = document.createElement("b");
    refresh.className = "mnemic-llm-pop-refresh";
    refresh.title = "Ask the endpoint again";
    refresh.textContent = "⟳";
    pop.querySelector(".mnemic-llm-pop-head").insertBefore(refresh, pop.querySelector(".mnemic-llm-pop-close"));

    const search = document.createElement("input");
    search.placeholder = "Search, or type any model name and press Enter…";
    const note = document.createElement("div");
    note.className = "mnemic-llm-note";
    note.textContent = "Asking the endpoint…";
    const list = document.createElement("div");
    list.className = "mnemic-llm-list";
    pop.append(search, note, list);
    search.focus();

    let models = [];
    let shown = [];
    let active = 0;
    const current = panel.widget("model")?.value ?? "";
    const info = endpointCache.byName.get(endpoint);

    const choose = (id) => {
        panel.setModel(id);
        closePopup();
    };

    const render = () => {
        const q = search.value.trim().toLowerCase();
        const terms = q.split(/\s+/).filter(Boolean);
        shown = models.filter((m) => terms.every((t) => `${m.id} ${m.detail ?? ""}`.toLowerCase().includes(t)));
        const items = [{ id: "", label: `Endpoint default${info?.default_model ? ` (${info.default_model})` : ""}`, detail: "" }, ...shown];
        if (q && !models.some((m) => m.id.toLowerCase() === q)) {
            items.push({ id: search.value.trim(), label: `Use “${search.value.trim()}”`, detail: "custom" });
        }
        shown = items;
        active = Math.min(active, items.length - 1);
        list.replaceChildren(
            ...items.map((m, i) => {
                const row = document.createElement("div");
                row.className = "mnemic-llm-item";
                if (i === active) row.classList.add("active");
                if (m.id === current && (m.id !== "" || current === "")) row.classList.add("current");
                const id = document.createElement("span");
                id.className = "mnemic-llm-item-id";
                id.textContent = m.label ?? m.id;
                id.title = m.id;
                row.append(id);
                if (m.loaded) {
                    const loaded = document.createElement("span");
                    loaded.className = "mnemic-llm-loaded";
                    loaded.textContent = "● in memory";
                    row.append(loaded);
                }
                if (m.detail) {
                    const detail = document.createElement("span");
                    detail.className = "mnemic-llm-item-detail";
                    detail.textContent = m.detail;
                    row.append(detail);
                }
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
        note.className = "mnemic-llm-note";
        note.textContent = "Asking the endpoint…";
        const data = await getModels(endpoint, force);
        if (openPopup !== pop) return;
        models = data.models ?? [];
        if (data.ok) {
            note.textContent = `${models.length} model${models.length === 1 ? "" : "s"} · ${data.ms} ms`;
        } else {
            note.className = "mnemic-llm-note err";
            note.textContent = `${data.error}${models.length ? " Showing models from the config instead." : ""}`;
        }
        render();
    };

    search.addEventListener("input", () => {
        active = search.value ? 1 : 0;
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

async function showPreset(panel, anchor) {
    const name = panel.widget("preset")?.value;
    const pop = createPopup(anchor, name === DEFAULT_PRESET ? "No preset selected" : name);
    const pre = document.createElement("pre");
    if (name === DEFAULT_PRESET) {
        pre.textContent = "The node is using its own system_message field.\n\nPick a preset to replace it with a saved system prompt. Presets are shared with the Groq nodes: nodes/groq/UserPrompts.json and UserPrompts_VLM.json.";
    } else {
        pre.textContent = (await getPresets(name))[name] ?? "(preset not found: it may have been removed from the preset files)";
    }
    pop.append(pre);
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
            </div>
            <div class="mnemic-llm-buttons">
                <button class="mnemic-llm-btn" data-act="models" title="Browse the models this endpoint offers">🔍 Models</button>
                <button class="mnemic-llm-btn" data-act="test" title="Check that the endpoint answers">⚡ Test</button>
                <button class="mnemic-llm-btn" data-act="preset" title="Show the selected preset's system prompt">📜 Preset</button>
                <button class="mnemic-llm-btn" data-act="copy" title="Copy the last reply">📋 Copy</button>
            </div>
            <div class="mnemic-llm-out empty">The reply will appear here.</div>
            <div class="mnemic-llm-stats"></div>
        `;
        this.dot = this.el.querySelector(".mnemic-llm-dot");
        this.where = this.el.querySelector('[data-role="where"]');
        this.key = this.el.querySelector('[data-role="key"]');
        this.host = this.el.querySelector(".mnemic-llm-host");
        this.out = this.el.querySelector(".mnemic-llm-out");
        this.stats = this.el.querySelector(".mnemic-llm-stats");

        this.el.addEventListener("pointerdown", (e) => {
            if (e.target.closest("button, .mnemic-llm-out")) e.stopPropagation();
        });
        this.out.addEventListener("wheel", (e) => {
            if (this.out.scrollHeight > this.out.clientHeight) e.stopPropagation();
        }, { passive: true });
        this.el.querySelectorAll("button").forEach((b) => b.addEventListener("click", (e) => {
            e.stopPropagation();
            this.onButton(b.dataset.act, b);
        }));

        this.domWidget = node.addDOMWidget("llm_panel", "mnemic_llm_panel", this.el, {
            serialize: false,
            hideOnZoom: false,
            getMinHeight: () => 150,
            getValue: () => "",
            setValue: () => {},
        });
        this.domWidget.serialize = false;
    }

    widget(name) {
        return this.node.widgets?.find((w) => w.name === name);
    }

    matches(id) {
        const own = String(this.node.id);
        const s = String(id);
        return s === own || s.endsWith(`:${own}`);
    }

    // ---- endpoint status ------------------------------------------------

    async refreshStatus(force = false) {
        const byName = await getEndpoints(force);
        const name = this.widget("endpoint")?.value;
        const info = byName.get(name);
        this.info = info;
        if (!info) {
            this.setChip(this.where, "❔ Unknown endpoint", true);
            this.setChip(this.key, "", false);
            this.host.textContent = "";
            if (this.state === "idle") this.setDot("warn");
            return;
        }
        const [icon, label] = LOCATION_LABEL[info.location] ?? LOCATION_LABEL.unknown;
        this.setChip(this.where, `${icon} ${label} · ${info.provider}`, info.location === "unknown");
        if (info.key_env) {
            this.setChip(this.key, info.key_set ? "🔑 key set" : info.key_optional ? "🔓 no key" : `🔑 ${info.key_env} missing`, !info.key_set && !info.key_optional);
        } else {
            this.setChip(this.key, "🔓 no key needed", false);
        }
        this.host.title = [info.description, ...info.problems].filter(Boolean).join("\n\n");
        this.updateModelHint();
        if (this.state === "idle") {
            // Green once configured; ⚡ Test checks that it actually answers.
            this.setDot(info.ok ? "ok" : "warn");
            if (!info.ok && !this.result) this.showNote(info.problems.join(" "), false);
            else if (info.ok && !this.result) this.showNote("The reply will appear here.", false);
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
        if (!model) {
            hint = this.info.default_model
                ? `model: ${this.info.default_model} (default)`
                : this.info.provider === "ollama" ? "model: one in memory, else first installed"
                : ["local", "network"].includes(this.info.location) ? "model: first the server lists"
                : "no model chosen";
        }
        this.host.textContent = [this.info.host, hint].filter(Boolean).join(" · ");
    }

    // ---- presets --------------------------------------------------------

    async updatePresetState() {
        const preset = this.widget("preset")?.value;
        const system = this.widget("system_message");
        const input = system?.inputEl;
        if (!input) return;
        if (preset && preset !== DEFAULT_PRESET) {
            const text = (await getPresets(preset))[preset] ?? "";
            input.style.opacity = "0.45";
            input.title = "Ignored while a preset is selected.";
            input.dataset.mnemicPlaceholder ??= input.placeholder ?? "";
            input.placeholder = `Preset “${preset}” is active:\n\n${text.slice(0, 600)}${text.length > 600 ? "…" : ""}`;
        } else {
            input.style.opacity = "";
            input.title = "";
            if (input.dataset.mnemicPlaceholder !== undefined) input.placeholder = input.dataset.mnemicPlaceholder;
        }
    }

    // ---- models ---------------------------------------------------------

    setModel(id) {
        const w = this.widget("model");
        if (!w) return;
        w.value = id;
        w.callback?.(id);
        this.rememberModel();
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
        this.result = null;
        this.stats.textContent = "";
        this.refreshStatus();
    }

    // ---- buttons --------------------------------------------------------

    async onButton(act, button) {
        if (act === "models") return showModelPicker(this, button);
        if (act === "preset") return showPreset(this, button);
        if (act === "copy") {
            const text = this.result?.text ?? "";
            if (!text) return;
            const ok = await copyText(text);
            button.textContent = ok ? "✓ Copied" : "Copy failed";
            setTimeout(() => (button.textContent = "📋 Copy"), 1200);
            return;
        }
        if (act === "test") {
            button.disabled = true;
            await this.refreshStatus(true);
            this.setDot("busy");
            const endpoint = this.widget("endpoint")?.value;
            const data = await getModels(endpoint, true);
            button.disabled = false;
            // A slow test must not paint over a newer endpoint or a running reply.
            if (this.widget("endpoint")?.value !== endpoint || this.state === "running") return;
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
            this.state = "running";
            this.startedAt = performance.now();
            this.setDot("busy");
            this.showNote(`Waiting for ${msg.model} on ${msg.endpoint}…`, false);
            this.stats.textContent = "";
        } else if (msg.phase === "stream") {
            this.state = "running";
            this.setDot("busy");
            const [text, inline] = splitInlineThinking(msg.text ?? "");
            this.renderReply(text, [msg.thinking, inline].filter(Boolean).join("\n\n"), true);
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
    name: "MNeMiC.LLMAPI",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);
            const panel = new LLMPanel(this);
            this.mnemicLLM = panel;

            chainCallback(panel.widget("endpoint"), (_value, previous) => panel.onEndpointChanged(previous));
            chainCallback(panel.widget("preset"), () => panel.updatePresetState());
            chainCallback(panel.widget("model"), () => {
                panel.rememberModel();
                panel.updateModelHint();
            });

            const [w, h] = this.size;
            this.setSize([Math.max(w, 400), Math.max(h, this.computeSize()[1])]);
            requestAnimationFrame(() => {
                panel.refreshStatus();
                panel.updatePresetState();
            });
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
                requestAnimationFrame(() => {
                    // Undo/redo and tab switches rebuild the node, and
                    // onExecuted is not replayed: restore the last reply.
                    const outputs = app.nodeOutputs ?? {};
                    const key = Object.keys(outputs).find((k) => panel.matches(k) && outputs[k]?.mnemic_llm?.[0]);
                    if (key && !panel.result) panel.onResult(outputs[key].mnemic_llm[0]);
                    panel.refreshStatus();
                    panel.updatePresetState();
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
