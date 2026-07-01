"""
Tiny runtime bridge so the Batch Wildcard Sampler can hand its per-image resolved
prompts to the Save Image With Metadata node.

The Batch Wildcard Sampler resolves a different prompt for every image in the
batch and samples internally (no KSampler / CLIPTextEncode nodes in the graph),
so the metadata saver's normal graph-walking cannot discover the prompts. This
module stores the most recent batch so the saver can pick it up by index.

Only the most recent batch is kept. The saver guards usage by confirming a
BatchWildcardSampler node is actually present in the current prompt graph and
that the recorded prompt count matches the image count, so a stale record can
never leak into an unrelated workflow.
"""

import threading

_lock = threading.Lock()
_last = {"positive": [], "negative": [], "seed": None}


def set_batch_prompts(positive_list, negative_list, seed=None):
    with _lock:
        _last["positive"] = list(positive_list)
        _last["negative"] = list(negative_list)
        _last["seed"] = seed


def get_batch_prompts():
    with _lock:
        return {
            "positive": list(_last["positive"]),
            "negative": list(_last["negative"]),
            "seed": _last["seed"],
        }
