import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

const NODE_ID = "MNeMiC_VideoCompareDiff";

// Diff modes, in shader order. The export on the server (DIFF_MODES) uses the same order.
const MODES = [
    { name: "Difference", title: "|A − B| per channel, times the gain." },
    { name: "Grayscale", title: "Brightness of |A − B|, times the gain." },
    { name: "Heatmap", title: "Largest channel difference as a heatmap: blue is equal, red is very different." },
    { name: "Signed (B − A)", title: "Grey where equal, brighter where B is brighter, darker where B is darker." },
    { name: "Threshold over A", title: "Red where any channel differs by more than the threshold, over a dimmed grayscale A." },
    { name: "Blend 50%", title: "A and B mixed half and half, like onion skinning." },
];

// Gain doubles per slider step: 1×, 2×, 4× … 64×.
const GAIN_STEPS = 6;
const SPEEDS = [0.1, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
const MAX_LOADING = 6;

// Player settings, saved with the workflow in node.properties.mnmVideoDiff.
const DEFAULT_SETTINGS = {
    mode: MODES[0].name,
    gainStep: 0, // 1×
    threshold: 8, // in 0-255 levels
    loop: true,
    in: null, // loop section, as frame indices; null for the whole video
    out: null,
    fps: null, // null uses the video's own frame rate
    speed: 1,
    volume: 1,
    muted: true,
    audio: "a", // whose sound plays when both videos have one
    swapped: false, // B on the left; the diff then treats B as the first video
    exportFormat: "mp4", // "mp4" or "png"
    maskType: "threshold", // "threshold" or "soft"
    exports: "diff", // what Export and export_on_run save: "diff", "mask" or "both"
};

// Files the player accepts for A and B: videos, and images as one-frame (or animated) clips.
const MEDIA_ACCEPT = "video/*,image/*";
const isMediaFile = (file) => file.type.startsWith("video/") || file.type.startsWith("image/");

/** A mode's name or description as shown: A and B trade places while swapped. */
const swapLetters = (text, swapped) => swapped ? text.replace(/\b[AB]\b/g, (letter) => (letter === "A" ? "B" : "A")) : text;

const VERTEX_SHADER = `
attribute vec2 position;
varying vec2 uv;
void main() {
    uv = vec2(position.x * 0.5 + 0.5, 0.5 - position.y * 0.5);
    gl_Position = vec4(position, 0.0, 1.0);
}`;

const FRAGMENT_SHADER = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform sampler2D a;
uniform sampler2D b;
uniform int mode;
uniform float gain;
uniform float threshold; // in 0-255 levels
varying vec2 uv;
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

// Polynomial approximation of the Turbo colormap.
vec3 turbo(float x) {
    vec4 v4 = vec4(1.0, x, x * x, x * x * x);
    vec2 v2 = v4.zw * v4.z;
    return vec3(
        dot(v4, vec4(0.13572138, 4.61539260, -42.66032258, 132.13108234)) + dot(v2, vec2(-152.94239396, 59.28637943)),
        dot(v4, vec4(0.09140261, 2.19418839, 4.84296658, -14.18503333)) + dot(v2, vec2(4.27729857, 2.82956604)),
        dot(v4, vec4(0.10667330, 12.64194608, -60.58204836, 110.36276771)) + dot(v2, vec2(-89.90310912, 27.34824973)));
}

void main() {
    vec3 ca = texture2D(a, uv).rgb;
    vec3 cb = texture2D(b, uv).rgb;
    vec3 d = abs(ca - cb);
    float largest = max(d.r, max(d.g, d.b));
    vec3 color;
    if (mode == 0) color = d * gain;
    else if (mode == 1) color = vec3(dot(d, LUMA) * gain);
    else if (mode == 2) color = turbo(clamp(largest * gain, 0.0, 1.0));
    else if (mode == 3) color = 0.5 + (cb - ca) * gain * 0.5;
    // Compare whole levels, so a difference equal to the threshold is never marked.
    else if (mode == 4) color = floor(largest * 255.0 + 0.5) > threshold ? vec3(1.0, 0.15, 0.15) : vec3(dot(ca, LUMA) * 0.5);
    else color = mix(ca, cb, 0.5);
    gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}`;

const STYLE = `
.mnm-vd { display: flex; flex-direction: column; gap: 8px; height: 100%; min-height: 0; box-sizing: border-box; font-size: 14px; color: var(--input-text, #ddd); outline: none; }
.mnm-vd-panels { position: relative; flex: 1; min-height: 0; display: flex; gap: 4px; }
.mnm-vd-panel { flex: 1; min-width: 0; position: relative; overflow: hidden; border-radius: 4px; background: rgba(0,0,0,0.35); cursor: pointer; }
.mnm-vd-panel canvas { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.mnm-vd-label { position: absolute; left: 6px; top: 6px; padding: 2px 8px; border-radius: 4px; background: rgba(0,0,0,0.6); font-size: 13px; pointer-events: none; white-space: nowrap; }
.mnm-vd-hint { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; padding: 10px; opacity: 0.65; font-style: italic; pointer-events: none; text-align: center; white-space: pre-line; overflow-wrap: anywhere; }
.mnm-vd-hint.mnm-vd-over { opacity: 1; font-style: normal; background: rgba(0,0,0,0.65); }
.mnm-vd-panel.mnm-vd-drop { outline: 2px dashed #4a9eff; outline-offset: -3px; }
/* One row of controls that wraps by group when the node is too narrow. */
.mnm-vd-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px; flex: 0 0 auto; min-width: 0; }
.mnm-vd-group { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.mnm-vd button { all: unset; box-sizing: border-box; height: 34px; padding: 0 10px; min-width: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border-radius: 6px; cursor: pointer; background: var(--comfy-input-bg, #333); border: 1px solid var(--border-color, #555); white-space: nowrap; }
.mnm-vd button svg { width: 20px; height: 20px; flex: none; }
.mnm-vd button.mnm-vd-icon { width: 34px; padding: 0; }
.mnm-vd button.mnm-vd-play { width: 46px; height: 38px; padding: 0; background: #2f6fb8; border-color: #4a9eff; }
.mnm-vd button.mnm-vd-play svg { width: 24px; height: 24px; }
.mnm-vd button:hover { filter: brightness(1.25); }
.mnm-vd button.mnm-vd-on { background: #2f6fb8; border-color: #4a9eff; }
.mnm-vd button:disabled { opacity: 0.5; cursor: progress; filter: none; }
.mnm-vd select, .mnm-vd input[type=number] { box-sizing: border-box; height: 34px; background: var(--comfy-input-bg, #333); color: inherit; border: 1px solid var(--border-color, #555); border-radius: 6px; font-size: 14px; padding: 0 8px; }
.mnm-vd input[type=number] { width: 70px; }
/* Slim sliders: a thin track and a small round knob, instead of the browser's oversized default. */
.mnm-vd input[type=range] { -webkit-appearance: none; appearance: none; width: 140px; height: 34px; margin: 0; padding: 0; background: transparent; cursor: pointer; }
.mnm-vd input[type=range]::-webkit-slider-runnable-track { height: 6px; border-radius: 3px; background: var(--border-color, #555); }
.mnm-vd input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; margin-top: -5px; border: none; border-radius: 50%; background: #4a9eff; }
.mnm-vd input[type=range]::-moz-range-track { height: 6px; border-radius: 3px; background: var(--border-color, #555); }
.mnm-vd input[type=range]::-moz-range-thumb { width: 16px; height: 16px; border: none; border-radius: 50%; background: #4a9eff; }
.mnm-vd-track { position: relative; flex: 1 1 260px; min-width: 180px; height: 30px; box-sizing: border-box; border-radius: 6px; background: rgba(255,255,255,0.08); border: 1px solid var(--border-color, #555); cursor: pointer; touch-action: none; }
.mnm-vd-section { position: absolute; top: 0; bottom: 0; background: rgba(74,158,255,0.25); border-left: 3px solid #4a9eff; border-right: 3px solid #4a9eff; box-sizing: border-box; pointer-events: none; }
.mnm-vd-loaded { position: absolute; left: 0; bottom: 0; height: 3px; background: rgba(255,255,255,0.35); pointer-events: none; }
.mnm-vd-head { position: absolute; top: -3px; bottom: -3px; width: 3px; margin-left: -1.5px; border-radius: 2px; background: #fff; pointer-events: none; }
/* Fixed widths, so changing numbers never move the other controls. */
.mnm-vd-counter { width: 20ch; flex: none; text-align: right; font-family: monospace; font-size: 14px; white-space: nowrap; overflow: hidden; }
.mnm-vd-value { width: 5ch; flex: none; font-family: monospace; font-size: 14px; white-space: nowrap; }
`;

// Button icons: 24×24 outlines in the text color, like the rest of ComfyUI.
const ICONS = {
    first: '<path d="M6 5v14"/><path d="M18 6l-8 6 8 6z" fill="currentColor"/>',
    last: '<path d="M18 5v14"/><path d="M6 6l8 6-8 6z" fill="currentColor"/>',
    previous: '<path d="M15 5l-7 7 7 7"/>',
    next: '<path d="M9 5l7 7-7 7"/>',
    play: '<path d="M7 4.5v15l12.5-7.5z" fill="currentColor" stroke="none"/>',
    pause: '<rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none"/>',
    loop: '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    swap: '<path d="M8 3L4 7l4 4"/><path d="M4 7h16"/><path d="M16 21l4-4-4-4"/><path d="M20 17H4"/>',
    note: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    muted: '<path d="M11 5L6 9H2v6h4l5 4z" fill="currentColor"/><path d="M22 9l-6 6"/><path d="M16 9l6 6"/>',
    silent: '<path d="M11 5L6 9H2v6h4l5 4z" fill="currentColor"/>',
    volume: '<path d="M11 5L6 9H2v6h4l5 4z" fill="currentColor"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
};

/** Show an icon and/or a label on a button, rewriting it only when they change. */
function setButton(target, icon, label = "") {
    const key = `${icon}|${label}`;
    if (target.mnmContent === key) return;
    target.mnmContent = key;
    target.replaceChildren();
    if (icon) {
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("fill", "none");
        svg.setAttribute("stroke", "currentColor");
        svg.setAttribute("stroke-width", "2");
        svg.setAttribute("stroke-linecap", "round");
        svg.setAttribute("stroke-linejoin", "round");
        svg.setAttribute("aria-hidden", "true");
        svg.innerHTML = ICONS[icon];
        target.append(svg);
    }
    if (label) target.append(element("span", "", { textContent: label }));
}

/** Set a property only when its value changes. Rewriting an open dropdown's options or a hovered title every frame makes them flicker. */
function put(target, key, value) {
    if (target[key] !== value) target[key] = value;
}

let styleAdded = false;

function addStyle() {
    if (styleAdded) return;
    styleAdded = true;
    const style = document.createElement("style");
    style.textContent = STYLE;
    document.head.appendChild(style);
}

function element(tag, className, props = {}) {
    const result = Object.assign(document.createElement(tag), props);
    if (className) result.className = className;
    return result;
}

/** A WebGL renderer drawing the diff of two frames, or null without WebGL. */
function createDiffRenderer(canvas) {
    const gl = canvas.getContext("webgl", { premultipliedAlpha: false, antialias: false });
    if (!gl) return null;
    const compile = (type, source) => {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        return shader;
    };
    const program = gl.createProgram();
    gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX_SHADER));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.warn("Video Compare Diff: shader failed to link", gl.getProgramInfoLog(program));
        return null;
    }
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, "position");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    // Upload the exact stored pixel values.
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    for (const [unit, name] of [[0, "a"], [1, "b"]]) {
        gl.activeTexture(gl.TEXTURE0 + unit);
        gl.bindTexture(gl.TEXTURE_2D, gl.createTexture());
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.uniform1i(gl.getUniformLocation(program, name), unit);
    }
    const modeAt = gl.getUniformLocation(program, "mode");
    const gainAt = gl.getUniformLocation(program, "gain");
    const thresholdAt = gl.getUniformLocation(program, "threshold");
    const uploaded = [null, null];

    return {
        draw(imageA, imageB, mode, gain, threshold) {
            if (canvas.width !== imageA.naturalWidth || canvas.height !== imageA.naturalHeight) {
                canvas.width = imageA.naturalWidth;
                canvas.height = imageA.naturalHeight;
            }
            gl.viewport(0, 0, canvas.width, canvas.height);
            [imageA, imageB].forEach((image, unit) => {
                if (uploaded[unit] === image) return;
                uploaded[unit] = image;
                gl.activeTexture(gl.TEXTURE0 + unit);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
            });
            gl.uniform1i(modeAt, mode);
            gl.uniform1f(gainAt, gain);
            gl.uniform1f(thresholdAt, threshold);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        },
        forget() {
            uploaded[0] = uploaded[1] = null;
        },
        destroy() {
            gl.getExtension("WEBGL_lose_context")?.loseContext();
        },
    };
}

/** Draw an image onto a 2D canvas at its own size. */
function drawImage(canvas, image) {
    if (canvas.width !== image.naturalWidth || canvas.height !== image.naturalHeight) {
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
    }
    canvas.getContext("2d").drawImage(image, 0, 0);
}

const isReady = (image) => image.complete && image.naturalWidth > 0;

/** Add the A | B | Diff player to a Video Compare Diff node. */
function addPlayer(node) {
    addStyle();
    node.properties ??= {};
    let settings = { ...DEFAULT_SETTINGS, ...node.properties.mnmVideoDiff };
    // Stored when a change is finished, not on every slider step, so dragging
    // a slider does not make the node re-render.
    const save = () => {
        node.properties.mnmVideoDiff = { ...settings };
        syncSettingsWidget();
    };
    const widgetNamed = (name) => node.widgets?.find((widget) => widget.name === name);

    // --- DOM ---
    const root = element("div", "mnm-vd", { tabIndex: 0 });
    const panels = element("div", "mnm-vd-panels");
    const makePanel = (canvas) => {
        const panel = element("div", "mnm-vd-panel");
        const label = element("div", "mnm-vd-label");
        const hint = element("div", "mnm-vd-hint");
        panel.append(canvas, label, hint);
        panels.append(panel);
        return { panel, label, hint };
    };
    const canvasLeft = element("canvas");
    const canvasRight = element("canvas");
    const canvasDiff = element("canvas");
    const { panel: panelLeft, label: labelLeft, hint: hintLeft } = makePanel(canvasLeft);
    const { panel: panelRight, label: labelRight, hint: hintRight } = makePanel(canvasRight);
    const { panel: panelDiff, label: labelDiff, hint: hintDiff } = makePanel(canvasDiff);
    const picker = element("input", "", { type: "file", accept: MEDIA_ACCEPT, multiple: true });
    picker.style.display = "none";

    const text = (value, className = "") => element("span", className, { textContent: value });
    const group = (...children) => {
        const result = element("span", "mnm-vd-group");
        result.append(...children);
        return result;
    };
    // A button with an icon, a label or both. Icon-only buttons are square.
    const button = (icon, label, title, onClick, className = label ? "" : "mnm-vd-icon") => {
        const result = element("button", className, { type: "button", title });
        setButton(result, icon, label);
        result.addEventListener("click", onClick);
        return result;
    };
    const slider = (min, max, step, title, onInput) => {
        const input = element("input", "", { type: "range", min, max, step, title });
        input.addEventListener("input", () => onInput(Number(input.value)));
        input.addEventListener("change", save);
        return input;
    };

    // Controls: frame stepping, play, scrub bar, loop, speed, frame rate, diff, sound, export.
    const playButton = button("play", "", "Play / pause (Space)", () => togglePlay(), "mnm-vd-play");
    const track = element("div", "mnm-vd-track", { title: "Drag to scrub. Drag the blue edges to move the loop section, or Shift+drag to draw a new one." });
    const sectionBar = element("div", "mnm-vd-section");
    const loadedBar = element("div", "mnm-vd-loaded");
    const head = element("div", "mnm-vd-head");
    track.append(sectionBar, loadedBar, head);
    const counter = text("", "mnm-vd-counter");
    const loopButton = button("loop", "Loop", "Loop playback (L)", () => {
        settings.loop = !settings.loop;
        save();
        updateControls();
    });
    const speedSlider = slider(0, SPEEDS.length - 1, 1, "Playback speed. Double-click for 1×.", (index) => {
        settings.speed = SPEEDS[index];
        updateControls();
        syncAudio();
    });
    speedSlider.addEventListener("dblclick", () => {
        settings.speed = 1;
        save();
        updateControls();
        syncAudio();
    });
    const speedValue = text("", "mnm-vd-value");
    const FPS_TITLE = "Frames per second of the video: how many frames make one second. Auto uses the video's own frame rate, or 24 for image batches.";
    const fpsSlider = slider(1, 120, 1, FPS_TITLE, (value) => {
        settings.fps = value;
        updateControls();
        syncAudio(true);
    });
    const fpsInput = element("input", "", { type: "number", min: 1, max: 240, step: "any", title: FPS_TITLE });
    fpsInput.addEventListener("change", () => {
        const value = Number(fpsInput.value);
        settings.fps = value > 0 ? value : null;
        save();
        updateControls();
        syncAudio(true);
    });
    const fpsAuto = button(null, "Auto", "Use the video's own frame rate, or 24 for image batches", () => {
        settings.fps = null;
        save();
        updateControls();
        syncAudio(true);
    });
    const muteButton = button("muted", "", "Mute / unmute (M)", () => {
        settings.muted = !settings.muted;
        save();
        updateControls();
        syncAudio(true);
    });
    const volumeSlider = slider(0, 100, 1, "Volume", (value) => {
        settings.volume = value / 100;
        settings.muted = false;
        updateControls();
        syncAudio();
    });
    const volumeValue = text("", "mnm-vd-value");
    const audioSourceButton = button("note", "A", "Play the sound of A or B", () => {
        settings.audio = settings.audio === "a" ? "b" : "a";
        save();
        setAudioSource();
    });
    const modeSelect = element("select", "", { title: "How the Diff panel shows the difference." });
    for (const mode of MODES) modeSelect.append(element("option", "", { value: mode.name, textContent: mode.name, title: mode.title }));
    modeSelect.addEventListener("change", () => {
        settings.mode = modeSelect.value;
        save();
        render();
    });
    const gainSlider = slider(0, GAIN_STEPS, 1, "Gain: multiplies the difference so small changes become visible. Each step doubles it: 1×, 2×, 4× … 64×. Also scales the soft mask.", (value) => {
        settings.gainStep = value;
        render();
    });
    const thresholdSlider = slider(0, 64, 1, "Threshold in 0-255 levels: larger differences are red in Threshold over A, and white in the threshold mask.", (value) => {
        settings.threshold = value;
        render();
    });
    const gainValue = text("", "mnm-vd-value");
    const thresholdValue = text("", "mnm-vd-value");
    const swapButton = button("swap", "Swap", "Swap A and B: B on the left, and the diff compares B against A (S)", () => {
        settings.swapped = !settings.swapped;
        save();
        render();
    });
    const choice = (title, options, key) => {
        const select = element("select", "", { title });
        for (const [value, label] of options) select.append(element("option", "", { value, textContent: label }));
        select.addEventListener("change", () => {
            settings[key] = select.value;
            save();
        });
        return select;
    };
    const exportsSelect = choice("What Export saves, and what export_on_run saves on every run.",
        [["diff", "Diff"], ["mask", "Mask"], ["both", "Diff + mask"]], "exports");
    const formatSelect = choice("MP4: one video, with the sound that is playing. PNG: lossless frames in a folder, or one PNG for a single frame.",
        [["mp4", "MP4"], ["png", "PNG"]], "exportFormat");
    const maskSelect = choice("Threshold mask: white where any channel differs by more than the threshold. Soft mask: the largest difference times the gain.",
        [["threshold", "Threshold mask"], ["soft", "Soft mask"]], "maskType");
    const exportButton = button(null, "Export", "Save now to the output folder, at filename_prefix, with the current settings. Exports the loop section when one is set, otherwise every frame.", () => exportNow());
    const controls = element("div", "mnm-vd-controls");
    controls.append(
        group(
            button("first", "", "First frame of the section (Home)", () => seek(section()[0])),
            button("previous", "", "Previous frame (←, Shift+← for 10)", () => step(-1)),
            button("next", "", "Next frame (→, Shift+→ for 10)", () => step(1)),
            button("last", "", "Last frame of the section (End)", () => seek(section()[1])),
        ),
        playButton,
        track,
        counter,
        group(
            loopButton,
            button(null, "[ In", "Start the loop section at this frame (I)", () => setSection(state.frame, section()[1])),
            button(null, "Out ]", "End the loop section at this frame (O)", () => setSection(section()[0], state.frame)),
            button(null, "Clear", "Remove the loop section and use the whole video", () => setSection(null, null)),
        ),
        group(text("Speed"), speedSlider, speedValue),
        group(text("FPS"), fpsSlider, fpsInput, fpsAuto),
        group(swapButton, text("Diff"), modeSelect),
        group(text("Gain"), gainSlider, gainValue),
        group(text("Threshold"), thresholdSlider, thresholdValue),
        group(audioSourceButton, muteButton, volumeSlider, volumeValue),
        group(exportsSelect, formatSelect, maskSelect, exportButton),
    );

    root.append(panels, controls);
    root.addEventListener("pointerdown", (event) => event.stopPropagation());
    root.append(picker);

    // --- Video files dropped or chosen on the player ---
    const fileWidget = (letter) => node.widgets?.find((widget) => widget.name === `file_${letter}`);
    const connected = (letter) => node.inputs?.some((input) => input.name === `video_${letter}` && input.link != null);
    // The video a side panel shows: A on the left unless swapped.
    const sideLetter = (side) => ((side === "left") !== settings.swapped ? "a" : "b");
    // Upload progress or the newly chosen file, shown over a panel until the next run.
    const pending = { a: "", b: "" };

    async function upload(letter, file) {
        pending[letter] = `Uploading ${file.name}…`;
        updateControls();
        try {
            const body = new FormData();
            body.append("image", file);
            body.append("type", "temp");
            const response = await api.fetchApi("/upload/image", { method: "POST", body });
            if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
            const data = await response.json();
            const name = data.subfolder ? `${data.subfolder}/${data.name}` : data.name;
            const widget = fileWidget(letter);
            if (!widget.options.values.includes(name)) widget.options.values.push(name);
            widget.value = name;
            widget.callback?.(name);
            pending[letter] = `${name}\nRun the workflow to load it.`;
            if (connected(letter)) pending[letter] += `\nThe connected ${letter.toUpperCase()} input is used instead.`;
        } catch (error) {
            pending[letter] = `Upload failed: ${error.message}`;
        }
        node.setDirtyCanvas?.(true, true);
        updateControls();
    }

    /**
     * Upload dropped or chosen videos and images. Two or more fill A and B in order; one
     * goes to `letter`, or without one to A, or to B when A already has a file.
     */
    function useFiles(files, letter) {
        const media = [...files].filter(isMediaFile);
        if (!media.length) return false;
        const targets = media.length > 1 ? ["a", "b"] : [letter ?? (fileWidget("a")?.value ? "b" : "a")];
        targets.forEach((target, index) => upload(target, media[index]));
        return true;
    }

    let pickerLetter = "a";
    picker.addEventListener("change", () => {
        useFiles(picker.files, pickerLetter);
        picker.value = "";
    });

    for (const [panel, side] of [[panelLeft, "left"], [panelRight, "right"], [panelDiff, null]]) {
        panel.addEventListener("click", () => {
            if (state.source) togglePlay();
            else if (side) {
                pickerLetter = sideLetter(side);
                picker.click();
            }
        });
        // Handle the drop here, so ComfyUI does not also try to open the file as a workflow.
        panel.addEventListener("dragover", (event) => {
            if (!event.dataTransfer?.types.includes("Files")) return;
            event.preventDefault();
            event.stopPropagation();
            event.dataTransfer.dropEffect = "copy";
            panel.classList.add("mnm-vd-drop");
        });
        panel.addEventListener("dragleave", (event) => {
            if (!panel.contains(event.relatedTarget)) panel.classList.remove("mnm-vd-drop");
        });
        panel.addEventListener("drop", (event) => {
            panel.classList.remove("mnm-vd-drop");
            if (!event.dataTransfer?.files.length) return;
            event.preventDefault();
            event.stopPropagation();
            useFiles(event.dataTransfer.files, side && sideLetter(side));
        });
    }

    // Keep the panel hints current when a file is picked from the list.
    for (const letter of ["a", "b"]) {
        const widget = fileWidget(letter);
        if (!widget) continue;
        const callback = widget.callback;
        widget.callback = function () {
            const result = callback?.apply(this, arguments);
            updateControls();
            return result;
        };
    }

    const renderer = createDiffRenderer(canvasDiff);
    const audio = new Audio();
    audio.preload = "auto";

    // --- State ---
    const state = {
        source: null, // the current run's frames and loading progress
        frame: 0,
        playing: false,
        waiting: false, // playback is held until the next frame has loaded
    };
    let animation = 0;
    let lastTime = 0;
    let due = 0;

    const total = () => state.source?.total ?? 0;
    const autoFps = () => state.source?.fps ?? 24;
    const fps = () => settings.fps || autoFps();
    const mode = () => MODES.find((item) => item.name === settings.mode) ?? MODES[0];
    const gain = () => 2 ** settings.gainStep;

    /** The loop section as [first, last] frame; the whole video when none is set. */
    const section = () => {
        const last = Math.max(0, total() - 1);
        const start = Math.min(Math.max(settings.in ?? 0, 0), last);
        const end = Math.min(Math.max(settings.out ?? last, start), last);
        return [start, end];
    };
    const hasSection = () => settings.in != null || settings.out != null;

    function setSection(start, end) {
        if (start == null || end == null) {
            settings.in = settings.out = null;
        } else if (total()) {
            settings.in = Math.min(start, end);
            settings.out = Math.max(start, end);
        }
        save();
        updateControls();
    }

    // --- Loading ---
    function fileUrl(subfolder, filename) {
        return api.apiURL(`/view?${new URLSearchParams({ filename, type: "temp", subfolder })}`);
    }

    /** The A and B images shown at a frame. A shorter video holds its last frame. */
    const imagesAt = (index) => [
        state.source.a[Math.min(index, state.source.a.length - 1)],
        state.source.b[Math.min(index, state.source.b.length - 1)],
    ];

    function request(source, image) {
        if (image.mnmRequested) return;
        image.mnmRequested = true;
        source.loading++;
        image.onload = image.onerror = () => {
            if (state.source !== source) return;
            source.loading--;
            source.done++;
            if (!isReady(image)) source.failed++;
            if (imagesAt(state.frame).includes(image)) render();
            else updateControls();
            pump(source);
        };
        image.src = image.mnmUrl;
    }

    /** Keep a few frames loading, in playback order. */
    function pump(source) {
        while (source.loading < MAX_LOADING && source.next < source.order.length) request(source, source.order[source.next++]);
    }

    function cancel(source) {
        for (const image of source.order) {
            image.onload = image.onerror = null;
            if (image.mnmRequested && !image.complete) image.src = "";
        }
    }

    function load(data) {
        pause();
        pending.a = pending.b = "";
        if (state.source) cancel(state.source);
        renderer?.forget();
        const makeFrames = (prefix, count) => Array.from({ length: count }, (_, index) =>
            Object.assign(new Image(), { mnmUrl: fileUrl(data.subfolder, `${prefix}_${String(index).padStart(5, "0")}.png`) }));
        const a = makeFrames("a", data.frames_a);
        const b = makeFrames("b", data.frames_b);
        const order = [];
        for (let i = 0; i < Math.max(a.length, b.length); i++) {
            if (a[i]) order.push(a[i]);
            if (b[i]) order.push(b[i]);
        }
        const sounds = ["a", "b"].filter((name) => data[`audio_${name}`]);
        state.source = { a, b, order, sounds, subfolder: data.subfolder, total: Math.max(a.length, b.length), fps: data.fps, next: 0, loading: 0, done: 0, failed: 0 };
        state.frame = Math.min(state.frame, total() - 1);
        pump(state.source);
        setAudioSource();
        if (data.exported?.length) notifyExported(data.exported);
    }

    // --- Sound ---
    /** The video whose sound plays: the chosen one if it has sound, else the other. */
    const audioName = () => {
        const sounds = state.source?.sounds ?? [];
        return sounds.includes(settings.audio) ? settings.audio : sounds[0] ?? null;
    };

    function setAudioSource() {
        const name = audioName();
        const url = name ? fileUrl(state.source.subfolder, `${name}.wav`) : null;
        if (audio.mnmUrl !== url) {
            audio.mnmUrl = url;
            audio.pause();
            if (url) audio.src = url;
            else audio.removeAttribute("src");
        }
        render();
        syncAudio(true);
    }

    /** Play the sound in step with the frames, or stop it. */
    function syncAudio(force = false) {
        audio.volume = settings.volume;
        audio.playbackRate = settings.speed;
        const time = (state.frame + due) / fps();
        const audible = audio.mnmUrl && !settings.muted && state.playing && !state.waiting && !(time >= audio.duration);
        if (!audible) {
            if (!audio.paused) audio.pause();
            return;
        }
        if (force || audio.paused || Math.abs(audio.currentTime - time) > 0.15) audio.currentTime = time;
        if (audio.paused) audio.play().catch(() => {});
    }

    // --- Rendering ---
    function render() {
        updateControls();
        if (!total()) return;
        const [imageA, imageB] = imagesAt(state.frame);
        request(state.source, imageA);
        request(state.source, imageB);
        if (!isReady(imageA) || !isReady(imageB)) return;
        const [left, right] = settings.swapped ? [imageB, imageA] : [imageA, imageB];
        drawImage(canvasLeft, left);
        drawImage(canvasRight, right);
        renderer?.draw(left, right, MODES.indexOf(mode()), gain(), settings.threshold);
    }

    function updateControls() {
        const source = state.source;
        const current = mode();
        for (const [hint, panel, side] of [[hintLeft, panelLeft, "left"], [hintRight, panelRight, "right"]]) {
            const letter = sideLetter(side);
            let note = pending[letter];
            if (!note && !source) {
                const file = fileWidget(letter)?.value;
                if (connected(letter)) note = `${letter.toUpperCase()} is connected.\nRun the workflow to load it.`;
                else if (file) note = `${file}\nRun the workflow to load it.`;
                else note = "Drop a video or image here,\nor click to choose one.";
            }
            put(hint, "textContent", note);
            put(hint.style, "display", note ? "" : "none");
            hint.classList.toggle("mnm-vd-over", !!source);
            put(panel, "title", source ? "Click to play or pause. Drop a video or image to replace this one." : "Click to choose a video or image, or drop one here.");
        }
        put(hintDiff, "textContent", "Run the workflow to compare A and B.");
        put(hintDiff.style, "display", source ? "none" : "");
        put(panelDiff, "title", source ? "Click to play or pause" : "Drop two videos or images to fill A and B.");
        setButton(playButton, state.playing ? "pause" : "play");
        loopButton.classList.toggle("mnm-vd-on", settings.loop);

        const speedIndex = SPEEDS.indexOf(settings.speed);
        put(speedSlider, "value", String(speedIndex === -1 ? SPEEDS.indexOf(1) : speedIndex));
        put(speedValue, "textContent", `${settings.speed}×`);
        put(fpsSlider, "value", String(Math.round(fps())));
        if (document.activeElement !== fpsInput) put(fpsInput, "value", String(Math.round(fps() * 100) / 100));
        fpsAuto.classList.toggle("mnm-vd-on", settings.fps == null);

        // Volume and mute stay usable without sound, ready for the next video.
        setButton(muteButton, settings.muted ? "muted" : settings.volume === 0 ? "silent" : "volume");
        put(muteButton, "title", audioName() ? "Mute / unmute (M)" : "Mute / unmute (M). The current videos have no sound.");
        put(volumeSlider, "value", String(Math.round(settings.volume * 100)));
        put(volumeValue, "textContent", `${Math.round(settings.volume * 100)}%`);
        put(audioSourceButton.style, "display", source?.sounds.length > 1 ? "" : "none");
        setButton(audioSourceButton, "note", (audioName() ?? "a").toUpperCase());

        swapButton.classList.toggle("mnm-vd-on", settings.swapped);
        for (const [index, option] of [...modeSelect.options].entries()) {
            put(option, "textContent", swapLetters(MODES[index].name, settings.swapped));
            put(option, "title", swapLetters(MODES[index].title, settings.swapped));
        }
        put(modeSelect, "value", current.name);
        put(gainSlider, "value", String(settings.gainStep));
        put(thresholdSlider, "value", String(settings.threshold));
        put(formatSelect, "value", settings.exportFormat);
        put(maskSelect, "value", settings.maskType);
        put(exportsSelect, "value", settings.exports);
        put(exportButton, "disabled", exporting);
        put(gainValue, "textContent", `${gain()}×`);
        put(thresholdValue, "textContent", String(settings.threshold));

        const count = total();
        const percent = (index) => (count > 1 ? index / (count - 1) : 0) * 100;
        const [start, end] = section();
        put(sectionBar.style, "display", hasSection() && count ? "" : "none");
        put(sectionBar.style, "left", `${percent(start)}%`);
        put(sectionBar.style, "width", `${percent(end) - percent(start)}%`);
        put(head.style, "left", `${percent(state.frame)}%`);
        put(loadedBar.style, "width", source ? `${(source.done / source.order.length) * 100}%` : "0px");

        if (!source) {
            put(counter, "textContent", "");
            put(labelLeft, "textContent", settings.swapped ? "B" : "A");
            put(labelRight, "textContent", settings.swapped ? "A" : "B");
            put(labelDiff, "textContent", "Diff");
            return;
        }
        put(counter, "textContent", source.failed
            ? `${source.failed} frames failed to load`
            : `${state.frame + 1} / ${count} · ${(state.frame / fps()).toFixed(2)}s`);
        const describe = (name, frames) => {
            const image = frames.find(isReady);
            return image ? `${name} · ${image.naturalWidth}×${image.naturalHeight} · ${frames.length}f` : `${name} · ${frames.length}f`;
        };
        const [left, right] = settings.swapped ? [["B", source.b], ["A", source.a]] : [["A", source.a], ["B", source.b]];
        put(labelLeft, "textContent", describe(...left));
        put(labelRight, "textContent", describe(...right));
        let diffLabel = renderer ? `Diff · ${swapLetters(current.name, settings.swapped)}` : "Diff · WebGL unavailable";
        if (source.done < source.order.length) diffLabel += ` · loading ${Math.round((source.done / source.order.length) * 100)}%`;
        put(labelDiff, "textContent", diffLabel);
    }

    // --- Playback ---
    function seek(index) {
        if (!total()) return;
        state.frame = Math.min(Math.max(Math.round(index), 0), total() - 1);
        due = 0;
        render();
        syncAudio(true);
    }

    function step(delta) {
        pause();
        seek(state.frame + delta);
    }

    /** The frame after the current one, or null at the end of the section without loop. */
    function nextFrame() {
        const [start, end] = section();
        if (state.frame < start || state.frame > end) return start;
        if (state.frame < end) return state.frame + 1;
        return settings.loop ? start : null;
    }

    function tick(time) {
        if (!state.playing) return;
        animation = requestAnimationFrame(tick);
        // Cap the step so a hidden tab does not jump far ahead when it returns.
        due += Math.min((time - lastTime) / 1000, 0.25) * fps() * settings.speed;
        lastTime = time;
        let changed = false;
        while (due >= 1) {
            const next = nextFrame();
            if (next === null) {
                pause();
                return;
            }
            // Wait for frames that are still loading instead of skipping them.
            const images = imagesAt(next);
            if (!images.every(isReady)) {
                images.forEach((image) => request(state.source, image));
                state.waiting = true;
                due = 0;
                break;
            }
            // Jumping back to the section start moves the sound with it.
            const wrapped = next < state.frame;
            state.frame = next;
            state.waiting = false;
            due -= 1;
            changed = true;
            if (wrapped) syncAudio(true);
        }
        if (changed) render();
        syncAudio();
    }

    function play() {
        if (state.playing || !total()) return;
        const [start, end] = section();
        if (state.frame < start || state.frame > end || (state.frame === end && !settings.loop)) state.frame = start;
        state.playing = true;
        state.waiting = false;
        due = 0;
        lastTime = performance.now();
        animation = requestAnimationFrame(tick);
        render();
        syncAudio(true);
    }

    function pause() {
        if (!state.playing) return;
        state.playing = false;
        cancelAnimationFrame(animation);
        syncAudio();
        updateControls();
    }

    function togglePlay() {
        if (state.playing) pause();
        else play();
    }

    // --- Export ---
    let exporting = false;

    const notify = (severity, summary, detail) => {
        if (app.extensionManager?.toast) app.extensionManager.toast.add({ severity, summary, detail, life: 6000 });
        else console.log(`Video Compare Diff: ${summary}: ${detail}`);
    };

    /** The settings an export uses, as the server reads them (EXPORT_DEFAULTS in video_compare_diff.py). */
    const exportSettings = (frameRate) => ({
        mode: MODES.indexOf(mode()),
        gain: gain(),
        threshold: settings.threshold,
        swapped: settings.swapped,
        start: settings.in,
        end: settings.out,
        fps: frameRate,
        audio: settings.audio,
        exports: settings.exports,
        format: settings.exportFormat,
        mask: settings.maskType,
    });

    // export_on_run reads the settings from the hidden player_settings widget. It stays empty
    // while export_on_run is off: otherwise every change in the player would change the node's
    // inputs, and the next run would write all the frames again for nothing.
    function syncSettingsWidget() {
        const storage = widgetNamed("player_settings");
        if (storage) storage.value = widgetNamed("export_on_run")?.value ? JSON.stringify(exportSettings(settings.fps)) : "";
    }

    const notifyExported = (paths) => notify("success", "Exported", paths.map((path) => `output/${path}`).join("\n"));

    /** Export the loaded frames right away, without running the workflow again. */
    async function exportNow() {
        if (!state.source) {
            notify("warn", "Nothing to export", "Run the workflow first.");
            return;
        }
        exporting = true;
        updateControls();
        try {
            const response = await api.fetchApi("/mnemic/video-compare-diff/export", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    subfolder: state.source.subfolder,
                    filename_prefix: widgetNamed("filename_prefix")?.value ?? "video_compare_diff/compare",
                    settings: exportSettings(fps()),
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.error || `${response.status} ${response.statusText}`);
            notifyExported(data.paths);
        } catch (error) {
            notify("error", "Export failed", error.message);
        } finally {
            exporting = false;
            updateControls();
        }
    }

    // --- Scrub bar ---
    function frameAt(event) {
        const rect = track.getBoundingClientRect();
        const fraction = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
        return Math.round(fraction * Math.max(0, total() - 1));
    }

    /** Which loop section edge is under the pointer, if any. */
    function edgeAt(event) {
        if (!hasSection() || total() < 2) return null;
        const rect = track.getBoundingClientRect();
        const x = (index) => rect.left + (index / (total() - 1)) * rect.width;
        const [start, end] = section();
        if (Math.abs(event.clientX - x(start)) <= 6) return "in";
        if (Math.abs(event.clientX - x(end)) <= 6) return "out";
        return null;
    }

    track.addEventListener("pointerdown", (event) => {
        if (!total() || event.button !== 0) return;
        event.preventDefault();
        root.focus({ preventScroll: true });
        const anchor = frameAt(event);
        const drag = event.shiftKey ? "draw" : edgeAt(event) ?? "scrub";
        const move = (moveEvent) => {
            const index = frameAt(moveEvent);
            if (drag === "draw") setSection(anchor, index);
            else if (drag === "in") setSection(index, section()[1]);
            else if (drag === "out") setSection(section()[0], index);
            seek(index);
        };
        const wasPlaying = state.playing;
        pause();
        track.setPointerCapture(event.pointerId);
        track.onpointermove = move;
        track.onpointerup = track.onpointercancel = () => {
            track.onpointermove = null;
            track.onpointerup = track.onpointercancel = null;
            if (wasPlaying) play();
        };
        move(event);
    });
    track.addEventListener("pointermove", (event) => {
        if (!track.onpointermove) track.style.cursor = edgeAt(event) ? "ew-resize" : "";
    });

    // --- Keyboard, while the player has focus ---
    root.addEventListener("keydown", (event) => {
        if (event.target.matches("input, select") || event.ctrlKey || event.metaKey || event.altKey) return;
        const amount = event.shiftKey ? 10 : 1;
        const actions = {
            " ": () => togglePlay(),
            ArrowLeft: () => step(-amount),
            ArrowRight: () => step(amount),
            Home: () => seek(section()[0]),
            End: () => seek(section()[1]),
            i: () => setSection(state.frame, section()[1]),
            o: () => setSection(section()[0], state.frame),
            l: () => loopButton.click(),
            m: () => muteButton.click(),
            s: () => swapButton.click(),
        };
        const action = actions[event.key.length === 1 ? event.key.toLowerCase() : event.key];
        if (!action) return;
        event.preventDefault();
        event.stopPropagation();
        action();
    });

    const widget = node.addDOMWidget("video_diff", "mnm_video_diff", root, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 300,
        getValue: () => "",
        setValue: () => {},
    });
    widget.serialize = false;

    node.mnmVideoDiff = {
        load,
        useFiles,
        refresh: updateControls,
        /** Pick up the settings a loaded workflow restored. */
        reload() {
            settings = { ...DEFAULT_SETTINGS, ...node.properties.mnmVideoDiff };
            syncSettingsWidget();
            setAudioSource();
        },
        destroy() {
            pause();
            if (state.source) cancel(state.source);
            audio.removeAttribute("src");
            renderer?.destroy();
        },
    };

    // player_settings is written by the player only, so keep it off the node.
    const storage = widgetNamed("player_settings");
    if (storage) {
        storage.hidden = true;
        storage.type = "hidden";
        storage.computeSize = () => [0, -4];
        storage.draw = () => {};
    }
    const exportOnRun = widgetNamed("export_on_run");
    if (exportOnRun) {
        const callback = exportOnRun.callback;
        exportOnRun.callback = function () {
            const result = callback?.apply(this, arguments);
            syncSettingsWidget();
            return result;
        };
    }
    syncSettingsWidget();
    updateControls();
}

app.registerExtension({
    name: "MNeMiC.VideoCompareDiff",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_ID) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            addPlayer(this);
            this.setSize([Math.max(this.size[0], 1100), Math.max(this.size[1], 640)]);
            return result;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            this.mnmVideoDiff?.reload();
            return result;
        };

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            const result = onExecuted?.apply(this, arguments);
            const data = message?.mnm_video_diff?.[0];
            if (data) this.mnmVideoDiff?.load(data);
            return result;
        };

        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.mnmVideoDiff?.destroy();
            return onRemoved?.apply(this, arguments);
        };

        // The panel hints say whether A and B are connected.
        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function () {
            const result = onConnectionsChange?.apply(this, arguments);
            this.mnmVideoDiff?.refresh();
            return result;
        };

        // Videos dropped on the node outside the player (title, widgets).
        nodeType.prototype.onDragOver = function (event) {
            return [...(event.dataTransfer?.items ?? [])].some((item) => item.kind === "file" && isMediaFile(item));
        };
        nodeType.prototype.onDragDrop = function (event) {
            return this.mnmVideoDiff?.useFiles(event.dataTransfer?.files ?? [], null) ?? false;
        };
    },

    // Temp files are gone after a restart. Clear a stale choice when a
    // workflow loads, so it does not fail validation while A or B is connected.
    async loadedGraphNode(node) {
        if (node.comfyClass !== NODE_ID) return;
        await Promise.all(["file_a", "file_b"].map(async (name) => {
            const widget = node.widgets?.find((item) => item.name === name);
            const value = widget?.value;
            if (typeof value !== "string" || !value) return;
            const separator = value.lastIndexOf("/");
            const query = new URLSearchParams({ filename: value.slice(separator + 1), subfolder: value.slice(0, Math.max(separator, 0)), type: "temp" });
            try {
                const response = await api.fetchApi(`/view?${query}`, { method: "HEAD" });
                if (response.status === 404 && widget.value === value) widget.value = "";
            } catch {
                // Keep the choice when the server could not check it.
            }
        }));
        node.mnmVideoDiff?.refresh();
    },
});
