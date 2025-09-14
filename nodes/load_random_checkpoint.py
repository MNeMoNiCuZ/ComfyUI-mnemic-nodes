import os
import random
import folder_paths
import comfy.sd
import difflib

class LoadRandomCheckpoint:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoints": ("STRING", {
                    "multiline": True,
                    "placeholder": "model_name\nmodel_name.safetensors\n..\\loras\\character\\\nC:\\path\\to\\specific\\model.ckpt",
                    "tooltip": "A list of checkpoint names, paths, or directories, one per line.\n\n- Names are fuzzy matched against files in your checkpoints folder.\n- Absolute paths to files are used directly.\n- Directory paths will add all checkpoints within them to the selection pool."
                }),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed controls the selection. Set 'Control After Generate' to 'Increment' to iterate."}),
                "repeat_count": ("INT", {"default": 1, "min": 1, "max": 1000, "tooltip": "Number of times to use the same checkpoint before selecting the next one."}),
                "shuffle": ("BOOLEAN", {"default": True, "tooltip": "Controls the selection order.\n\n- True (Shuffle): Randomly selects a checkpoint from the list on each new selection.\n- False (Sequential): Iterates through the checkpoints in the order they appear in the list."}),
            },
            "optional": {
                "limit_to_paths": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Limit search to specific sub-folders, one per line.\n(Paths must be relative to your checkpoints folder)",
                    "tooltip": "Filter the search to specific folders, one per line.\nPaths MUST be relative to your main ComfyUI checkpoints directory."
                }),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("model", "clip", "vae")
    FUNCTION = "load_checkpoint"
    CATEGORY = "⚡ MNeMiC Nodes"
    DESCRIPTION = "Randomly or sequentially loads a checkpoint from a list, outputting the Model, CLIP, and VAE."

    def find_best_match_custom(self, query, candidates):
        print(f"LoadRandomCheckpoint: Finding best match for '{query}'...")
        
        if not candidates:
            return None

        # Normalize query
        query_norm = query.lower()

        scores = []
        for candidate in candidates:
            # Normalize candidate filename
            candidate_filename = os.path.basename(candidate)
            candidate_norm, _ = os.path.splitext(candidate_filename)
            candidate_norm = candidate_norm.lower()
            
            # Calculate similarity score
            ratio = difflib.SequenceMatcher(None, query_norm, candidate_norm).ratio()
            
            # Add bonus for being a substring
            if query_norm in candidate_norm:
                ratio += 0.1
            
            scores.append((candidate, ratio))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        print("LoadRandomCheckpoint: Top 10 matches:")
        for i in range(min(10, len(scores))):
            print(f"  - Score: {scores[i][1]:.2f}, File: {scores[i][0]}")

        if scores and scores[0][1] > 0.3: # Confidence threshold
            return scores[0][0]
        else:
            return None

    def load_checkpoint(self, checkpoints, seed, repeat_count, shuffle, limit_to_paths=""):
        # --- Build a list of potential targets from the input text area ---
        potential_targets = []
        ckpt_base_dirs = folder_paths.get_folder_paths("checkpoints")
        
        for line in checkpoints.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check if the line is a directory path
            path_to_check = ""
            if os.path.isabs(line):
                path_to_check = line
            else:
                # Check relative to the main checkpoints folder
                path_to_check = os.path.abspath(os.path.join(ckpt_base_dirs[0], line))
            
            if os.path.isdir(path_to_check):
                print(f"LoadRandomCheckpoint: Expanding directory: {path_to_check}")
                for root, _, files in os.walk(path_to_check, followlinks=True):
                    for file in files:
                        if file.endswith(('.ckpt', '.safetensors')):
                            potential_targets.append(os.path.join(root, file))
            else:
                # If not a directory, treat it as a name/query
                potential_targets.append(line)

        if not potential_targets:
            raise ValueError("The checkpoint list is empty or contains no valid paths/names.")

        # --- Determine which target to use based on seed and shuffle settings ---
        effective_index = seed // repeat_count
        if shuffle:
            random.seed(effective_index)
            selected_name = random.choice(potential_targets)
        else:
            selected_name = potential_targets[effective_index % len(potential_targets)]

        if os.path.isabs(selected_name) and os.path.exists(selected_name):
            print(f"LoadRandomCheckpoint: Using absolute path from list: {selected_name}")
            ckpt_path = selected_name
        else:
            # Build a comprehensive list of all available checkpoints with absolute paths
            all_ckpt_abs_paths = set()
            ckpt_base_dirs = folder_paths.get_folder_paths("checkpoints")
            for base_dir in ckpt_base_dirs:
                for root, _, files in os.walk(base_dir, followlinks=True):
                    for file in files:
                        if file.endswith(('.ckpt', '.safetensors')):
                            all_ckpt_abs_paths.add(os.path.join(root, file))
            
            search_candidates_abs = list(all_ckpt_abs_paths)

            # Filter this list if limit_to_paths is used
            user_paths = [p.strip() for p in limit_to_paths.splitlines() if p.strip()]
            if user_paths:
                resolved_user_paths = []
                for p in user_paths:
                    if os.path.isabs(p):
                        resolved_user_paths.append(os.path.abspath(p))
                    else:
                        # Assume relative paths are relative to the first (main) checkpoints folder
                        resolved_user_paths.append(os.path.abspath(os.path.join(ckpt_base_dirs[0], p)))
                
                filtered_paths = [p for p in search_candidates_abs if any(p.startswith(user_p) for user_p in resolved_user_paths)]
                
                if filtered_paths:
                    search_candidates_abs = filtered_paths
                else:
                    print(f"LoadRandomCheckpoint: Warning - No checkpoints found in specified paths. Searching all checkpoints instead.")

            # Perform the search against the final candidate list
            best_match_abs = self.find_best_match_custom(selected_name, search_candidates_abs)
            ckpt_path = best_match_abs

        if not ckpt_path:
            raise FileNotFoundError(f"Could not find a valid checkpoint file for '{selected_name}'. The new search algorithm also failed.")

        print(f"LoadRandomCheckpoint: Loading checkpoint: {os.path.basename(ckpt_path)}")
        
        model, clip, vae, _ = comfy.sd.load_checkpoint_guess_config(
            ckpt_path, 
            output_vae=True, 
            output_clip=True, 
            embedding_directory=folder_paths.get_folder_paths("embeddings")
        )

        return (model, clip, vae)

NODE_CLASS_MAPPINGS = {
    "LoadRandomCheckpoint": LoadRandomCheckpoint
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadRandomCheckpoint": "Load Random Checkpoint"
}
