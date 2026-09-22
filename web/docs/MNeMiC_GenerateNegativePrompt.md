# ⛔ Generate Negative Prompt

**Experimental.** Generates a negative prompt from a positive one, using a
small GPT-2 model fine-tuned on Civitai negative prompts.

The model is weak and largely random: treat the output as a starting point,
not a recommendation. NSFW terms can appear.

## Inputs

- **input_prompt** — The positive prompt to react to.
- **max_length** — Token cap on the generated text.
- **num_beams** — Beam search width. Higher is slower and more conservative.
- **temperature** — Randomness. Lower is more predictable.
- **top_k** — Consider only the K most likely next words. Lower is more
  predictable, higher is more varied.
- **top_p** — Nucleus sampling cutoff. Lower keeps output focused.
- **blocked_words** — One entry per line; each is removed from the result.
  Handy for stripping embeddings you do not have installed.

## Outputs

- **negative_prompt** — The generated text.

## Notes

The model files live in `nodes/negativeprompt/` and are loaded on every run, so
the first call after a fresh start is slow. The node is not an output node, so
it only runs when something downstream needs its result.
