import os
import random
import folder_paths
import comfy.sd
import difflib
import hashlib
import colorama

from comfy_api.latest import io

from ..utils.settings_utils import is_load_random_checkpoint_console_log_enabled

POOL_CACHE = {}

# Per-node instance state in V1; module level here because V3 nodes execute as
# classmethods on a per-run class clone.
_CACHED_PATH = None
_CACHED_INDEX = -1
_SHUFFLED_POOL = []

class LoadRandomCheckpoint(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MNeMiC_LoadRandomCheckpoint",
            display_name="🎲 Load Random Checkpoint",
            category="⚡ MNeMiC Nodes",
            description="Load checkpoints from a flexible list with repeat control. Supports fuzzy name matching, file paths, and directories. Perfect for batch processing with varied model selection.",
            inputs=[
                io.String.Input(
                    "checkpoints",
                    multiline=True,
                    placeholder="model_one or model_two.safetensors\nRelative paths (SDXL/Realistic/) based from checkpoints folder\nAbsolute paths (C:/path/to/model.safetensors)",
                    tooltip="Enter checkpoint names, file paths, or directory paths - one per line.\n\n• Names (model_one) are fuzzy-matched against checkpoint files\n• Relative paths (SDXL/Realistic/) based from checkpoints folder\n• Absolute paths (C:/path/to/model.safetensors)\n• Directory paths add all .ckpt/.safetensors files within them\n\n• Empty lines are ignored",
                ),
                io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, tooltip="Controls checkpoint selection. Works with repeat_count:\n\n• repeat_count=1: Each seed gives different checkpoint\n• repeat_count=3: Seeds 0,1,2 → same checkpoint, seeds 3,4,5 → same different checkpoint\n\nSet 'Control After Generate' to 'Increment' for repeat_count to work."),
                io.Int.Input("repeat_count", default=1, min=1, max=1000, tooltip="Set 'Control After Generate' to 'Increment' for repeat_count to work.\n\nHow many consecutive seeds use the same checkpoint.\n\n• 1 = Each seed picks a different checkpoint\n• 3 = Seeds 0,1,2 all use checkpoint A, seeds 3,4,5 all use checkpoint B"),
                io.Boolean.Input("shuffle", default=False, tooltip="Selection mode:\n\n• False: Checkpoints will not repeat until all possible candidates has been used\n\n• True: Random selection from the pool. The same checkpoint could be used multiple times in a row"),
            ],
            outputs=[
                io.Model.Output(display_name="model", tooltip="The loaded checkpoint model (MODEL)"),
                io.Clip.Output(display_name="clip", tooltip="The CLIP model from the checkpoint (CLIP)"),
                io.Vae.Output(display_name="vae", tooltip="The VAE model from the checkpoint (VAE)"),
                io.String.Output(display_name="path", tooltip="The full file path of the selected checkpoint file (STRING)"),
            ],
        )


    @classmethod
    def find_best_matches_custom(cls, query, candidates, console_log=False):
        if console_log:
            print(f"Finding best matches for '{query}'...")
        if not candidates:
            return []

        query_norm = query.lower()
        contains_matches = []
        for candidate in candidates:
            candidate_lower = os.path.basename(candidate).lower()
            if query_norm in candidate_lower:
                contains_matches.append(candidate)

        if contains_matches:
            if console_log:
                print(f"Found {len(contains_matches)} substring matches:")
                for match in contains_matches:
                    print(f"  - {os.path.basename(match)}")
            return contains_matches

        # If no substring matches, fall back to fuzzy matching
        scores = []
        for candidate in candidates:
            candidate_filename = os.path.basename(candidate)
            candidate_norm, _ = os.path.splitext(candidate_filename)
            candidate_norm = candidate_norm.lower()

            ratio = difflib.SequenceMatcher(None, query_norm, candidate_norm).ratio()

            if query_norm == candidate_norm:
                ratio = 1.0
            elif query_norm in candidate_norm:
                ratio += 0.1

            scores.append((candidate, ratio))

        scores.sort(key=lambda x: x[1], reverse=True)

        if console_log:
            print("Top 10 matches:")
            for i in range(min(10, len(scores))):
                print(f"  - Score: {scores[i][1]:.2f}, File: {os.path.basename(scores[i][0])}")

        if not scores or scores[0][1] <= 0.3:
            return []

        top_score = scores[0][1]
        top_matches = [s[0] for s in scores if s[1] == top_score]

        return top_matches

    @classmethod
    def execute(cls, checkpoints, seed, repeat_count, shuffle, limit_to_paths="") -> io.NodeOutput:
        global _CACHED_PATH, _CACHED_INDEX, _SHUFFLED_POOL
        console_log = is_load_random_checkpoint_console_log_enabled()
        HEADER = "\n\n--- 🎲 Load Random Checkpoint 🎲 ---"
        FOOTER = "--- 🎲 End Load Random Checkpoint 🎲 ---\n\n"

        if console_log:
            print(HEADER)
            print(f"Received > Seed: {seed}, Repeat: {repeat_count}, Shuffle: {shuffle}")

        effective_index = seed // repeat_count
        if console_log:
            print(f"Calculated > Effective Index: {effective_index} (Seed / Repeat)")
            print(f"Cached > Previous Index: {_CACHED_INDEX}")

        if _CACHED_INDEX == effective_index and _CACHED_PATH:
            if console_log:
                print("Status > CACHE HIT: Using cached path for this repeat run.")
            path = _CACHED_PATH
        else:
            if console_log:
                print("Status > CACHE MISS: Selecting a new checkpoint.")
            input_hash = hashlib.sha256(checkpoints.encode() + limit_to_paths.encode()).hexdigest()
            if input_hash not in POOL_CACHE:
                if console_log:
                    print("Pool > Input changed, rebuilding checkpoint pool...")
                final_pool = []
                ckpt_base_dirs = folder_paths.get_folder_paths("checkpoints")
                all_checkpoints_relative = folder_paths.get_filename_list("checkpoints")

                search_candidates = all_checkpoints_relative
                user_paths = [p.strip().replace('\\', '/') for p in limit_to_paths.splitlines() if p.strip()]
                if user_paths:
                    filtered_candidates = [c for c in all_checkpoints_relative if any(c.replace('\\', '/').startswith(p) for p in user_paths)]
                    if filtered_candidates:
                        search_candidates = filtered_candidates
                    else:
                        print(f"Warning: No checkpoints found in specified paths. Searching all checkpoints instead.")

                for line in checkpoints.splitlines():
                    line = line.strip()
                    if not line: continue

                    path_to_check = os.path.abspath(os.path.join(ckpt_base_dirs[0], line)) if not os.path.isabs(line) else line

                    if os.path.isdir(path_to_check):
                        for root, _, files in os.walk(path_to_check, followlinks=True):
                            for file in files:
                                if file.endswith(('.ckpt', '.safetensors')):
                                    final_pool.append(os.path.join(root, file))
                    elif os.path.isabs(line) and os.path.exists(line):
                        final_pool.append(line)
                    else:
                        best_matches_relative = cls.find_best_matches_custom(line, search_candidates, console_log=console_log)
                        for match in best_matches_relative:
                            final_pool.append(folder_paths.get_full_path("checkpoints", match))

                _SHUFFLED_POOL = sorted(list(set(final_pool)))
                # Use effective_index=0 for initial pool shuffling to ensure consistency
                rng = random.Random(0)
                rng.shuffle(_SHUFFLED_POOL)
                POOL_CACHE[input_hash] = _SHUFFLED_POOL
                if console_log:
                    print(f"Pool > Rebuilt pool with {len(_SHUFFLED_POOL)} unique items.")
            else:
                _SHUFFLED_POOL = POOL_CACHE[input_hash]
                if console_log:
                    print(f"Pool > Using cached pool with {len(_SHUFFLED_POOL)} items.")

            # Print the final pool with status
            if console_log:
                if shuffle:
                    print("Final pool (shuffled, all active):")
                    for item in _SHUFFLED_POOL:
                        print(colorama.Fore.YELLOW + f"  - {os.path.basename(item)}" + colorama.Style.RESET_ALL)
                else:
                    idx = effective_index % len(_SHUFFLED_POOL) if _SHUFFLED_POOL else 0
                    print("Final pool (ordered, cycling):")
                    for i, item in enumerate(_SHUFFLED_POOL):
                        if i < idx:
                            print(colorama.Fore.LIGHTBLACK_EX + f"  - {os.path.basename(item)} (used)" + colorama.Style.RESET_ALL)
                        else:
                            print(colorama.Fore.YELLOW + f"  - {os.path.basename(item)} (pending)" + colorama.Style.RESET_ALL)

            if not _SHUFFLED_POOL:
                raise ValueError("Could not resolve any valid checkpoint files from the input list.")

            if shuffle:
                # Use effective_index for final selection to ensure repeats work
                rng = random.Random(effective_index)
                path = rng.choice(_SHUFFLED_POOL)
            else:
                idx = effective_index % len(_SHUFFLED_POOL)
                path = _SHUFFLED_POOL[idx]

            _CACHED_PATH = path
            _CACHED_INDEX = effective_index

        if not path:
            raise FileNotFoundError(f"Could not select a valid checkpoint file from the resolved pool.")

        print(f"\n>>> Chosen Model: {os.path.basename(path)} <<<")
        if console_log:
            print(f"Loading checkpoint...")

        model, clip, vae, _ = comfy.sd.load_checkpoint_guess_config(
            path,
            output_vae=True,
            output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings")
        )

        if console_log:
            print(FOOTER)
        return io.NodeOutput(model, clip, vae, path)

