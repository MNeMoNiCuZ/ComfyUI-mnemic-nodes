import os

# slot -> ((path, size, mtime), loaded result). One model per slot, so a node keeps
# the model it used last and releases it when it switches to another file.
_LOADED = {}


def load_cached(slot, path, load):
    """Return load(path), reusing the previous result for this slot while the file is unchanged."""
    stat = os.stat(path)
    key = (path, stat.st_size, stat.st_mtime_ns)
    cached = _LOADED.get(slot)
    if cached is None or cached[0] != key:
        # Release the old model before loading the next one.
        _LOADED.pop(slot, None)
        cached = _LOADED[slot] = (key, load(path))
    return cached[1]
