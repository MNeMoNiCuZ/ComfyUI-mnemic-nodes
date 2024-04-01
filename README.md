# Nodes for ComfyUI

This repository hosts a collection of nodes developed for ComfyUI. It aims to share useful components that enhance the functionality of ComfyUI projects.

## Save Text File Node

This node is adapted and enhanced from the Save Text File node found in the [YMC GitHub ymc-node-suite-comfyui pack](https://github.com/YMC-GitHub/ymc-node-suite-comfyui). It was modified to output a file for easier usability. The output pin now includes the input text along with a delimiter and a padded number, offering a versatile solution for file naming and automatic text file generation for captions.

![Save Text File Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/ae544486-feba-4a82-a560-59998902f286)

## Generate Negative Prompt Node

This node utilizes a GPT-2 text inference model to generate a negative prompt that is supposed to enhance the aspects of the positive prompt.

![Generate Negative Prompt Node](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/fcb3e8cc-30ec-4f56-838d-777657aee90b)

![Generated Negative Prompt Example](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/a3decef7-917f-4a98-beef-66dd403bca23)

> [!IMPORTANT]
> **Installation Step:**
> Download the [weights.pt file](https://huggingface.co/mnemic/NegativePromptGenerator/blob/main/weights.pt) from the project's [Hugging Face repository](https://huggingface.co/mnemic/NegativePromptGenerator/tree/main).
>
> Place the `weights.pt` file in the following directory of your ComfyUI setup without renaming it:
> ```
> \ComfyUI\custom_nodes\ComfyUI-mnemic-nodes\nodes\negativeprompt
> ```
> The directory should resemble the following structure:
>
> ![Installation Directory](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/assets/60541708/8deb9cba-2800-4ab9-a391-832661bda7bd)

For additional information, please visit the [project's GitHub page](https://github.com/MNeMoNiCuZ/NegativePromptGenerator).
