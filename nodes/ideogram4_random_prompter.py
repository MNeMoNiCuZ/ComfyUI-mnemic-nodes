"""Ideogram 4 Random Prompter.

An experimental companion to the Ideogram 4 Prompt Builder. Instead of letting
you draw regions by hand, this node *invents* a whole composition from scratch:
it scatters a random number of regions across the canvas (background / large /
medium / small tiers, weighted) and fills each one with a description whose
words come straight from a real dictionary (the `wonderwords` library) — no
curated/hardcoded word lists anywhere. Style, lighting, medium, colour palette
and arrangement are randomised too.

It outputs the assembled Ideogram 4 JSON caption, a preview image of the
regions, the pixel-space bounding boxes, and the canvas width/height — matching
the Ideogram 4 Prompt Builder so the two can be swapped freely.

Requires the `wonderwords` package (listed in requirements.txt):
    pip install wonderwords
"""

import colorsys
import random

# Reuse the JSON/preview/bbox helpers from the visual builder so both nodes emit
# byte-identical caption formatting and previews.
from .ideogram4_prompt_builder import _render_preview, _norm_bbox, _palette, _dumps

# Real dictionary word source. Imported lazily-safe: if it's missing we raise a
# clear, actionable error at run time rather than breaking the whole node pack.
try:
    from wonderwords import RandomWord
    _RW = RandomWord()
except Exception:  # noqa: BLE001 - any failure means "library unavailable"
    _RW = None


# Per-run word-length window (set in generate()); None means "no length bias".
_WMIN = None
_WMAX = None


def _word(parts):
    """Return one random dictionary word for the given part(s) of speech.

    parts: list like ["nouns"], ["adjectives"], ["verbs"]. Honours the per-run
    length window (_WMIN/_WMAX) when set, widening to unconstrained if no word
    matches. Uses the global `random` state (seeded per run) so output is
    reproducible for a given seed.
    """
    for lo, hi in ((_WMIN, _WMAX), (None, None)):
        try:
            return _RW.word(include_parts_of_speech=parts, word_min_length=lo, word_max_length=hi)
        except Exception:  # noqa: BLE001 - e.g. NoWordsToChoseFrom for a tight window
            continue
    return _RW.word()


def _noun():
    return _word(["nouns"])


def _adj():
    return _word(["adjectives"])


def _verb():
    return _word(["verbs"])


# Medium is the one structural choice the Ideogram schema needs (it decides
# whether a `photo` or `art_style` key is emitted). These are the schema's own
# medium values, not flavour text.
MEDIUM_OPTIONS = ["photograph", "illustration", "3d_render", "painting", "graphic_design"]

# Colour generation modes, mirrored from the Colorful Starting Image node.
COLOR_PALETTE_OPTIONS = ["random_color", "muted", "grayscale", "binary", "neon", "pastel", "colorized"]
COLOR_HARMONY_OPTIONS = ["none", "complementary", "analogous", "triadic", "tetradic"]
POSITIONING_BIAS_OPTIONS = [
    "scattered", "center_weighted", "edge_weighted", "grid_aligned", "random_weighted",
    "north", "south", "east", "west",
    "north_west", "north_east", "south_west", "south_east",
]
ARRANGEMENT_OPTIONS = ["none", "spiral", "burst", "grid"]

# Spatial/relational binder words used ONLY when scene_framing is ON. These are
# structural connectors (not descriptive content) and do NOT count toward a
# region's content-word budget. In pure mode (scene_framing OFF) none of these
# appear and descriptions are bare dictionary words.
SCENE_CONNECTORS = ["beside", "near", "behind", "before", "above", "below",
                    "amid", "atop", "against", "beyond", "framing", "facing"]

# Size range (as a fraction of the canvas, per axis) for each region tier.
TIER_SIZES = {
    "background": (0.55, 1.0),
    "large": (0.34, 0.62),
    "medium": (0.17, 0.40),
    "small": (0.05, 0.17),
}
TIER_ORDER = ["background", "large", "medium", "small"]


def _rgb_to_hex(r, g, b):
    return "#%02X%02X%02X" % (int(round(r)), int(round(g)), int(round(b)))


def _harmonized_hues(rng, harmony):
    base = rng.random()
    if harmony == "complementary":
        return [base, (base + 0.5) % 1]
    if harmony == "analogous":
        return [base, (base + 0.083) % 1, (base - 0.083) % 1]
    if harmony == "triadic":
        return [base, (base + 0.333) % 1, (base - 0.333) % 1]
    if harmony == "tetradic":
        return [base, (base + 0.25) % 1, (base + 0.5) % 1, (base + 0.75) % 1]
    return []


def _one_color(rng, palette, hues, colorized_hue):
    # Returns an "#RRGGBB" string, honouring palette type and (optional) harmony hues.
    if hues:
        h = rng.choice(hues)
        if palette == "grayscale":
            l, s = rng.uniform(0.0, 1.0), rng.uniform(0.0, 0.15)
        elif palette == "binary":
            l, s = (0.05 if rng.random() > 0.5 else 0.95), rng.uniform(0.0, 0.1)
        else:
            l, s = rng.uniform(0.4, 0.7), rng.uniform(0.5, 1.0)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return _rgb_to_hex(r * 255, g * 255, b * 255)
    if palette == "muted":
        return _rgb_to_hex(rng.randint(50, 200), rng.randint(50, 200), rng.randint(50, 200))
    if palette == "grayscale":
        v = rng.randint(0, 255)
        return _rgb_to_hex(v, v, v)
    if palette == "binary":
        return "#000000" if rng.random() > 0.5 else "#FFFFFF"
    if palette == "neon":
        r, g, b = colorsys.hsv_to_rgb(rng.random(), 1.0, 0.9)
        return _rgb_to_hex(r * 255, g * 255, b * 255)
    if palette == "pastel":
        r, g, b = colorsys.hsv_to_rgb(rng.random(), 0.25, 1.0)
        return _rgb_to_hex(r * 255, g * 255, b * 255)
    if palette == "colorized":
        hue = colorized_hue if colorized_hue is not None else rng.random()
        r, g, b = colorsys.hls_to_rgb(hue, rng.uniform(0.2, 0.85), rng.uniform(0.5, 1.0))
        return _rgb_to_hex(r * 255, g * 255, b * 255)
    return _rgb_to_hex(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))


def _biased_center(rng, bias, idx, total, arrangement, aspect):
    # Returns a (cx, cy) center in 0-1 fractions for a region, honouring either
    # a structured arrangement (spiral/burst/grid) or a positioning bias.
    import math
    if arrangement == "spiral":
        ang = idx * (2 * math.pi * 2.5 / max(1, total))
        rad = 0.46 * (idx / max(1, total - 1)) if total > 1 else 0.0
        return (0.5 + rad * math.cos(ang), 0.5 + rad * math.sin(ang))
    if arrangement == "burst":
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(0.0, 0.46)
        return (0.5 + rad * math.cos(ang), 0.5 + rad * math.sin(ang))
    if arrangement == "grid":
        cols = max(1, int(round((total * aspect) ** 0.5)))
        rows = max(1, int((total + cols - 1) // cols))
        col, row = idx % cols, (idx // cols) % rows
        cx = (col + 0.5) / cols + rng.uniform(-0.5, 0.5) / cols * 0.6
        cy = (row + 0.5) / rows + rng.uniform(-0.5, 0.5) / rows * 0.6
        return (cx, cy)

    def g(mu, sigma):
        return rng.gauss(mu, sigma)

    if bias == "center_weighted":
        return (g(0.5, 0.16), g(0.5, 0.16))
    if bias == "edge_weighted":
        if rng.random() > 0.5:
            return (0.05 if rng.random() > 0.5 else 0.95, rng.random())
        return (rng.random(), 0.05 if rng.random() > 0.5 else 0.95)
    if bias == "grid_aligned":
        return (rng.randint(0, 7) / 7.0, rng.randint(0, 7) / 7.0)
    if bias == "random_weighted":
        ax, ay = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)
        return (g(ax, 0.12), g(ay, 0.12))
    if bias == "north":
        return (rng.random(), g(0.10, 0.07))
    if bias == "south":
        return (rng.random(), g(0.90, 0.07))
    if bias == "west":
        return (g(0.10, 0.07), rng.random())
    if bias == "east":
        return (g(0.90, 0.07), rng.random())
    if bias == "north_west":
        return (g(0.10, 0.07), g(0.10, 0.07))
    if bias == "north_east":
        return (g(0.90, 0.07), g(0.10, 0.07))
    if bias == "south_west":
        return (g(0.10, 0.07), g(0.90, 0.07))
    if bias == "south_east":
        return (g(0.90, 0.07), g(0.90, 0.07))
    return (rng.random(), rng.random())  # scattered


def _clamp01(v):
    return max(0.0, min(1.0, v))


def _article(word):
    # Algorithmic a/an (not hardcoded flavour) - used only in scene_framing mode.
    return "an" if word[:1].lower() in "aeiou" else "a"


class Ideogram4RandomPrompter:
    """
    Experimental random caption generator for Ideogram 4.

    Produces a full structured JSON caption. Every descriptive word is pulled
    live from the `wonderwords` dictionary (no curated/hardcoded vocabulary):
    a random count of regions, weighted across background / large / medium /
    small size tiers, each filled with a dictionary-built description, plus
    random style, lighting, medium, colour palette and arrangement. Outputs the
    same prompt / preview / bboxes / width / height as the Ideogram 4 Prompt
    Builder.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff,
                                 "tooltip": "Random seed for the whole generation.\n\n"
                                            "The same seed + the same settings always produce the exact same caption, "
                                            "preview and bounding boxes. Change the seed to roll a brand-new random "
                                            "composition without touching any other setting.\n\n"
                                            "Example: seed 0 and seed 1 give two completely different layouts; seed 0 "
                                            "run twice gives identical output."}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 16384, "step": 16,
                                  "tooltip": "Canvas width in pixels.\n\n"
                                             "Sets the output aspect ratio and the pixel grid the bounding boxes are "
                                             "measured against. Ideogram 4 prefers multiples of 16.\n\n"
                                             "Example: width 1344 with height 768 gives a wide 16:9-ish landscape; "
                                             "1024 x 1024 is a square."}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 16384, "step": 16,
                                   "tooltip": "Canvas height in pixels.\n\n"
                                              "Sets the output aspect ratio and the pixel grid the bounding boxes are "
                                              "measured against. Ideogram 4 prefers multiples of 16.\n\n"
                                              "Example: height 1344 with width 768 gives a tall portrait."}),
                "region_count_min": ("INT", {"default": 10, "min": 1, "max": 64,
                                             "tooltip": "Minimum number of element regions to generate.\n\n"
                                                        "The actual region count is a random integer between min and max "
                                                        "(inclusive). This is the EXACT number of elements that end up in "
                                                        "the caption and the preview (freeform / box-less regions are now "
                                                        "drawn dashed in the preview, so the visible count always matches).\n\n"
                                                        "Example: min 10, max 25 -> somewhere from 10 to 25 regions. "
                                                        "Set min = max for a fixed count (e.g. 12 and 12 = always 12)."}),
                "region_count_max": ("INT", {"default": 20, "min": 1, "max": 64,
                                             "tooltip": "Maximum number of element regions to generate.\n\n"
                                                        "The actual region count is a random integer between min and max "
                                                        "(inclusive).\n\n"
                                                        "Example: min 1, max 5 -> a sparse scene of 1 to 5 elements; "
                                                        "min 30, max 40 -> a dense, busy collage."}),
                "background_weight": ("FLOAT", {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                                                "tooltip": "Relative likelihood that any given region is a BACKGROUND-tier "
                                                           "block.\n\n"
                                                           "Background blocks are huge: each one covers at least 70% of the "
                                                           "canvas AREA (often the whole frame), acting as a base layer "
                                                           "behind everything else.\n\n"
                                                           "All four tier weights (background / large / medium / small) are "
                                                           "summed and each region picks a tier proportionally. Set all four "
                                                           "to 0 to fall back to equal weighting.\n\n"
                                                           "Example: weights 0.3 / 0 / 0 / 0.7 -> roughly 30% giant "
                                                           "backgrounds, 70% tiny details, nothing in between."}),
                "large_weight": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01,
                                           "tooltip": "Relative likelihood that a region is a LARGE-detail element "
                                                      "(~34-62% of the canvas per axis).\n\n"
                                                      "Weighted against the other three tiers. Set to 0 to forbid large "
                                                      "elements entirely.\n\n"
                                                      "Example: large 1.0 with everything else 0 -> every element is big."}),
                "medium_weight": ("FLOAT", {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                                            "tooltip": "Relative likelihood that a region is a MEDIUM-detail element "
                                                       "(~17-40% of the canvas per axis).\n\n"
                                                       "Weighted against the other three tiers. Set to 0 to forbid medium "
                                                       "elements.\n\n"
                                                       "Example: medium 1.0, all others 0 -> a uniform field of mid-size "
                                                       "shapes."}),
                "small_weight": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01,
                                           "tooltip": "Relative likelihood that a region is a SMALL-detail element "
                                                      "(~5-17% of the canvas per axis).\n\n"
                                                      "Weighted against the other three tiers. Set to 0 to forbid small "
                                                      "elements.\n\n"
                                                      "Example: small 1.0, all others 0 -> only tiny scattered details "
                                                      "(a confetti / texture look)."}),
                "word_length_bias": ("INT", {"default": 0, "min": 0, "max": 18,
                                             "tooltip": "Preferred dictionary word length, in characters.\n\n"
                                                        "0 = no preference (a natural mix of short and long words). Any "
                                                        "value above 0 biases every picked word toward that length.\n\n"
                                                        "Example: 4 favours short punchy words (e.g. 'wide', 'calm'); "
                                                        "11 favours long ornate words (e.g. 'melancholic')."}),
                "word_length_randomness": ("INT", {"default": 2, "min": 0, "max": 18,
                                                   "tooltip": "Spread (in characters) around 'word_length_bias'.\n\n"
                                                              "Words are drawn from the window [bias - this, bias + this]. "
                                                              "Larger = looser mix; 0 = words of exactly the bias length. "
                                                              "Ignored when word_length_bias is 0.\n\n"
                                                              "Example: bias 8, randomness 2 -> words 6-10 characters long."}),
                "scene_framing": ("BOOLEAN", {"default": True, "label_on": "scene", "label_off": "pure",
                                              "tooltip": "OFF (pure): each region's description is a bare list of "
                                                         "dictionary words, e.g. 'vivid tower, hollow stone.' Maximum "
                                                         "randomness, but Ideogram tends to render this as a COLLAGE / "
                                                         "asset sheet of separate items.\n\n"
                                                         "ON (scene): the same dictionary words are woven together with "
                                                         "articles and spatial connector words (beside / near / behind / "
                                                         "against ...) into one continuous sentence, e.g. 'a vivid tower "
                                                         "beside a hollow stone against an amber cloud.' This tells "
                                                         "Ideogram it is ONE coherent scene, so 'photograph' actually "
                                                         "looks like a photograph instead of a grid. The connector / "
                                                         "article words are structural and do NOT count toward "
                                                         "region_word_min/max.\n\n"
                                                         "Tip: for a real photo use scene ON + medium 'photograph' + a "
                                                         "low region count + large boxes (high background/large weight)."}),
                "region_word_min": ("INT", {"default": 5, "min": 1, "max": 200,
                                            "tooltip": "Minimum number of randomized CONTENT words (adjectives + nouns "
                                                       "from the dictionary) in each region's description.\n\n"
                                                       "The exact count per region is a random integer between "
                                                       "region_word_min and region_word_max (inclusive). Binder words "
                                                       "(articles / connectors added by scene_framing) are NOT counted.\n\n"
                                                       "Set min = max for an exact count: e.g. min 20, max 20 -> every "
                                                       "region has exactly 20 content words."}),
                "region_word_max": ("INT", {"default": 15, "min": 1, "max": 200,
                                            "tooltip": "Maximum number of randomized CONTENT words in each region's "
                                                       "description.\n\n"
                                                       "The exact count per region is a random integer between "
                                                       "region_word_min and region_word_max (inclusive). Binder words "
                                                       "are NOT counted.\n\n"
                                                       "Example: min 5, max 20 -> each region gets 5-20 content words; "
                                                       "min 20, max 20 -> exactly 20 every time."}),
                "freeform_chance": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                                              "tooltip": "Per-region chance that a region drops its hard bounding box and "
                                                         "becomes a FREEFORM element.\n\n"
                                                         "Ideogram has no edge-blur control. An element WITHOUT a bbox is "
                                                         "blended softly into the scene instead of being pinned to a hard "
                                                         "rectangle, so higher values give a less 'cut-out collage' look. "
                                                         "Freeform regions are still counted and are drawn dashed in the "
                                                         "preview, but they are excluded from the bbox output (they have no "
                                                         "fixed location).\n\n"
                                                         "Example: 0.0 -> every element keeps a hard box; 1.0 -> nothing is "
                                                         "boxed (fully painterly, empty bbox output)."}),
                "text_region_min": ("INT", {"default": 0, "min": 0, "max": 64,
                                            "tooltip": "Minimum number of regions rendered as in-image TEXT (a real "
                                                       "dictionary word drawn into the picture) instead of an object.\n\n"
                                                       "The text count is a random integer between text_region_min and "
                                                       "text_region_max (inclusive), then clamped so it never exceeds the "
                                                       "total region count. This is an EXACT count, not a probability.\n\n"
                                                       "Example: min 1, max 2 -> always 1 or 2 text words in the image, "
                                                       "no matter how many total regions there are."}),
                "text_region_max": ("INT", {"default": 2, "min": 0, "max": 64,
                                            "tooltip": "Maximum number of regions rendered as in-image TEXT.\n\n"
                                                       "The text count is a random integer between text_region_min and "
                                                       "text_region_max (inclusive), clamped to the total region count.\n\n"
                                                       "Example: min 0, max 0 -> never any text; min 3, max 3 -> always "
                                                       "exactly 3 text words."}),
                "element_palette_chance": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                                                     "tooltip": "Per-region chance that a region carries its OWN small "
                                                                "colour palette (a subset of the image-level palette) "
                                                                "instead of inheriting the global one.\n\n"
                                                                "Has no effect when color_palette is 'none'.\n\n"
                                                                "Example: 0.0 -> all elements share the image palette; "
                                                                "1.0 -> every element gets its own colour sub-set."}),
                "medium": (["random"] + MEDIUM_OPTIONS, {"default": "photograph",
                                                         "tooltip": "Image medium (an Ideogram 4 schema value).\n\n"
                                                                    "'photograph' emits a 'photo' style key (focal length / "
                                                                    "aperture); every other medium emits an 'art_style' "
                                                                    "key instead. 'random' picks one per run.\n\n"
                                                                    "Example: 'photograph' -> camera-style caption; "
                                                                    "'painting' -> art-style caption."}),
                "color_palette": (["random", "none"] + COLOR_PALETTE_OPTIONS,
                                  {"default": "none",
                                   "tooltip": "Colour palette family used to build the image palette (mirrors the "
                                              "Colorful Starting Image node).\n\n"
                                              "- none: emit NO colour palette at all (Ideogram chooses colours freely)\n"
                                              "- random_color: any RGB\n"
                                              "- muted / grayscale / binary / neon / pastel: themed colours\n"
                                              "- colorized: grayscale tinted with one shared hue\n"
                                              "- random: pick one of the families above per run\n\n"
                                              "Example: 'none' -> no color_palette keys anywhere; 'neon' -> vivid "
                                              "saturated swatches."}),
                "color_harmony": (["random"] + COLOR_HARMONY_OPTIONS,
                                  {"default": "none",
                                   "tooltip": "Colour-harmony rule applied to the generated palette.\n\n"
                                              "- none: unrelated colours\n"
                                              "- complementary: two opposite hues\n"
                                              "- analogous: neighbouring hues\n"
                                              "- triadic: three evenly spaced hues\n"
                                              "- tetradic: four evenly spaced hues\n"
                                              "- random: pick one per run\n\n"
                                              "Ignored when color_palette is 'none'.\n\n"
                                              "Example: 'complementary' -> a punchy two-colour contrast scheme."}),
                "positioning_bias": (["random"] + POSITIONING_BIAS_OPTIONS,
                                     {"tooltip": "Where regions tend to cluster on the canvas (mirrors the Colorful "
                                                 "Starting Image node).\n\n"
                                                 "scattered = anywhere; center_weighted / edge_weighted; grid_aligned; "
                                                 "random_weighted; or a compass direction (north / south / east / west "
                                                 "and the diagonals). Ignored when 'arrangement' is anything other than "
                                                 "'none'.\n\n"
                                                 "Example: 'south' -> elements gather along the bottom; 'center_weighted' "
                                                 "-> a tight central cluster."}),
                "arrangement": (["random"] + ARRANGEMENT_OPTIONS,
                                {"default": "none",
                                 "tooltip": "Structured placement pattern for region centres.\n\n"
                                            "- none: use positioning_bias instead (default)\n"
                                            "- spiral: centres wind outward in a spiral\n"
                                            "- burst: centres explode out from the middle\n"
                                            "- grid: centres snap to a tidy grid\n"
                                            "- random: pick one per run\n\n"
                                            "Overrides positioning_bias whenever it is not 'none'.\n\n"
                                            "Example: 'grid' -> an orderly tiled layout; 'burst' -> an energetic "
                                            "radial spray."}),
            },
            "optional": {
                "description_length": ("INT", {"default": 35, "min": 1, "max": 200,
                                               "tooltip": "Target length (in words) for the AUTO-GENERATED high_level_description.\n\n"
                                                          "The generator keeps adding dictionary word-groups until it reaches "
                                                          "about this many words, so larger = a longer, richer overview line. "
                                                          "Ignored when description_override is set.\n\n"
                                                          "Example: 6 -> a short caption; 30 -> a long, dense descriptive run."}),
                "description_override": ("STRING", {"multiline": True, "default": "",
                                                    "tooltip": "FULL REPLACEMENT for the high_level_description.\n\n"
                                                               "When this is non-empty, the high_level_description is set to "
                                                               "EXACTLY this string and nothing is generated for it (description_prefix "
                                                               "and description_length are ignored). Leave blank to auto-generate.\n\n"
                                                               "Example: 'A wide cinematic establishing shot of a coastal town "
                                                               "at dawn' -> that exact line is used verbatim."}),
                "description_prefix": ("STRING", {"multiline": True, "default": "A close-up photography of",
                                                  "tooltip": "PREFIX prepended to the auto-generated high_level_description.\n\n"
                                                             "Ignored when description_override is set. The final value is "
                                                             "'<prefix> <generated words>'.\n\n"
                                                             "Example: prefix 'A vintage 35mm photograph of' -> "
                                                             "'A vintage 35mm photograph of amber hollow river, brisk stone, ...'"}),
                "description_background_prefix": ("STRING", {"multiline": True, "default": "an environment photography background of",
                                                             "tooltip": "PREFIX prepended to the auto-generated background description.\n\n"
                                                                        "The final value is '<prefix> <generated words>'. Leave blank "
                                                                        "to let the background be fully random.\n\n"
                                                                        "Example: 'a serene mountain landscape with' -> "
                                                                        "'a serene mountain landscape with vivid hollow stone ...'"}),
            },
        }

    RETURN_TYPES = ("STRING", "IMAGE", "BOUNDING_BOX", "INT", "INT")
    RETURN_NAMES = ("prompt", "preview", "bboxes", "width", "height")
    FUNCTION = "generate"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = ("Experimental random prompt generator for Ideogram 4's structured JSON caption format. "
                   "Every word is pulled live from the wonderwords dictionary (nothing hardcoded). "
                   "Scatters weighted background/large/medium/small regions and randomises style, lighting, "
                   "medium, colour palette and arrangement. Outputs prompt / preview / bboxes / width / height. "
                   "Requires the 'wonderwords' package.")

    # ---- dictionary-driven text fragments ----
    # CONTRACT: every CONTENT word comes from the wonderwords dictionary and is
    # the only thing counted toward a region's word budget. No hardcoded
    # descriptive flavour ("blurred", "light", "shadows", "style", "focus").
    # The ONLY non-dictionary tokens are punctuation, numeric camera parameters,
    # and - exclusively when scene_framing is ON - structural binder words
    # (articles a/an + spatial connectors) which are NOT counted as content.

    def _phrases(self, rng, n):
        # Split an EXACT content-word budget n into noun-phrases. Each phrase is
        # (k-1) adjectives + 1 noun and consumes exactly k content words, so the
        # phrases together always total exactly n content words.
        phrases, remaining = [], max(1, n)
        while remaining > 0:
            k = rng.randint(1, min(3, remaining))
            phrases.append(([_adj() for _ in range(k - 1)], _noun()))
            remaining -= k
        return phrases

    def _desc(self, rng, n, scene):
        # Render exactly n dictionary content words as a description.
        #   scene=False -> bare comma-separated words (pure mode, no binders).
        #   scene=True  -> phrases joined with article + spatial connectors so it
        #                  reads as one continuous scene (binders are NOT counted).
        phrases = self._phrases(rng, n)
        if not scene:
            return ", ".join(" ".join(adjs + [noun]) for adjs, noun in phrases) + "."
        chunks = []
        for idx, (adjs, noun) in enumerate(phrases):
            np = " ".join([_article(adjs[0] if adjs else noun)] + adjs + [noun])
            chunks.append(np if idx == 0 else "%s %s" % (rng.choice(SCENE_CONNECTORS), np))
        return " ".join(chunks) + "."

    def _high_level(self, rng, n, scene):
        return self._desc(rng, n, scene)

    def _element_desc(self, rng, n, scene):
        return self._desc(rng, n, scene)

    def _background_desc(self, rng, n, scene):
        return self._desc(rng, n, scene)

    def _aesthetics(self):
        return "%s, %s, %s" % (_adj(), _adj(), _adj())

    def _lighting(self):
        return "%s, %s %s" % (_adj(), _adj(), _noun())

    def _photo(self, rng):
        # Numeric camera parameters only (focal length / aperture); no English words.
        return "%dmm, f/%.1f" % (rng.randint(14, 200), rng.uniform(1.4, 16.0))

    def _art_style(self):
        return "%s %s, %s" % (_adj(), _noun(), _adj())

    def generate(self, seed, width, height, region_count_min, region_count_max,
                 background_weight, large_weight, medium_weight, small_weight,
                 word_length_bias, word_length_randomness,
                 scene_framing, region_word_min, region_word_max,
                 freeform_chance, text_region_min, text_region_max, element_palette_chance,
                 medium, color_palette, color_harmony, positioning_bias, arrangement,
                 description_length=35, description_override="", description_prefix="A close-up photography of",
                 description_background_prefix="an environment photography background of"):
        if _RW is None:
            raise RuntimeError(
                "Ideogram 4 Random Prompter requires the 'wonderwords' package. "
                "Install it into your ComfyUI Python environment with:  pip install wonderwords")

        # Seed the global random state so BOTH our maths and wonderwords' picks
        # are reproducible for a given seed.
        random.seed(seed)
        rng = random

        # Configure the per-run dictionary word-length window (0 = no preference).
        global _WMIN, _WMAX
        if word_length_bias > 0:
            _WMIN = max(2, word_length_bias - word_length_randomness)
            _WMAX = word_length_bias + word_length_randomness
        else:
            _WMIN = _WMAX = None

        # Resolve the "random" dropdown choices.
        if medium == "random":
            medium = rng.choice(MEDIUM_OPTIONS)
        if color_palette == "random":
            color_palette = rng.choice(COLOR_PALETTE_OPTIONS)
        if color_harmony == "random":
            color_harmony = rng.choice(COLOR_HARMONY_OPTIONS)
        if positioning_bias == "random":
            positioning_bias = rng.choice(POSITIONING_BIAS_OPTIONS)
        if arrangement == "random":
            arrangement = rng.choice(ARRANGEMENT_OPTIONS)

        # Build the image-level colour palette ('none' = no palette at all).
        if color_palette == "none":
            image_palette = []
        else:
            hues = _harmonized_hues(rng, color_harmony) if color_harmony != "none" else []
            colorized_hue = rng.random() if color_palette == "colorized" else None
            palette_len = rng.randint(3, 6)
            raw_palette = [_one_color(rng, color_palette, hues, colorized_hue) for _ in range(palette_len)]
            seen = set()
            image_palette = [c for c in raw_palette if not (c in seen or seen.add(c))]

        # How many regions, and which tier each one belongs to.
        lo, hi = sorted((max(1, region_count_min), max(1, region_count_max)))
        count = rng.randint(lo, hi)
        weights = [background_weight, large_weight, medium_weight, small_weight]
        if sum(weights) <= 0:
            weights = [1.0, 1.0, 1.0, 1.0]
        aspect = (width / height) if height else 1.0

        # Pick the EXACT number of text regions up front (a count, not a per-region
        # dice roll), then choose which region indices they land on.
        tlo, thi = sorted((max(0, text_region_min), max(0, text_region_max)))
        text_count = min(count, rng.randint(tlo, thi))
        text_idx = set(rng.sample(range(count), text_count)) if text_count else set()

        # Per-region content-word budget window (binder words are not counted).
        rwlo, rwhi = sorted((max(1, region_word_min), max(1, region_word_max)))

        boxes = []
        for i in range(count):
            tier = rng.choices(TIER_ORDER, weights=weights, k=1)[0]
            if tier == "background":
                # Each background block covers >= 70% of the canvas AREA.
                cov = rng.uniform(0.70, 1.0)
                w = rng.uniform(cov ** 0.5, 1.0)
                h = min(1.0, cov / w)
            else:
                smin, smax = TIER_SIZES[tier]
                w = rng.uniform(smin, smax)
                h = rng.uniform(smin, smax)
            cx, cy = _biased_center(rng, positioning_bias, i, count, arrangement, aspect)
            x = _clamp01(cx - w / 2.0)
            y = _clamp01(cy - h / 2.0)
            x = min(x, max(0.0, 1.0 - w))
            y = min(y, max(0.0, 1.0 - h))

            n_words = rng.randint(rwlo, rwhi)               # exact content words this region
            box = {"x": x, "y": y, "w": w, "h": h}
            if i in text_idx:
                box["type"] = "text"
                box["text"] = _noun().upper()
                box["desc"] = self._element_desc(rng, n_words, scene_framing)
            else:
                box["type"] = "obj"
                box["desc"] = self._element_desc(rng, n_words, scene_framing)
            if image_palette and rng.random() < element_palette_chance:
                k = rng.randint(1, min(5, len(image_palette)))
                box["palette"] = rng.sample(image_palette, k)
            # Drop the bbox on some regions so they blend into the scene instead
            # of rendering as a hard, cut-out rectangle.
            if rng.random() < freeform_chance:
                box["nobbox"] = True
            boxes.append(box)

        # Assemble the caption (key order matters for the Ideogram verifier).
        generated_bg = self._background_desc(rng, rng.randint(rwlo, rwhi), scene_framing)
        background = ("%s %s" % (description_background_prefix.strip(), generated_bg)).strip() \
            if description_background_prefix.strip() else generated_bg
        # high_level_description: full override > prefix + generated > generated.
        if description_override.strip():
            high_level_description = description_override.strip()
        else:
            generated = self._high_level(rng, description_length, scene_framing)
            high_level_description = ("%s %s" % (description_prefix.strip(), generated)).strip() \
                if description_prefix.strip() else generated

        caption = {"high_level_description": high_level_description}

        sd = {"aesthetics": self._aesthetics(), "lighting": self._lighting()}
        if medium == "photograph":
            sd["photo"] = self._photo(rng)
            sd["medium"] = medium
        else:
            sd["medium"] = medium
            sd["art_style"] = self._art_style()
        if image_palette:
            sd["color_palette"] = image_palette
        caption["style_description"] = sd

        elements = []
        for box in boxes:
            etype = box["type"]
            elem = {"type": etype}                          # key order matters
            if not box.get("nobbox"):                       # freeform elements omit bbox
                elem["bbox"] = _norm_bbox(box)
            if etype == "text":
                elem["text"] = box.get("text", "")
            elem["desc"] = box.get("desc", "")
            pal = _palette(box.get("palette", []))
            if pal:
                elem["color_palette"] = pal[:5]
            elements.append(elem)

        caption["compositional_deconstruction"] = {
            "background": background,
            "elements": elements,
        }

        # draw_freeform=True so box-less regions still show (dashed) and the visible
        # count matches the generated region count.
        preview = _render_preview(boxes, width, height, None, 25, draw_freeform=True)

        # Pixel-space bboxes ({x, y, width, height}) for SAM3 / BoundingBox consumers,
        # nested per-frame (list[list[dict]]) like the Prompt Builder emits. Freeform
        # (nobbox) regions are excluded since they have no fixed location.
        bbox_dicts = [{"x": round(b["x"] * width), "y": round(b["y"] * height),
                       "width": round(b["w"] * width), "height": round(b["h"] * height)}
                      for b in boxes if not b.get("nobbox")]
        bboxes_out = [bbox_dicts] if bbox_dicts else []

        return (_dumps(caption), preview, bboxes_out, width, height)


NODE_CLASS_MAPPINGS = {
    "Ideogram4RandomPrompter": Ideogram4RandomPrompter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Ideogram4RandomPrompter": "🎲 Ideogram 4 Random Prompter",
}
