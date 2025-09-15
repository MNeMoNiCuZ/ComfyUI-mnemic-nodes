import os
import random
import folder_paths
import comfy.sd
import difflib
import hashlib

class LoadRandomCheckpoint:
    def __init__(self):
        self.cached_path = None
        self.cached_index = -1
        self.last_input_hash = ""
        self.shuffled_pool = []

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoints": ("STRING", {
                    "multiline": True,
                    "placeholder": "model_one or model_two.safetensors\nRelative paths (SDXL/Realistic/) based from checkpoints folder\nAbsolute paths (C:/path/to/model.safetensors)",
                    "tooltip": "Enter checkpoint names, file paths, or directory paths - one per line.\n\n• Names (model_one) are fuzzy-matched against checkpoint files\n• Relative paths (SDXL/Realistic/) based from checkpoints folder\n• Absolute paths (C:/path/to/model.safetensors)\n• Directory paths add all .ckpt/.safetensors files within them\n\n• Empty lines are ignored"
                }),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Controls checkpoint selection. Works with repeat_count:\n\n• repeat_count=1: Each seed gives different checkpoint\n• repeat_count=3: Seeds 0,1,2 → same checkpoint, seeds 3,4,5 → same different checkpoint\n\nSet 'Control After Generate' to 'Increment' for repeat_count to work."}),
                "repeat_count": ("INT", {"default": 1, "min": 1, "max": 1000, "tooltip": "Set 'Control After Generate' to 'Increment' for repeat_count to work.\n\nHow many consecutive seeds use the same checkpoint.\n\n• 1 = Each seed picks a different checkpoint\n• 3 = Seeds 0,1,2 all use checkpoint A, seeds 3,4,5 all use checkpoint B"}),
                "shuffle": ("BOOLEAN", {"default": False, "tooltip": "Selection mode:\n\n• False: Checkpoints will not repeat until all possible candidates has been used\n\n• True: Random selection from the pool. The same checkpoint could be used multiple times in a row"
                }),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "path")
    OUTPUT_TOOLTIPS = (
        "The loaded checkpoint model (MODEL)",
        "The CLIP model from the checkpoint (CLIP)",
        "The VAE model from the checkpoint (VAE)",
        "The full file path of the selected checkpoint file (STRING)",
    )

    FUNCTION = "load_checkpoint"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Load checkpoints from a flexible list with repeat control. Supports fuzzy name matching, file paths, and directories. Perfect for batch processing with varied model selection."


    def find_best_matches_custom(self, query, candidates):
        print(f"Finding best matches for '{query}'...")
        if not candidates:
            return []

        query_norm = query.lower()
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

        print("Top 10 matches:")
        for i in range(min(10, len(scores))):
            print(f"  - Score: {scores[i][1]:.2f}, File: {os.path.basename(scores[i][0])}")

        if not scores or scores[0][1] <= 0.3:
            return []

        top_score = scores[0][1]
        top_matches = [s[0] for s in scores if s[1] == top_score]

        return top_matches

    def load_checkpoint(self, checkpoints, seed, repeat_count, shuffle, limit_to_paths=""):
        HEADER = "\n\n--- 🎲 Load Random Checkpoint 🎲 ---"
        FOOTER = "--- 🎲 End Load Random Checkpoint 🎲 ---\n\n"
        
        print(HEADER)
        print(f"Received > Seed: {seed}, Repeat: {repeat_count}, Shuffle: {shuffle}")

        effective_index = seed // repeat_count
        print(f"Calculated > Effective Index: {effective_index} (Seed / Repeat)")
        print(f"Cached > Previous Index: {self.cached_index}")

        if self.cached_index == effective_index and self.cached_path:
            print("Status > CACHE HIT: Using cached path for this repeat run.")
            path = self.cached_path
        else:
            print("Status > CACHE MISS: Selecting a new checkpoint.")
            input_hash = hashlib.sha256(checkpoints.encode() + limit_to_paths.encode()).hexdigest()
            if self.last_input_hash != input_hash:
                print("Pool > Input changed, rebuilding checkpoint pool...")
                self.last_input_hash = input_hash
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
                        best_matches_relative = self.find_best_matches_custom(line, search_candidates)
                        for match in best_matches_relative:
                            final_pool.append(folder_paths.get_full_path("checkpoints", match))

                self.shuffled_pool = sorted(list(set(final_pool)))
                # Use effective_index=0 for initial pool shuffling to ensure consistency
                rng = random.Random(0)
                rng.shuffle(self.shuffled_pool)
                print(f"Pool > Rebuilt pool with {len(self.shuffled_pool)} unique items.")

            if not self.shuffled_pool:
                raise ValueError("Could not resolve any valid checkpoint files from the input list.")

            if shuffle:
                # Use effective_index for final selection to ensure repeats work
                rng = random.Random(effective_index)
                path = rng.choice(self.shuffled_pool)
            else:
                idx = effective_index % len(self.shuffled_pool)
                path = self.shuffled_pool[idx]

            self.cached_path = path
            self.cached_index = effective_index

        if not path:
            raise FileNotFoundError(f"Could not select a valid checkpoint file from the resolved pool.")

        print(f"\n>>> Chosen Model: {os.path.basename(path)} <<<")
        print(f"Loading checkpoint...")
        
        model, clip, vae, _ = comfy.sd.load_checkpoint_guess_config(
            path, 
            output_vae=True, 
            output_clip=True, 
            embedding_directory=folder_paths.get_folder_paths("embeddings")
        )
        
        print(FOOTER)
        return (model, clip, vae, path)

NODE_CLASS_MAPPINGS = {
    "LoadRandomCheckpoint": LoadRandomCheckpoint
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadRandomCheckpoint": "Load Random Checkpoint"
}