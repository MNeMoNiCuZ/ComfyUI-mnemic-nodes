import { app } from "../../../scripts/app.js";

// Helpers for the Ideogram 4 Prompt Builder editor (adapted from KJNodes' utility.js).

export function chainCallback(object, property, callback) {
  if (object == undefined) {
    console.error("Tried to add callback to non-existant object");
    return;
  }
  if (property in object) {
    const callback_orig = object[property];
    object[property] = function () {
      const r = callback_orig.apply(this, arguments);
      callback.apply(this, arguments);
      return r;
    };
  } else {
    object[property] = callback;
  }
}

// ─── Middle-click pan passthrough for DOM widgets ───
// Allows panning the LiteGraph canvas via middle-click drag on any DOM element
export function addMiddleClickPan(element) {
  const onMouseDown = (e) => {
    if (e.button !== 1) return;
    e.preventDefault();
    const ds = app.canvas?.ds;
    if (!ds) return;
    const startX = e.clientX, startY = e.clientY;
    const startOffsetX = ds.offset[0], startOffsetY = ds.offset[1];
    const onMove = (me) => {
      ds.offset[0] = startOffsetX + (me.clientX - startX);
      ds.offset[1] = startOffsetY + (me.clientY - startY);
      app.canvas.setDirty(true, true);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };
  element.addEventListener('mousedown', onMouseDown);
  return () => element.removeEventListener('mousedown', onMouseDown);
}

// ─── Wheel zoom passthrough for DOM widgets ───
// Re-dispatches wheel events to the LiteGraph canvas for zoom
export function addWheelPassthrough(element) {
  element.addEventListener("wheel", (e) => {
    const gc = document.getElementById("graph-canvas");
    if (gc) {
      gc.dispatchEvent(new WheelEvent(e.type, e));
      e.preventDefault();
    }
  }, { passive: false });
}

// Returns the appropriate CSS cursor for a bbox hit mode string.
export function cursorForBboxMode(mode) {
  if (mode === "move") return "move";
  if (mode === "resize-tl" || mode === "resize-br") return "nwse-resize";
  if (mode === "resize-tr" || mode === "resize-bl") return "nesw-resize";
  if (mode === "resize-t" || mode === "resize-b") return "ns-resize";
  if (mode === "resize-l" || mode === "resize-r") return "ew-resize";
  return null;
}

// ─── Resolve preview image/video from a connected source node ───
// Walks the graph link to find what's connected to node.inputs[inputSlot]
// and returns { url, isVideo, videoEl } or null
export function resolveSourcePreview(node, inputSlot) {
  if (!node.graph) return null;
  const input = node.inputs?.[inputSlot];
  if (!input || input.link == null) return null;
  const link = node.graph.links?.get(input.link);
  if (!link) return null;
  const srcNode = node.graph.getNodeById(link.origin_id);
  if (!srcNode) return null;

  // Check for VHS-style video preview widget
  const vpWidget = srcNode.widgets?.find((w) => w.name === "videopreview");
  if (vpWidget?.videoEl?.src) {
    return { isVideo: true, videoEl: vpWidget.videoEl };
  }

  // Look for a LoadImage "image" widget or LoadVideo "video" widget
  const w = srcNode.widgets?.find((w) => w.name === "image" || w.name === "video");
  if (w?.value) {
    let subfolder = "", fname = w.value;
    const lastSlash = fname.lastIndexOf("/");
    if (lastSlash >= 0) { subfolder = fname.substring(0, lastSlash); fname = fname.substring(lastSlash + 1); }
    const isVideo = w.name === "video";
    const url = `/view?filename=${encodeURIComponent(fname)}&type=input&subfolder=${encodeURIComponent(subfolder)}`;
    return { url, isVideo };
  }

  // Fallback: check node.imgs (set after execution)
  if (srcNode.imgs?.length > 0 && srcNode.imgs[0].src) {
    return { url: srcNode.imgs[0].src, isVideo: false };
  }
  return null;
}

// ─── Source input watcher ───
// Watches a named IMAGE input for connection changes and source widget changes.
// Calls onChange(sources) when connections change or the source node's image/video widget changes.
// sources: array of { url, isVideo, videoEl } per connected IMAGE input matching inputName (or all if inputName is null).
// Returns a cleanup function.
export function watchImageInputs(node, inputName, onChange) {
  let watchedWidgets = [];

  function unwatchWidgets() {
    for (const { widget, origCb } of watchedWidgets) widget.callback = origCb;
    watchedWidgets = [];
  }

  function resolve() {
    if (!node.inputs) return [];
    const slots = inputName
      ? node.inputs.map((inp, i) => inp.name === inputName ? i : -1).filter(i => i >= 0)
      : node.inputs.map((inp, i) => inp.type === "IMAGE" ? i : -1).filter(i => i >= 0);
    return slots.map(i => resolveSourcePreview(node, i)).filter(s => s !== null);
  }

  function watch() {
    unwatchWidgets();
    if (!node.inputs || !node.graph) return;
    const slots = inputName
      ? node.inputs.map((inp, i) => inp.name === inputName ? i : -1).filter(i => i >= 0)
      : node.inputs.map((inp, i) => inp.type === "IMAGE" ? i : -1).filter(i => i >= 0);
    for (const slotIdx of slots) {
      const input = node.inputs[slotIdx];
      if (!input || input.link == null) continue;
      const link = node.graph.links?.get(input.link);
      if (!link) continue;
      const srcNode = node.graph.getNodeById(link.origin_id);
      if (!srcNode) continue;
      const w = srcNode.widgets?.find(w => w.name === "image" || w.name === "video");
      if (!w) continue;
      const origCb = w.callback;
      w.callback = function (...args) {
        if (origCb) origCb.apply(this, args);
        setTimeout(() => onChange(resolve()), 100);
      };
      watchedWidgets.push({ widget: w, origCb });
    }
  }

  chainCallback(node, "onConnectionsChange", function (type) {
    // Only react to input connection changes, not output
    if (type != null && type !== 1) return;
    setTimeout(() => {
      watch();
      onChange(resolve());
    }, 100);
  });

  chainCallback(node, "onRemoved", unwatchWidgets);

  return unwatchWidgets;
}

// ─── Video frame capture ───
// Draws the current frame of a video element to a fresh canvas at native resolution.
// If the video isn't decoded yet (readyState < 2), waits once for "loadeddata" before capturing.
// Calls callback(canvas) with the resulting canvas.
export function captureVideoFrame(videoEl, callback) {
  const capture = () => {
    if (!videoEl.videoWidth || !videoEl.videoHeight) return;
    const c = document.createElement("canvas");
    c.width = videoEl.videoWidth;
    c.height = videoEl.videoHeight;
    c.getContext("2d").drawImage(videoEl, 0, 0);
    callback(c);
  };
  if (videoEl.readyState >= 2) {
    capture();
  } else {
    const onReady = () => { videoEl.removeEventListener("loadeddata", onReady); capture(); };
    videoEl.addEventListener("loadeddata", onReady);
  }
}
