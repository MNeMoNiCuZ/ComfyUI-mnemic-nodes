import re
import random
import os
from pathlib import Path
import folder_paths
import json
from ..utils.file_utils import find_best_match
from colorama import Fore, Style, init as colorama_init

class WildcardProcessor:
    """
    A custom node for ComfyUI that processes text containing wildcards, with support for
    file-based wildcards, inline choices, weights, multiple selections, variables, and nesting.
    This is a complete rewrite of the original node to fix issues and add features.
    """
    OUTPUT_NODE = True
    FUNCTION = "process_wildcards"
    CATEGORY = "⚡ MNeMiC Nodes"
    # Set to True to enable console logging, False to disable.
    console_log = True

    DESCRIPTION = ("A versatile text processor that replaces wildcards with dynamic content from files or inline lists.\n\n"
                         "Features:\n"
                         "File Wildcards:\nUse __filename__ to insert a random line from filename.txt in one of the supported wildcard directories. Lines starting with # are treated as comments and are ignored.\n\n"
                         "Inline Choices:\nUse {a|b|c} to randomly choose between a, b, or c.\nExample Input: A photo of a {red|green|blue} car.\nExample Output: A photo of a green car.\n\n"
                         "Weighted Choices:\nUse {5::black|green|red} to make black 5 times more likely to be chosen than green or red.\n\n"
                         "Select Multiple Wildcards:\nUse {2$$a|b|c|d} to output a specific number of items from the result.\nExample Input: My favorite colors are {3$$red|green|blue|yellow|purple}.\nExample Output: My favorite colors are blue, yellow, purple.\n\n"
                         "Ranged Select Multiple:\nUse {1-3$$red|green|blue|yellow|purple} to select a random number of 1-3 items within a range.\n\n"
                         "Variables:\nDefine a variable to reuse a value. Can be defined directly, or using a wildcard\nExample Input: ${animal=!__animals__} The ${animal} is friends with the other ${animal}.\nExample Output: The cat is friends with the other cat.\n\n"
                         "Smart wildcard matching:\nThe node will try to find the best match for a wildcard, even if the name is not an exact match. It will search for files in the wildcards directories and use the best match based on a scoring system. Exact matches have priority, and more root level files have priority after that.\n\n"
                         "Multiple Wildcard Paths:\nWildcards can be placed in different directories. It's recommended to only use one.\n"
                         "\nPaths:\n"
                         "ComfyUI/wildcards\n"
                         "ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards\n"
                         "or in a user-defined path in: ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json.\n\n"
                         "View README_WILDCARD.md for more information."
                         )
    
    def __init__(self):
        colorama_init()
        # Caches to store wildcard file content and located file paths
        self.wildcard_cache = {}
        self.create_user_wildcard_paths_file()  # Ensure the user paths file exists
        self.wildcard_files = self._find_wildcard_files()
        # Variables for the current processing run
        self.variables = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wildcard_string": ("STRING", {
                    "multiline": True,
                    "dynamicPrompts": False,
                    "tooltip": (
                        "The text prompt to process. Supports multiple features:\n\n"
                        "File Wildcards:\nUse __filename__ to insert a random line from filename.txt in one of the supported wildcard directories. Lines starting with # are treated as comments and are ignored.\n\n"
                        "Inline Choices:\nUse {a|b|c} to randomly choose between a, b, or c.\nExample Input: A photo of a {red|green|blue} car.\nExample Output: A photo of a green car.\n\n"
                        "Weighted Choices:\nUse {5::black|green|red} to make black 5 times more likely to be chosen than green or red.\n\n"
                        "Select Multiple Wildcards:\nUse {2$$a|b|c|d} to output a specific number of items from the result.\nExample Input: My favorite colors are {3$$red|green|blue|yellow|purple}.\nExample Output: My favorite colors are blue, yellow, purple.\n\n"
                        "Ranged Select Multiple:\nUse {1-3$$red|green|blue|yellow|purple} to select a random number of 1-3 items within a range.\n\n"
                        "Variables:\nDefine a variable to reuse a value. Can be defined directly, or using a wildcard\nExample Input: ${animal=!__animals__} The ${animal} is friends with the other ${animal}.\nExample Output: The cat is friends with the other cat."
                    ),
                    "placeholder": "A photo of a __sample_colors__ {dog|cat|monkey}."
                }),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "The seed for the random number generator. Using the same seed with the same prompt will produce the same output."}),
                "multiple_separator": ("STRING", {"default": " ", "multiline": False, "tooltip": "The separator used when selecting multiple items from a single wildcard.\n\nExample:\n- Prompt: {2$$red|green|blue}\n- Separator: \", \"\n- Output example: \"red, green\""}),
                "recache_wildcards": ("BOOLEAN", {"default": False, "tooltip": "Force a reload of all wildcard files from disk. Can be disabled again after you have ran it once."}),

                # The console_log and tag_extraction_tags inputs are temporarily removed from the UI.
                # Console logging can be forced on or off by changing the FORCE_CONSOLE_LOG setting at the top of the class.
                # To re-enable the UI controls, uncomment the following blocks and update the process_wildcards method.
                # "console_log": ("BOOLEAN", {"default": False, "tooltip": "Enable or disable detailed logging of the wildcard processing steps in the console."}),
                # "tag_extraction_tags": ("STRING", {
                #     "default": "",
                #     "multiline": False,
                #     "tooltip": "Define pairs of characters to extract tags from the prompt. Example: [],**,<<>>. The extracted content is processed for wildcards and removed from the main prompt. \n\nReserved characters: ( ) { } |.",
                #     "placeholder": "Example: [],**,<>"
                # }),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING", "STRING", "STRING",)
    RETURN_NAMES = ("processed_text", "seed", "extracted_tags_string", "extracted_tags_list", "raw_tags_string", "raw_tags_list",)
    OUTPUT_TOOLTIPS = (
        "The final text after all wildcards and tags have been processed.",
        "The seed value used for this generation.",
        "A single string containing all extracted and processed tag content, joined by '|'.",
        "A list of strings, where each item is one piece of extracted and processed tag content.",
        "A single string containing all raw, unprocessed tags, including their delimiters, concatenated together.",
        "A list of strings, where each item is one raw, unprocessed tag, including its delimiters."
    )

    def wildcard_log(self, message, level=0):
        """Logs a message to the console if logging is enabled, with color and indentation."""
        if self.console_log:
            indent = "  " * level
            print(f"{indent}{message}{Style.RESET_ALL}")

    def create_user_wildcard_paths_file(self):
        """Creates an empty user wildcard paths file if it doesn't exist."""
        user_settings_dir = Path(__file__).parent / "wildcards"
        user_settings_dir.mkdir(parents=True, exist_ok=True)
        user_paths_file = user_settings_dir / "wildcards_paths_user.json"
        if not user_paths_file.exists():
            with open(user_paths_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
            print(f"{Fore.CYAN}WildcardProcessor: Created user wildcard paths file: {user_paths_file}{Style.RESET_ALL}")

    def get_user_wildcard_paths(self):
        """
        Loads user-defined wildcard paths from wildcards_paths_user.json.
        This parser is intentionally lenient to handle paths with single backslashes
        that would otherwise be invalid in strict JSON.
        """
        user_paths_file = Path(__file__).parent / "wildcards" / "wildcards_paths_user.json"
        if not user_paths_file.exists():
            return []
        
        try:
            with open(user_paths_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return []

            # Use regex to find all strings within quotes. This is robust against
            # JSON errors caused by unescaped backslashes.
            paths = re.findall(r'"([^"]*)"', content)
            # The Path() object constructor will handle normalizing the slashes.
            return [p for p in paths if p.strip()]

        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load user wildcard paths from {user_paths_file}. Error: {e}{Style.RESET_ALL}")
            return []

    def get_all_wildcard_paths(self):
        """
        Gets all wildcard paths, including this node's, user-defined, and ComfyUI root paths.
        """
        # Use a set to avoid duplicate paths.
        wildcard_paths = set()

        # 1. Add this node's own 'wildcards' directory.
        node_wildcards_path = Path(__file__).parent.parent / "wildcards"
        if node_wildcards_path.is_dir():
            wildcard_paths.add(str(node_wildcards_path))

        # 2. Add user-defined paths from the JSON file.
        user_paths = self.get_user_wildcard_paths()
        if user_paths:
            wildcard_paths.update(user_paths)

        # 3. Add ComfyUI's default wildcard paths and root wildcard folder.
        try:
            # Safely get ComfyUI's default wildcard paths, if they exist.
            if "wildcards" in folder_paths.folder_names_and_paths:
                default_paths = folder_paths.get_folder_paths("wildcards")
                wildcard_paths.update(default_paths)
            
            # Also add the main ComfyUI wildcards folder.
            comfyui_root_path = Path(folder_paths.get_folder_paths("custom_nodes")[0]).parent
            root_wildcards_path = comfyui_root_path / "wildcards"
            if root_wildcards_path.is_dir():
                wildcard_paths.add(str(root_wildcards_path))

        except (ImportError, IndexError):
            print("[WildcardProcessor] `folder_paths` not available. Relying on local and user paths.")

        return list(wildcard_paths)

    def _find_wildcard_files(self, log=False):
        """Scans for all .txt files in the wildcards directories, with optional logging."""
        wildcard_paths = self.get_all_wildcard_paths()
        all_files = []
        
        if log:
            print(f"{Fore.YELLOW}\nRe-caching wildcards: Reloading user paths and re-scanning all wildcard files...{Style.RESET_ALL}")

        for p_str in wildcard_paths:
            path = Path(p_str)
            if path.is_dir():
                found_files = list(path.rglob('*.txt'))
                if log:
                    print(f"  - {path} [{len(found_files)}]")
                all_files.extend([str(f) for f in found_files])
        
        if log:
            print() # Add a newline for clear separation

        return all_files

    def get_wildcard_options(self, wildcard_name):
        """
        Retrieves the content of a wildcard file using the prioritization schema.
        Caches results for efficiency.
        """
        # If logging is on, we always want to show the search process.
        if self.console_log:
            if self.first_wildcard_processed:
                # Add a separator between wildcard processing logs
                print(f"\n{Fore.CYAN}{'-----' * 21}{Style.RESET_ALL}\n") # Match length of the start/end separator
            # Pass wildcard_paths to find_best_match for accurate logging
            find_best_match(wildcard_name, self.wildcard_files, log=True, wildcard_paths=self.get_all_wildcard_paths())
            self.first_wildcard_processed = True

        # Now, get the content, using cache if possible.
        if wildcard_name in self.wildcard_cache:
            return self.wildcard_cache[wildcard_name]

        # Cache miss, so find the file (silently) and read it.
        best_match = find_best_match(wildcard_name, self.wildcard_files, log=False, wildcard_paths=self.get_all_wildcard_paths())

        if not best_match:
            self.wildcard_cache[wildcard_name] = None # Cache the failure
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
        """
        Replaces a __wildcard__ with a random line from corresponding file(s).
        Supports glob patterns for filename matching.
        """
        wildcard_name = match.group(1)
        # A simple check to see if the wildcard name contains any glob characters.
        is_glob = any(c in wildcard_name for c in '*?[]')

        # If it's not a glob pattern, use the existing efficient method.
        if not is_glob:
            options = self.get_wildcard_options(wildcard_name)
            if not options:
                return match.group(0)
            chosen_option = self._process_text(random.choice(options))
            self.wildcard_log(f"{Style.DIM}Evaluated {match.group(0)} -> {Style.NORMAL}{Fore.MAGENTA}{chosen_option}", level=1)
            return chosen_option

        # If it is a glob pattern, perform a file search.
        self.wildcard_log(f"Detected glob pattern: {wildcard_name}", level=1)
        all_lines = []
        wildcard_paths = self.get_all_wildcard_paths()

        matching_files = set()
        for p_str in wildcard_paths:
            p = Path(p_str)
            # The glob pattern is applied relative to each wildcard directory.
            # `rglob` is used for recursive matching, which is what `**` does.
            for found_path in p.rglob(wildcard_name):
                if found_path.is_file():
                    matching_files.add(found_path)

        if not matching_files:
            self.wildcard_log(f"{Fore.YELLOW}Warning: Glob pattern '{wildcard_name}' did not match any files.", level=1)
            return match.group(0)

        # Sort files for deterministic behavior in tests.
        sorted_files = sorted(list(matching_files))
        self.wildcard_log(f"Glob pattern '{wildcard_name}' matched {len(sorted_files)} files: {[os.path.basename(str(f)) for f in sorted_files]}", level=1)

        for file_path in sorted_files:
            # Use the cached method to read files to avoid re-reading.
            # We need to find the "wildcard name" that corresponds to the file path.
            # This is a bit tricky, but we can derive it.
            try:
                # Find which base path this file belongs to
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
        """
        Evaluates an inline wildcard expression, e.g., {a|b|c}.
        Handles weights, multiple selections, and nesting.
        """
        expression = match.group(1)

        # 1. Clean comments and whitespace
        expression = re.sub(r'#.*', '', expression)
        expression = re.sub(r'\s*\n\s*', '', expression)

        # 2. Parse multi-selection syntax (e.g., {2$$...} or {1-3$$...})
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
        
        # 3. Split into options and parse weights (e.g., {2::a|b})
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

        # 4. Select `count` options, allowing for looping if count > number of choices
        selected_options = []
        if count > 0:
            remaining_count = count
            
            while remaining_count > 0:
                num_to_pick = min(remaining_count, len(choices))
                
                # If weights are uniform, `random.sample` is efficient.
                if all(w == 1.0 for w in weights):
                    selected_options.extend(random.sample(choices, k=num_to_pick))
                else:
                    # For weighted unique sampling, we pick one by one.
                    # We need to create a temporary list to modify for each loop.
                    temp_choices = list(choices)
                    temp_weights = list(weights)
                    for _ in range(num_to_pick):
                        if not temp_choices: break # Should not happen with this logic, but safe
                        chosen = random.choices(temp_choices, weights=temp_weights, k=1)[0]
                        selected_options.append(chosen)
                        idx = temp_choices.index(chosen)
                        temp_choices.pop(idx)
                        temp_weights.pop(idx)
                
                remaining_count -= num_to_pick
        
        # 5. Join and return using the provided separator.
        result = self.separator.join(selected_options)

        self.wildcard_log(f"{Style.DIM}Evaluated {{{match.group(1)}}} -> {Style.NORMAL}{Fore.CYAN}{result}", level=1)
        return result

    def _process_text(self, text):
        """
        Iteratively processes a string, resolving wildcards from the inside out.
        This function handles both __file__ wildcards and {inline|wildcards}.
        """
        # Loop until the string no longer changes, ensuring all nested wildcards are processed.
        while True:
            original_text = text
            
            # First, substitute any defined variables.
            for var_name, var_value in self.variables.items():
                text = text.replace(f"${{{var_name}}}", var_value)

            # Process innermost curly braces expressions
            text = re.sub(r'{([^{}]*?)}', self.evaluate_curly_braces, text)
            
            # Process file-based wildcards
            # Process file-based wildcards (including glob patterns)
            text = re.sub(r'__([a-zA-Z0-9_./\\*?\[\]-]+?)__', self._evaluate_file_wildcard, text)

            if text == original_text:
                break
        return text

    def extract_and_process_tags(self, text, tag_delimiters_str):
        """
        Extracts content from specified tags, processes wildcards within them,
        and removes them from the original text.
        """
        if not tag_delimiters_str:
            return text, [], []

        raw_tags_found = []
        
        # Parse the tag delimiters
        # e.g., "[],**,<<>>" -> [('[', ']'), ('*', '*'), ('<', '>')]
        delimiter_pairs = []
        raw_pairs = tag_delimiters_str.split(',')
        for pair in raw_pairs:
            pair = pair.strip()
            if len(pair) >= 2:
                start_tag = pair[0]
                end_tag = pair[-1]
                # Validation
                if any(char in '()}{)|' for char in (start_tag, end_tag)):
                    self.wildcard_log(f"{Fore.YELLOW}Warning: Invalid characters in tag pair '{pair}'. Skipping.", level=1)
                    continue
                delimiter_pairs.append((start_tag, end_tag))

        if not delimiter_pairs:
            return text, [], []

        # Build a regex to find all tags
        # e.g., (\[.*?\])|(\*.*?\*)|(\<.*?\>)
        # We now capture the full tag, including delimiters
        regex_parts = []
        for start, end in delimiter_pairs:
            # Escape special regex characters
            esc_start = re.escape(start)
            esc_end = re.escape(end)
            # Capture the full tag including delimiters
            regex_parts.append(f"({esc_start}.*?{esc_end})")
        
        full_regex = "|".join(regex_parts)

        # We need to find all matches and then process them.
        matches = list(re.finditer(full_regex, text, re.DOTALL))
        
        # We iterate backwards to not mess up indices of unprocessed parts of the string
        for match in reversed(matches):
            # The first non-None group is our full matched tag.
            full_tag = next((g for g in match.groups() if g is not None), None)
            
            if full_tag is not None:
                # Prepend to our list to maintain original order
                # We store the original tag with its delimiters
                raw_tags_found.insert(0, full_tag)
                # Remove the matched tag from the text
                text = text[:match.start()] + text[match.end():]

        # Now, process the extracted contents for wildcards
        processed_tags = []
        processed_raw_tags = [] # This will hold the raw tags with resolved wildcards
        if raw_tags_found:
            self.wildcard_log(f"Extracted {len(raw_tags_found)} raw tags for processing: {raw_tags_found}")
            for i, raw_tag in enumerate(raw_tags_found):
                # To process, we need to strip the outer delimiters first
                # This is a bit naive but works for single-character delimiters
                start_delim = raw_tag[0]
                end_delim = raw_tag[-1]
                content_to_process = raw_tag[1:-1]
                
                # Process the content inside the tag
                processed_content = self._process_text(content_to_process)
                processed_tags.append(processed_content)
                
                # Re-assemble the "raw" tag with the processed content
                processed_raw_tag = f"{start_delim}{processed_content}{end_delim}"
                processed_raw_tags.append(processed_raw_tag)

                self.wildcard_log(f"Processed tag #{i+1}: '{raw_tag}' -> '{processed_content}'", level=1)
        
        return text, processed_tags, processed_raw_tags

    def process_wildcards(self, **kwargs):
        """
        Main function to process an input string with wildcards.
        All inputs are received via kwargs to handle spaces in names.
        """
        # Extract parameters from kwargs
        wildcard_string = kwargs.get("wildcard_string", "")
        seed = kwargs.get("seed", 0)
        self.separator = kwargs.get("multiple_separator", " ")
        self.console_log = WildcardProcessor.console_log
        recache = kwargs.get("recache_wildcards", False)
        tag_extraction_tags = kwargs.get("tag_extraction_tags", "")

        random.seed(seed)
        self.variables = {} # Reset variables for each run
        self.first_wildcard_processed = False # Reset for each run

        if recache:
            # Re-scan all wildcard directories and clear the cache.
            # The logging is now handled inside _find_wildcard_files.
            self.wildcard_files = self._find_wildcard_files(log=self.console_log)
            self.wildcard_cache.clear()

        if self.console_log:
            print(f"{Fore.GREEN}{'-----' * 8}📝 Wildcard Processor Start{'-----' * 8}{Style.RESET_ALL}")
            # Use repr() to make newlines and other special characters visible
            print(f"{Fore.YELLOW}Input:{Style.RESET_ALL} {repr(wildcard_string)}")
            print(f"{Fore.YELLOW}Seed:{Style.RESET_ALL} {seed}")
            if tag_extraction_tags:
                print(f"{Fore.YELLOW}Tag Delimiters:{Style.RESET_ALL} {tag_extraction_tags}")


        text = wildcard_string

        # 1. Find and evaluate variable definitions: ${var=!{...}}
        variable_pattern = r"\${(.*?)=!(.*?)}"
        definitions = re.findall(variable_pattern, text)
        
        # Create a temporary, clean version of the text with definitions removed
        text_no_defs = re.sub(variable_pattern, "", text)

        for var_name, var_value_expr in definitions:
            var_name = var_name.strip()
            # The value expression itself can contain wildcards. To evaluate it in isolation,
            # we instantiate a temporary processor.
            temp_processor = WildcardProcessor()
            # Use a new random seed for variable evaluation to not interfere with main seed
            var_seed = random.randint(0, 0xffffffffffffffff)
            # We pass console log as false to prevent recursive logging clutter.
            evaluated_value = temp_processor.process_wildcards(**{"wildcard_string": var_value_expr, "seed": var_seed, "console_log": False})[0]
            
            self.variables[var_name] = evaluated_value
            self.wildcard_log(f"Defined variable ${{{var_name}}} = {evaluated_value}")

        # 2. Extract and process tags
        text_after_extraction, processed_tags, raw_tags = self.extract_and_process_tags(text_no_defs, tag_extraction_tags)

        # 3. Process the main text (which has definitions and tags removed)
        processed_text = self._process_text(text_after_extraction)

        # 4. Prepare outputs
        extracted_tags_string = "|".join(processed_tags)
        extracted_tags_list = processed_tags
        
        # New raw outputs
        raw_tags_string = "".join(raw_tags) # Concatenated without any separator
        raw_tags_list = raw_tags


        if self.console_log:
            if raw_tags:
                print(f"{Fore.YELLOW}Extracted Tags (Raw):{Style.RESET_ALL} {raw_tags}")
                print(f"{Fore.YELLOW}Extracted Tags (Processed):{Style.RESET_ALL} {processed_tags}")
            print(f"{Fore.YELLOW}Processed Text:{Style.RESET_ALL} {repr(processed_text)}")
            print(f"{Fore.GREEN}{'-----' * 8}📝 Wildcard Processor End{'-----' * 8}{Style.RESET_ALL}")
            
        return (processed_text, seed, extracted_tags_string, extracted_tags_list, raw_tags_string, raw_tags_list)

NODE_CLASS_MAPPINGS = {
    "WildcardProcessor": WildcardProcessor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WildcardProcessor": "Wildcard Processor",
}