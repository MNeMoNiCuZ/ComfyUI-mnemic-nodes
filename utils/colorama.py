import threading

import colorama

_INIT_LOCK = threading.Lock()
_INIT_DONE = False


def ensure_colorama_initialized():
    """
    Initialize colorama once per process to avoid recursive stream wrapping.
    """
    global _INIT_DONE
    if _INIT_DONE:
        return
    with _INIT_LOCK:
        if _INIT_DONE:
            return
        colorama.init()
        _INIT_DONE = True
