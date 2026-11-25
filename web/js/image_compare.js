import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const GROUP = "MNeMiC.ImageCompare.";
const settings = [
    { key: "SplitView", name: "Split View", type: "boolean", defaultValue: false,
        tooltip: "Always show two sources with A/B selectors." },
    { key: "ShowSourceLabels", name: "Show source labels", type: "boolean", defaultValue: true,
        tooltip: "Identify each region by its connected input." },
    { key: "ReverseOrder", name: "Reverse comparison order", type: "boolean", defaultValue: true,
        tooltip: "Show sources in reverse order. In a horizontal wipe, B appears on the left." },
    { key: "Direction", name: "Wipe direction", type: "combo", defaultValue: "Horizontal",
        options: ["Horizontal", "Vertical", "Diagonal"], tooltip: "Direction of the two-source wipe." },
    { key: "Transparency", name: "Divider transparency (%)", type: "number", defaultValue: 70,
        attrs: { min: 0, max: 100, step: 1 } },
    { key: "Thickness", name: "Divider thickness (px)", type: "number", defaultValue: 1,
        attrs: { min: 0, max: 10, step: 0.5 } },
];

function preference(key) {
    return app.ui.settings.getSettingValue(GROUP + key) ?? settings.find(s => s.key === key).defaultValue;
}

function addComparer(node) {
    const root = document.createElement("div");
    root.style.cssText = "display:flex;flex-direction:column;height:100%;min-height:0;gap:6px;color-scheme:dark";
    const toolbar = document.createElement("div");
    toolbar.style.cssText = "display:flex;gap:10px;overflow-x:auto;flex:none";
    const stage = document.createElement("div");
    stage.style.cssText = "position:relative;flex:1;min-height:100px;background:#191a1c;border-radius:5px;overflow:hidden;touch-action:none";
    stage.tabIndex = 0;
    stage.setAttribute("role", "group");
    stage.setAttribute("aria-label", "Comparison wipe. Drag or use the arrow keys to move the divider.");

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none";
    svg.setAttribute("aria-hidden", "true");
    const lines = document.createElementNS(svg.namespaceURI, "path");
    lines.setAttribute("stroke", "white");
    lines.setAttribute("fill", "none");
    svg.append(lines);
    stage.append(svg);

    const timeline = document.createElement("input");
    timeline.type = "range";
    timeline.setAttribute("aria-label", "Video time");
    timeline.min = timeline.value = "0";
    timeline.hidden = true;
    root.append(toolbar, stage, timeline);
    const widget = node.addDOMWidget("comparison", "mnemic_image_compare", root, {
        serialize: false, hideOnZoom: false, getMinHeight: () => 260,
    });
    widget.serialize = false;

    let data = { sources: [] };
    const choices = new Map();
    const slots = [];
    const selections = [];
    let x = 0.5, y = 0.5;
    let rotation = 0, lastAngle = null;
    const radial = () => slots.length >= 3 && slots.length !== 4;

    // Anchor within the stage, accounting for the badge's own size at each edge.
    function placeBadge(slot, u, v) {
        slot.badge.style.left = `calc(${u * 100}% + ${5 - 10 * u}px)`;
        slot.badge.style.top = `calc(${v * 100}% + ${5 - 10 * v}px)`;
        slot.badge.style.transform = `translate(${-u * 100}%, ${-v * 100}%)`;
    }

    function layout() {
        const w = stage.clientWidth, h = stage.clientHeight;
        if (slots.length < 2) {
            if (slots.length) placeBadge(slots[0], 0, 0);
            lines.removeAttribute("d");
            stage.style.cursor = "default";
            return;
        }
        if (!w || !h) return;
        const cx = radial() ? w / 2 : x * w, cy = radial() ? h / 2 : y * h;
        const segments = [];
        function segment(x1, y1, x2, y2) {
            segments.push(`M ${x1} ${y1} L ${x2} ${y2}`);
        }
        const count = slots.length;
        const direction = preference("Direction");
        stage.style.cursor = count > 2 ? "move" : { Horizontal: "ew-resize", Vertical: "ns-resize", Diagonal: "nwse-resize" }[direction];
        if (count === 2) {
            placeBadge(slots[0], 0, 0);
            let clip;
            if (direction === "Vertical") {
                clip = `inset(${y * 100}% 0 0 0)`;
                segment(0, cy, w, cy);
            } else if (direction === "Diagonal") {
                const intercept = cx + cy;
                clip = `polygon(${intercept}px 0, ${w+h}px 0, ${w+h}px ${h}px, ${intercept-h}px ${h}px)`;
                segment(intercept, 0, intercept-h, h);
            } else {
                clip = `inset(0 0 0 ${x * 100}%)`;
                segment(cx, 0, cx, h);
            }
            slots[1].region.style.clipPath = clip;
            placeBadge(slots[1], direction === "Vertical" ? 0 : 1, direction === "Horizontal" ? 0 : 1);
        } else if (count === 4) {
            const right = (1-x)*100, bottom = (1-y)*100;
            const corners = [`0 ${right}% ${bottom}% 0`, `0 0 ${bottom}% ${x*100}%`,
                `${y*100}% ${right}% 0 0`, `${y*100}% 0 0 ${x*100}%`];
            slots.forEach((slot, i) => {
                slot.region.style.clipPath = `inset(${corners[i]})`;
                placeBadge(slot, i % 2, Math.floor(i / 2));
            });
            segment(cx, 0, cx, h);
            segment(0, cy, w, cy);
        } else {
            // Extend each triangle beyond the farthest corner, even for a three-way wipe.
            const radius = (Math.hypot(w, h) + 1) / Math.cos(Math.PI / count);
            const rays = slots.map((_, i) => {
                const angle = rotation + 2 * Math.PI * i / count - Math.PI / 2;
                return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
            });
            slots.forEach((slot, i) => {
                const [ax, ay] = rays[i], [bx, by] = rays[(i + 1) % count];
                slot.region.style.clipPath = `polygon(${cx}px ${cy}px, ${ax}px ${ay}px, ${bx}px ${by}px)`;
                // Follow the slice bisector toward the edge, keeping its center clear.
                const dx = (ax + bx) / 2 - cx, dy = (ay + by) / 2 - cy;
                const scale = 0.46 / Math.max(Math.abs(dx) / w, Math.abs(dy) / h);
                placeBadge(slot, 0.5 + dx * scale / w, 0.5 + dy * scale / h);
                segment(cx, cy, ax, ay);
            });
        }
        lines.setAttribute("d", segments.join(" "));
    }

    function position(nx, ny) {
        x = Math.max(0, Math.min(1, nx));
        y = Math.max(0, Math.min(1, ny));
        layout();
    }
    function drag(event) {
        const box = stage.getBoundingClientRect();
        if (radial()) {
            const dx = event.clientX - box.left - box.width / 2;
            const dy = event.clientY - box.top - box.height / 2;
            if (Math.hypot(dx, dy) < 2) {
                lastAngle = null;
                return;
            }
            const angle = Math.atan2(dy, dx);
            if (lastAngle !== null) rotation += angle - lastAngle;
            lastAngle = angle;
            layout();
            return;
        }
        position((event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height);
    }
    stage.onpointerdown = event => {
        if (slots.length < 2 || !event.isPrimary || event.button !== 0) return;
        event.stopPropagation();
        stage.focus({ preventScroll: true });
        stage.setPointerCapture(event.pointerId);
        lastAngle = null;
        drag(event);
    };
    stage.onpointermove = event => {
        if (stage.hasPointerCapture(event.pointerId)) drag(event);
    };
    stage.onkeydown = event => {
        const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
        if (!delta) return;
        event.preventDefault();
        event.stopPropagation();
        if (radial()) {
            rotation += (delta[0] + delta[1]) * Math.PI / 180;
            layout();
        } else position(x + delta[0] / 100, y + delta[1] / 100);
    };

    function render() {
        const sides = slots.map(slot => choices.get(slot.select?.value ?? slot.key));
        if (preference("ReverseOrder")) sides.reverse();
        const videos = sides.filter(side => side?.fps);
        timeline.hidden = !videos.length;
        timeline.max = String(Math.max(0, ...videos.map(v => (v.count - 1) / v.fps)));
        timeline.step = String(1 / Math.max(1, ...videos.map(v => v.fps)));
        sides.forEach((side, i) => {
            if (!side) return;
            const sourceLabel = !side.fps && side.count > 1 ? `${side.name} / ${side.frame + 1}` : side.name;
            if (slots[i].badge.textContent !== sourceLabel) slots[i].badge.textContent = sourceLabel;
            const frame = side.fps ? Math.min(side.count - 1, Math.floor(timeline.valueAsNumber * side.fps + 1e-6)) : side.frame;
            const filename = `${side.name}_${String(frame).padStart(5, "0")}.png`;
            const url = api.apiURL("/view?" + new URLSearchParams({ type: "temp", subfolder: data.folder, filename }));
            if (slots[i].img.getAttribute("src") !== url) slots[i].img.src = url;
        });
    }
    timeline.oninput = render;

    function addSelector(i, key) {
        const label = document.createElement("label");
        label.style.cssText = "display:flex;align-items:center;gap:5px;flex:1 0 118px;min-width:0";
        label.textContent = ["A", "B"][i];
        const select = document.createElement("select");
        select.style.cssText = "flex:1;min-width:0";
        for (const [id, item] of choices) select.add(new Option(item.label, id));
        select.disabled = choices.size < 2;
        select.value = choices.has(selections[i]) ? selections[i] : key;
        select.onchange = () => { selections[i] = select.value; render(); };
        label.append(select);
        toolbar.append(label);
        return select;
    }
    function buildSlots() {
        toolbar.replaceChildren();
        for (const { region } of slots) region.remove();
        slots.length = 0;
        const split = preference("SplitView");
        const keys = data.sources.map(source => source.name + "/0");
        if (keys.length === 1 && choices.size > 1) keys.push(data.sources[0].name + "/1");
        if (split && keys.length === 1) keys.push(keys[0]);
        if (split) keys.splice(2);
        toolbar.style.display = split && keys.length ? "flex" : "none";
        for (const [i, key] of keys.entries()) {
            const select = split ? addSelector(i, key) : null;
            const region = document.createElement("div");
            region.style.cssText = "position:absolute;inset:0;pointer-events:none";
            const img = document.createElement("img");
            img.alt = "";
            img.draggable = false;
            img.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#191a1c;pointer-events:none";
            const badge = document.createElement("span");
            badge.style.cssText = "display:var(--mnm-source-label-display,block);position:absolute;padding:1px 4px;border-radius:3px;background:rgba(20,21,23,.66);color:#eee;font:10px/1.4 system-ui;white-space:nowrap;user-select:none";
            region.append(img, badge);
            stage.insertBefore(region, svg);
            slots.push({ region, img, badge, select, key });
        }
        render();
    }
    function refresh(key) {
        stage.style.setProperty("--mnm-source-label-display", preference("ShowSourceLabels") ? "block" : "none");
        if (!key || key === "SplitView") buildSlots();
        if (key === "ReverseOrder") render();
        lines.style.opacity = String(1 - preference("Transparency") / 100);
        lines.style.strokeWidth = preference("Thickness") + "px";
        layout();
    }
    const changed = event => refresh(event.detail);
    window.addEventListener("mnemic-image-compare-settings", changed);
    const resize = new ResizeObserver(layout);
    resize.observe(stage);
    refresh();
    return {
        load(result) {
            data = result;
            choices.clear();
            for (const source of data.sources) {
                const label = source.name.replace("source_", "Source ");
                for (let frame = 0; frame < (source.fps ? 1 : source.count); frame++) {
                    choices.set(source.name + "/" + frame, { ...source, frame,
                        label: !source.fps && source.count > 1 ? label + " / Image " + (frame + 1) : label });
                }
            }
            timeline.value = "0";
            refresh();
        },
        dispose() {
            resize.disconnect();
            window.removeEventListener("mnemic-image-compare-settings", changed);
        },
    };
}

app.registerExtension({
    name: "MNeMiC.ImageCompare",
    settings: settings.map(({ key, ...setting }) => ({
        ...setting, id: GROUP + key, category: ["⚡MNeMiC Nodes", "Image Compare", setting.name],
        onChange: () => window.dispatchEvent(new CustomEvent("mnemic-image-compare-settings", { detail: key })),
    })),
    beforeRegisterNodeDef(nodeType, data) {
        if (data.name !== "MNeMiC_ImageCompare") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = created?.apply(this, arguments);
            this.comparer = addComparer(this);
            this.setSize([Math.max(this.size[0], 420), Math.max(this.size[1], 350)]);
            return result;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            const result = executed?.apply(this, arguments);
            if (message?.comparison?.[0]) this.comparer.load(message.comparison[0]);
            return result;
        };
        const removed = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.comparer?.dispose();
            return removed?.apply(this, arguments);
        };
    },
});
