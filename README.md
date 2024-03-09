# Nodes
This is a node-collection for ComfyUI. I will share whatever reasonable thing I create here.

## Save Text File
This is a copy and refactor from the Save Text File-node from the https://github.com/YMC-GitHub/ymc-node-suite-comfyui pack. I needed it to provide an output file for ease of use, so I updated it to do so.
The bottom pin outputs both the input text, but also the delimiter and the padded number. This can be useful to name files and write to text-files for automatic captioning.
![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/ae544486-feba-4a82-a560-59998902f286)

## Generate Negative Prompt
This is a node that loads a GPT2 text inference model with the purpose of inputting a positive prompt, and outputting a negative prompt.

![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/fcb3e8cc-30ec-4f56-838d-777657aee90b)

![311445827-6b7614e6-2510-4b02-8696-8a6d7e1c59d3](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/a3decef7-917f-4a98-beef-66dd403bca23)

> [!IMPORTANT]
> Installation step: Download the from my [weights.pt](https://huggingface.co/mnemic/NegativePromptGenerator/blob/main/weights.pt) from my [huggingface](https://huggingface.co/mnemic/NegativePromptGenerator/tree/main).
>
> Place the weights.pt file without renaming it, inside this folder in your comfy setup:
>
> `\ComfyUI\custom_nodes\ComfyUI-mnemic-nodes\nodes\negativeprompt`
>
> It should now look something like this:
>
> ![image](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/8deb9cba-2800-4ab9-a391-832661bda7bd)

For further reading, checkout the [project github](https://github.com/MNeMoNiCuZ/NegativePromptGenerator).
