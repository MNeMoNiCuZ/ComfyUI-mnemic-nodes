# Wildcard Processor

The Wildcard Processor is a powerful and flexible custom node for ComfyUI designed to add dynamic content to your prompts. It allows you to pull random elements from lists, use weighted choices, select multiple items, define variables, and nest these features for complex and varied outputs.

This node is a complete rewrite of a previous version, designed for stability, performance, and a rich feature set.

This node adds powerful dynamic capabilities to your prompts. Wildcards are generally used to randomize your output, by writing the prompt in a specific format, or loading random lines from text-files.

## Feature Summary

### Smart Wildcard Matching
Smart wildcard matching:\nThe node will try to find the best match for a wildcard, even if the name is not an exact match. It will search for files in the wildcards directories and use the best match based on a scoring system. Exact matches have priority, and more root level files have priority after that.

### Multiple Wildcard Paths
Wildcards can be placed in different directories. It's recommended to only use one, but they can all be combined.
Paths:
- `ComfyUI/wildcards`
- `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards`

or in a user-defined path in:

- `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json`

### File Wildcards

Loads a random line from a text-file in the wildcards directory.

![image](https://github.com/user-attachments/assets/0c57e27c-2e78-41c4-afde-62c6de186141)

-   **Syntax**: `__filename__`
-   **Description**: Inserts a random line from a `.txt` file found in one of the supported `wildcards` directories.
    -   `ComfyUI/wildcards/`
    -   `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards/`
    -   or in a user-defined path in
        -   `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json`
-   **Example**: `A photo of a __color__ __animal__.` -> `A photo of a blue frog.`
-   Empty lines are automatically discarded.
-   Comments can be made using `# commented line`

---

### Inline Wildcards

Creates a wildcard right in the prompt instead of loading from a file.

![image](https://github.com/user-attachments/assets/848e6b2a-5a13-48ee-8063-8935337fe2eb)

-   **Syntax**: `{option1|option2|option3}`
-   **Description**: Chooses one of the provided options.
-   **Example**: `A {red|green|blue} car.` -> `A green car.`

---

### Weighted Choices

Makes one entry more likely to be chosen than others.

![image](https://github.com/user-attachments/assets/bbceea2a-3c23-4c3c-b19d-efc91bf705a1)

-   **Syntax**: `{weight::option1|option2}`
-   **Description**: Changes the chance that an option gets randomly selected. `weight` is an integer number (e.g., `5`). Default weight is 1.
-   **Example**: `A {4::red|2::green|blue} car.` -> `A red car.`
    -   Red is chosen randomly 4 times more often than Blue
    -   Green is twice as likely to be chosen as Blue
    -   Red is twice as likely to be chosen as Green

---

### Multiple Selections (Fixed & Ranged)

Returns X number of wildcard results based the input number. The input can also be a range.

![image](https://github.com/user-attachments/assets/9251f16c-6824-49e0-a560-91c71dd4dbe0)


-   **Syntax**: `{N$$...}` for a fixed number, `{N-M$$...}` for a random range.
-   **Description**: Selects multiple items from a list, joined by the `multiple_separator` string. If the number of requested items is greater than the number of available options, it will loop and start picking from the beginning again.
-   **Example (Fixed)**:
    -   **Prompt**: `{2$$red|green|blue|purple}`
    -   **Output**: `red, green`
-   **Example (Range)**:
    -   **Prompt**: `A {1-3$$red|green|blue|purple|white|gold} outfit`
    -   **Output**: `blue, white, purple` (Randomly got 1-4 outputs, we got 3 in this case. If the number of items to select is larger than the number of options, it will loop.)
-   There is an option for the separator in the node. This is inserted between each selected entry.

---

### Variables

Define a variable to reuse a value. Can be defined directly, or using a wildcard. This can be useful if you want to randomize a part, but want to re-use the randomized value multiple times in your prompt.

![image](https://github.com/user-attachments/assets/d12c52d4-b6e7-4aee-a3bf-ac36edaa708d)


-   **Syntax**: `${var=!{...}}` and `${var}`
-   **Description**: Defines a variable `${var}` with a dynamic value that can be reused.
-   **Example**: `${animal=!__animals__} The ${animal} is friends with the other ${animal}.` -> `The cat is friends with the other cat.`

---

### Nesting

Everything can be combined into more complex prompts.

![image](https://github.com/user-attachments/assets/3ea9a7ce-440b-44f2-91e5-2b1f82dd80f5)


-   **Description**: All features can be nested.
-   **Example**: `A {3::big|small|__color__} __animal__ wearing a {2$$__color__} jacket` -> `A big Panda wearing a pink blue jacket`

---

### Glob Wildcards

Use * as wildcards for your wildcards. Use this when you want to select a random output from multiple files matching the same pattern, or from all files in a folder.

[More information](https://pymotw.com/2/glob/)

![image](https://github.com/user-attachments/assets/bd0d3335-88f2-4a2c-8340-6d89839960dc)

-   **Syntax**: `__*filename*__`
-   **Description**: Uses glob patterns to match multiple files. It collects all lines from all matched files and picks one randomly.
-   **Example**: `a __*color*__ vase` -> `A green vase` (Selected from all wildcard files that has the word `color` in their name)


You can also use it to randomly select a random wildcard file from inside a folder.

![image](https://github.com/user-attachments/assets/b8b1451f-ac93-4cd4-b9b6-fb114e3ac583)


-   **Syntax**: `__path/to/*__`
-   **Description**: Uses glob patterns to match all files inside a folder. A random file is chosen.
-   **Example**: `__environment/*__` -> africa.txt `Majestic views of the Kabylie mountains in Algeria at midday.` (Selected from a random wildcard file in the /environment subfolder)


---

### Seed Output

-   **Description**: The node outputs the integer `seed` that was used for the generation. This is useful if you want to match seeds in multiple nodes.

---

### Tag Extraction

Advanced functionality that lets you extract encapsulated results from the final prompt.

![image](https://github.com/user-attachments/assets/b28b6a71-e19e-46bf-81c1-7276bd59e5a4)


-   **Syntax**: Define delimiter pairs in the `tag_extraction_tags` input (e.g., `[],<>`). Then use them in your prompt: `A prompt with [tagged content] and <more>`.
-   **Description**: Extracts content from the defined tags. The content is processed for wildcards and removed from the main prompt.
-   **Outputs**:
    - `processed_text`: The prompt with tags removed.
    - `extracted_tags_string`: Processed content from tags, joined by `|`.
    - `extracted_tags_list`: A list of the processed tag contents.
    - `raw_tags_string`: The re-assembled tags (including delimiters) with their content processed.
    - `raw_tags_list`: A list of the re-assembled, processed tags.
-   **Tip**: Use the `String Text Splitter` node to split the `extracted_tags_string` output.
-   **Tip**: Use the `String Text Extractor` node to capture the values of the `raw_tags_string` output.

---

## Features Documentation

- **File-based Wildcards**: Use `__filename__` to insert a random line from any `.txt` file in your `wildcards` folder. Lines starting with `#` are ignored.
- **Glob Wildcards**: Use patterns like `__animals/*__` to randomly select a line from any file within the `animals` subdirectory.
- **Inline Wildcards**: Use `{option1|option2|option3}` for simple, on-the-fly choices.
- **Weighted Choices**: Give certain options a higher chance of being picked with `{2::option1|option2}`.
- **Multiple Selections**:
    - **Fixed**: Choose a specific number of items: `{3$$item1|item2|item3|item4}`. If the count is larger than the number of items, it will loop.
    - **Ranged**: Choose a random number of items within a range: `{1-3$$item1|item2|item3|item4}`.
- **Custom Separator**: An input field on the node lets you define the string used to join multiple selected items from a single wildcard (e.g., a space, a comma, or nothing).
- **Variables**: Define and reuse a dynamic value within your prompt: `${my_var=!{a|b|c}} ... ${my_var}`.
- **Nesting**: Combine any of the above features, like `A {__colors__} {car|truck} with a {__animal__|__colors__} decal.`
- **Comments & Whitespace**: Add comments (`#`) and line breaks inside `{}` blocks to keep your prompts readable.
- **Intelligent File Matching**: When looking for `__wildcard__` files, the processor uses a smart matching system to find the best possible file, prioritizing exact matches and handling subdirectories gracefully.
- **Console Logging**: A toggleable option to print detailed processing steps to the console for easy debugging and verification. (Note: This is currently disabled from the UI but can be re-enabled in the code.)
- **Tag Extraction**: A powerful feature to pull specific parts out of your prompt for separate use, while removing them from the main text. (Note: This is currently disabled from the UI but can be re-enabled in the code.)

## How to Use

1.  **Add the Node**: Add the `Wildcard Processor` node to your workflow.
2.  **Connect Inputs**:
    -   `wildcard_string`: This is where you write your prompt using the wildcard syntax.
    -   `seed`: Controls the randomization. Use the `control_after_generate` widget to set it to `fixed`, `randomize`, etc.
    -   `multiple_separator`: (Default: space) The character(s) to put between items when you select more than one from a single wildcard (e.g., using `2$$`).
    -   `recache_wildcards`: Enable this to force a reload of all wildcard files from disk.
    -   `consolewildcard_log`: (Default: False) Check this to see detailed output in your console.
    -   `tag_extraction_tags`: Define character pairs to extract content (e.g., `[],**`).
3.  **Connect Outputs**:
    -   `processed_text`: The final, cleaned text to be used as your prompt.
    -   `seed`: The integer seed value that was used for this run.
    -   `extracted_tags_string`: A single string containing all the processed content from the extracted tags, joined by `|`.
    -   `extracted_tags_list`: A list of strings, where each item is a piece of processed content from an extracted tag.
    -   `raw_tags_string`: A single string containing the re-assembled tags (delimiters included) after their internal wildcards have been processed.
    -   `raw_tags_list`: A list of strings, where each item is a re-assembled tag.

---

## Feature Details & Examples

### File Wildcards (`__...__`)

This feature lets you manage large lists of options in separate text files. The processor is highly flexible and searches for `.txt` wildcard files in multiple locations in a specific order of priority:

-   **ComfyUI's Root Wildcard Folder**: `ComfyUI/wildcards/`
-   **User-Defined Paths**: Any folder paths you add to the `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/nodes/wildcards/wildcards_paths_user.json` file. This allows you to organize your wildcards anywhere you like.
-   **Node's Own Wildcard Folder**: `ComfyUI/custom_nodes/ComfyUI-mnemic-nodes/wildcards/`

The node scans all these locations recursively (including subfolders). When you use a wildcard like `__animals__`, it uses a smart matching system to find the best file. It prioritizes exact matches (`animals.txt`) and files closer to the root of each wildcard directory.

-   **Example**: If you have `wildcards/animals.txt`, you can use `__animals__` in your prompt.
-   **Input**: `A cute little __animals__.`
-   **Possible Output**: `A cute little cat.`

### Glob Wildcards (`__*__`)

This feature allows you to use glob patterns (like `*`, `?`, `**`) to match multiple wildcard files at once. The node will collect all lines from all matching files and pick one at random.

-   **Example**: You have files `wildcards/monsters/goblins.txt` and `wildcards/monsters/orcs.txt`.
-   **Input**: `A dangerous __monsters/*__ appears.`
-   **Explanation**: The pattern `monsters/*` matches both `goblins.txt` and `orcs.txt`. The processor will pool all lines from both files together before picking one.
-   **Possible Output**: `A dangerous goblin scout appears.`

### Inline Wildcards (`{...|...}`)

For simple choices, you can define them directly in the prompt.

-   **Example Input**: `A {red|green|blue} car.`
-   **Possible Output**: `A green car.`
-   **Empty Options**: You can have empty options. `{a|b||d}` gives a 25% chance of returning an empty string.

### Weighted Choices (`N::...`)

To make an option more likely, prefix it with a number and `::`. The number represents its "weight". An option without a weight has a default weight of 1.

-   **Example Input**: `A {5::majestic|tiny} {10::panda|ant|crawler}.`
-   **Explanation**: `majestic` is 5 times more likely to be chosen than `tiny`, and `panda` is 10 times more likely than `ant` or `crawler`.
-   **Possible Output**: `A majestic panda.` (most of the time)

### Fixed Multiple Selections (`N$$...`)

Choose a fixed number of items from a list. If the requested number is larger than the list, it will loop. The selected items will be joined together by the string you provide in the `multiple_separator` input.

-   **Example with an inline wildcard**:
    -   **Prompt Input**: `My favorite colors are {2$$red|green|blue|yellow}.`
    -   **`multiple_separator` Input**: `, `
    -   **Possible Output**: `My favorite colors are blue, green.`

### Ranged Multiple Selections (`N-M$$...`)

Choose a random number of items from a list within a specified range. If the requested number is larger than the list, it will loop.

-   **Example with a file wildcard**:
    -   Assume you have a file `wildcards/clothing.txt` containing `hat, shirt, pants, socks`.
    -   **Prompt Input**: `The character is wearing {1-2$$__clothing__}.`
    -   **`multiple_separator` Input**: ` and `
    -   **Possible Output**: `The character is wearing shirt and socks.`

### Variables (`${...=!...}`)

Define a variable to reuse a randomly selected value multiple times in the same prompt. This ensures consistency. The value is determined once and then substituted wherever the variable is used.

-   **Example**:
    -   **Prompt Input**: `The ${animal=!__animals__} is a happy ${animal}. It loves to chase a {red|blue} ball.`
    -   **Explanation**: The `__animals__` wildcard is evaluated once and stored in the `animal` variable. That same value is then used everywhere `${animal}` appears.
    -   **Possible Output**: `The cat is a happy cat. It loves to chase a red ball.`

### Nesting

You can combine all of these features for incredibly dynamic and complex prompts. The processor evaluates them from the inside out.

-   **Example**: `a {{red|black}__animal__|__color__ __animal__}`
-   **Explanation**: This gives a 50% chance of a `red` or `black` animal (e.g., `a red cat`), and a 50% chance of a random color and a random animal (e.g., `a blue dog`).

### Comments and Whitespace

To improve the readability of complex prompts, you can add comments and format your wildcards over multiple lines.

-   **Example**:
    ```
    A diamond ring set on a {
        {rose|yellow|white} gold   # you can also add comments
        | platinum                 # which will be ignored by the parser
    } band
    ```
-   **Possible Output**: `A diamond ring set on a rose gold band`

### Tag Extraction

This feature allows you to define special tags in your prompt that will be extracted and processed separately. The tags and their content are removed from the main prompt, allowing you to isolate parts of your prompt for other uses, such as feeding them into other nodes.

-   **Syntax**: You define the tag delimiters in the `tag_extraction_tags` input field. For example, `[],**` would tell the node to look for content inside `[square brackets]` and `*asterisks*`.
-   **Wildcard Compatibility**: Wildcards work inside the extracted tags! The content is processed with the same seed as the main prompt.
-   **Invalid Characters**: The characters `( ) { } |` cannot be used as tag delimiters.

-   **Example Workflow**:
    1.  **`wildcard_string` input**:
        ```
        A beautiful landscape, [photo by __artist__], style <{realistic|painterly}>
        ```
    2.  **`tag_extraction_tags` input**:
        ```
        [],<>
        ```
    3.  **Processing Steps**:
        - The node finds `[photo by __artist__]` and `<{realistic|painterly}>`.
        - It removes them from the main string, leaving: `A beautiful landscape, , style `
        - It processes the content of the first tag: `photo by __artist__` might become `photo by Ansel Adams`.
        - It processes the content of the second tag: `{realistic|painterly}` will become either `realistic` or `painterly`.
    4.  **Outputs**:
        -   **`processed_text`**: `A beautiful landscape, , style `
        -   **`extracted_tags_string`**: `photo by Ansel Adams|realistic` (assuming `__artist__` resolved to `Ansel Adams` and `{...}` to `realistic`)
        -   **`extracted_tags_list`**: `['photo by Ansel Adams', 'realistic']`
        -   **`raw_tags_string`**: `[photo by Ansel Adams]<{realistic}>` (Note: wildcards inside the tags are resolved)
        -   **`raw_tags_list`**: `['[photo by Ansel Adams]', '<_io.TextIOWrapper name='C:\Users\MNeMiC\Desktop\New Folder\ComfyUI-mnemic-nodes\README_WILDCARD.md' mode='r' encoding='utf-8'>']`

This allows you to, for example, route the artist's name or a chosen style to another part of your workflow, while ensuring it doesn't appear in the final prompt sent to the sampler.

---

## Utility Nodes

These nodes are included in the Mnemic Nodes pack and are designed to work well with the Wildcard Processor for advanced string manipulation.

### String Text Splitter

This node is perfect for breaking up a string into multiple parts based on a delimiter. It's especially useful for handling the `extracted_tags_string` output from the Wildcard Processor, which is joined by `|`.

-   **Inputs**:
    -   `input_string`: The text to split (e.g., `item1|item2|item3`).
    -   `delimiter`: The character to split on (e.g., `|`).
-   **Outputs**:
    -   `first_chunk`: The part of the string before the *first* delimiter (e.g., `item1`).
    -   `remainder`: The rest of the string after the *first* delimiter (e.g., `item2|item3`).
    -   `chunk_list`: A list containing all the parts of the split string (e.g., `['item1', 'item2', 'item3']`).

### String Text Extractor

Use this node to pull out all occurrences of text that are enclosed by a specific pair of characters.

-   **Inputs**:
    -   `input_string`: The text to search within.
    -   `delimiters`: The pair of characters to use as delimiters (e.g., `[]`, `**`).
-   **Outputs**:
    -   `extracted_text`: The content found inside the *first* pair of delimiters.
    -   `remainder_text`: The original text with the first extracted part (and its delimiters) removed.
    -   `extracted_list`: A list of all items found between any of the delimiter pairs in the string.
