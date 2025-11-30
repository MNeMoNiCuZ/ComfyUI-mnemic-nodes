import re
import random
import os
from pathlib import Path
import json
import folder_paths
from .file_utils import find_best_match
from colorama import Fore, Style, init as colorama_init

class WildcardManager:
    def __init__(self, console_log=False):
        colorama_init()
        self.console_log = console_log
        self.wildcard_cache = {}
        self.create_user_wildcard_paths_file()
        self.wildcard_files = self._find_wildcard_files()
        self.variables = {}
        self.separator = " "
        self.first_wildcard_processed = False

    def wildcard_log(self, message, level=0):
        if self.console_log:
            indent = "  " * level
            print(f"{indent}{message}{Style.RESET_ALL}")

    def create_user_wildcard_paths_file(self):
        user_settings_dir = Path(folder_paths.get_folder_paths("custom_nodes")[0]).parent / "ComfyUI-mnemic-nodes" / "nodes" / "wildcards"
        user_settings_dir.mkdir(parents=True, exist_ok=True)
        user_paths_file = user_settings_dir / "wildcards_paths_user.json"
        if not user_paths_file.exists():
            with open(user_paths_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
            self.wildcard_log(f"{Fore.CYAN}WildcardManager: Created user wildcard paths file: {user_paths_file}{Style.RESET_ALL}")

    def get_user_wildcard_paths(self):
        user_paths_file = Path(folder_paths.get_folder_paths("custom_nodes")[0]).parent / "ComfyUI-mnemic-nodes" / "nodes" / "wildcards" / "wildcards_paths_user.json"
        if not user_paths_file.exists():
            return []
        
        try:
            with open(user_paths_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip():
                return []
            paths = re.findall(r'"([^"]*)"', content)
            return [p for p in paths if p.strip()]
        except Exception as e:
            self.wildcard_log(f"{Fore.YELLOW}Warning: Could not load user wildcard paths from {user_paths_file}. Error: {e}{Style.RESET_ALL}")
            return []

    def get_all_wildcard_paths(self):
        wildcard_paths = set()
        node_wildcards_path = Path(folder_paths.get_folder_paths("custom_nodes")[0]).parent / "ComfyUI-mnemic-nodes" / "wildcards"
        if node_wildcards_path.is_dir():
            wildcard_paths.add(str(node_wildcards_path))

        user_paths = self.get_user_wildcard_paths()
        if user_paths:
            wildcard_paths.update(user_paths)

        try:
            if "wildcards" in folder_paths.folder_names_and_paths:
                default_paths = folder_paths.get_folder_paths("wildcards")
                wildcard_paths.update(default_paths)
            
            comfyui_root_path = Path(folder_paths.get_folder_paths("custom_nodes")[0]).parent.parent
            root_wildcards_path = comfyui_root_path / "wildcards"
            if root_wildcards_path.is_dir():
                wildcard_paths.add(str(root_wildcards_path))
        except (ImportError, IndexError):
            self.wildcard_log("[WildcardManager] `folder_paths` not available. Relying on local and user paths.")

        return list(wildcard_paths)

    def _find_wildcard_files(self, log=False):
        wildcard_paths = self.get_all_wildcard_paths()
        all_files = []
        
        if log:
            self.wildcard_log(f"{Fore.YELLOW}\nRe-caching wildcards: Reloading user paths and re-scanning all wildcard files...{Style.RESET_ALL}")

        for p_str in wildcard_paths:
            path = Path(p_str)
            if path.is_dir():
                found_files = list(path.rglob('*.txt'))
                if log:
                    self.wildcard_log(f"  - {path} [{len(found_files)}]")
                all_files.extend([str(f) for f in found_files])
        
        if log:
            self.wildcard_log("")

        return all_files

    def get_wildcard_options(self, wildcard_name):
        if self.console_log:
            if self.first_wildcard_processed:
                print(f"\n{Fore.CYAN}{'-----' * 21}{Style.RESET_ALL}\n")
            find_best_match(wildcard_name, self.wildcard_files, log=True, wildcard_paths=self.get_all_wildcard_paths())
            self.first_wildcard_processed = True

        if wildcard_name in self.wildcard_cache:
            return self.wildcard_cache[wildcard_name]

        best_match = find_best_match(wildcard_name, self.wildcard_files, log=False, wildcard_paths=self.get_all_wildcard_paths())

        if not best_match:
            self.wildcard_cache[wildcard_name] = None
            return None

        try:
            with open(best_match, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\r\n') for line in f if line.rstrip('\r\n') and not line.lstrip().startswith('#')]
        except UnicodeDecodeError:
            self.wildcard_log(f"{Fore.YELLOW}Warning: Could not decode {os.path.basename(best_match)} as UTF-8. Trying with 'latin-1' encoding.", level=1)
            with open(best_match, 'r', encoding='latin-1') as f:
                lines = [line.rstrip('\r\n') for line in f if line.rstrip('\r\n') and not line.lstrip().startswith('#')]
        
        self.wildcard_cache[wildcard_name] = lines
        return lines

    def _evaluate_file_wildcard(self, match):
        wildcard_name = match.group(1)
        is_glob = any(c in wildcard_name for c in '*?[]')

        if not is_glob:
            options = self.get_wildcard_options(wildcard_name)
            if not options:
                return match.group(0)
            chosen_option = self._process_text(random.choice(options))
            self.wildcard_log(f"{Style.DIM}Evaluated {match.group(0)} -> {Style.NORMAL}{Fore.MAGENTA}{chosen_option}", level=1)
            return chosen_option

        self.wildcard_log(f"Detected glob pattern: {wildcard_name}", level=1)
        all_lines = []
        wildcard_paths = self.get_all_wildcard_paths()

        matching_files = set()
        for p_str in wildcard_paths:
            p = Path(p_str)
            for found_path in p.rglob(wildcard_name):
                if found_path.is_file():
                    matching_files.add(found_path)

        if not matching_files:
            self.wildcard_log(f"{Fore.YELLOW}Warning: Glob pattern '{wildcard_name}' did not match any files.", level=1)
            return match.group(0)

        sorted_files = sorted(list(matching_files))
        self.wildcard_log(f"Glob pattern '{wildcard_name}' matched {len(sorted_files)} files: {[os.path.basename(str(f)) for f in sorted_files]}", level=1)

        for file_path in sorted_files:
            try:
                base_path = next(p for p in wildcard_paths if Path(p) in file_path.parents)
                relative_path = file_path.relative_to(base_path)
                file_wildcard_name = str(relative_path).replace('\\', '/').replace('.txt', '')
                lines = self.get_wildcard_options(file_wildcard_name)
                if lines:
                    all_lines.extend(lines)
            except StopIteration:
                 self.wildcard_log(f"{Fore.YELLOW}Warning: Could not determine base path for {file_path}. Skipping.", level=1)

        if not all_lines:
            self.wildcard_log(f"{Fore.YELLOW}Warning: Glob pattern '{wildcard_name}' matched files, but they are empty or contain only comments.", level=1)
            return match.group(0)

        chosen_option = self._process_text(random.choice(all_lines))
        self.wildcard_log(f"{Style.DIM}Evaluated glob {match.group(0)} -> {Style.NORMAL}{Fore.MAGENTA}{chosen_option}", level=1)
        return chosen_option

    def evaluate_curly_braces(self, match):
        expression = match.group(1)
        expression = re.sub(r'#.*', '', expression)
        expression = re.sub(r'\s*\n\s*', '', expression)

        count = 1
        min_count, max_count = 1, 1
        is_range = False
        
        count_match = re.match(r'(\d+)-(\d+)\$\$(.*)', expression)
        if count_match:
            min_count, max_count, expression = int(count_match.group(1)), int(count_match.group(2)), count_match.group(3)
            is_range = True
        else:
            count_match = re.match(r'(\d+)\$\$(.*)', expression)
            if count_match:
                count, expression = int(count_match.group(1)), count_match.group(2)
                min_count = max_count = count

        if is_range:
            count = random.randint(min_count, max_count)
        
        options_str = expression.split('|')
        choices = []
        weights = []
        for option in options_str:
            weight_match = re.match(r'(\d+(?:\.\d+)?)::(.*)', option)
            if weight_match:
                weight = float(weight_match.group(1))
                opt = weight_match.group(2)
                weights.append(weight)
                choices.append(opt)
            else:
                weights.append(1.0)
                choices.append(option)
        
        if not choices:
            return ""

        selected_options = []
        if count > 0:
            remaining_count = count
            
            while remaining_count > 0:
                num_to_pick = min(remaining_count, len(choices))
                
                if all(w == 1.0 for w in weights):
                    selected_options.extend(random.sample(choices, k=num_to_pick))
                else:
                    temp_choices = list(choices)
                    temp_weights = list(weights)
                    for _ in range(num_to_pick):
                        if not temp_choices: break
                        chosen = random.choices(temp_choices, weights=temp_weights, k=1)[0]
                        selected_options.append(chosen)
                        idx = temp_choices.index(chosen)
                        temp_choices.pop(idx)
                        temp_weights.pop(idx)
                
                remaining_count -= num_to_pick
        
        result = self.separator.join(selected_options)
        self.wildcard_log(f"{Style.DIM}Evaluated {{{match.group(1)}}} -> {Style.NORMAL}{Fore.CYAN}{result}", level=1)
        return result

    def _process_text(self, text):
        while True:
            original_text = text
            
            for var_name, var_value in self.variables.items():
                text = text.replace(f"${{{var_name}}}", var_value)

            text = re.sub(r'{([^{}]*?)}', self.evaluate_curly_braces, text)
            text = re.sub(r'__([a-zA-Z0-9_./\\*?\[\]-]+?)__', self._evaluate_file_wildcard, text)

            if text == original_text:
                break
        return text

    def process(self, text, separator=" ", seed=0, recache=False):
        random.seed(seed)
        self.variables = {}
        self.first_wildcard_processed = False
        self.separator = separator

        if recache:
            self.wildcard_files = self._find_wildcard_files(log=self.console_log)
            self.wildcard_cache.clear()

        variable_pattern = r"\${(.*?)=!(.*?)}"
        definitions = re.findall(variable_pattern, text)
        
        text_no_defs = re.sub(variable_pattern, "", text)

        for var_name, var_value_expr in definitions:
            var_name = var_name.strip()
            # To evaluate the expression, we need a new manager to avoid state collision
            temp_manager = WildcardManager(console_log=False)
            var_seed = random.randint(0, 0xffffffffffffffff)
            evaluated_value = temp_manager.process(var_value_expr, seed=var_seed)
            
            self.variables[var_name] = evaluated_value
            self.wildcard_log(f"Defined variable ${{{var_name}}} = {evaluated_value}")

        processed_text = self._process_text(text_no_defs)
        return processed_text
