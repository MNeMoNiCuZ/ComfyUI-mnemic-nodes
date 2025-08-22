# ✨📝 Groq ALM API

[Groq Speech Documentation](https://console.groq.com/docs/speech-text)

This node makes an API call to groq with an attached audio file and then uses Audio Language Models to transcribe the audio and return the text in different output formats.

The model `distil-whisper-large-v3-en` only supports the language `en`.
The model `whisper-large-v3` supports the languages listed below. It can also be left empty, but this provides worse results than running the model locally.

> [!NOTE]
> The presets / prompt do very little. They are meant to help you guide the output, but I don't get any relevant results.

You can convert the `file_path` to input to use the [Get File Path](https://github.com/MNeMoNiCuZ/ComfyUI-mnemic-nodes/edit/main/README.md#-get-file-path) node to find your files.


### Supported Languages
[https://www.wikiwand.com/en/articles/List_of_ISO_639_language_codes](https://www.wikiwand.com/en/articles/List_of_ISO_639_language_codes)
> is tg uz zh ru tr hi la tk haw fr vi cs hu kk he cy bs sw ht mn gl si mg sa es ja pt lt mr fa sl kn uk ms ta hr bg pa yi fo th lv ln ca br sq jv sn gu ba te bn et sd tl ha de hy so oc nn az km yo ko pl da mi ml ka am tt su yue nl no ne mt my ur ps ar id fi el ro as en it sk be lo lb bo sv sr mk eu

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `.env` file. A template file is provided and can be renamed to `.env` for use.

Currently, the Groq API can be used for free, with very friendly and generous [rate limits](https://console.groq.com/docs/rate-limits).

### Example: Transcribe meeting notes

![image](https://github.com/user-attachments/assets/4b9d2e31-96df-462e-bc18-eba6e381fa34)

-------------------------------

### Example: Generate image based on voice description or a story

![image](https://github.com/user-attachments/assets/926a6086-dccc-47dd-9f3b-86326976a62d)


-------------------------------

### Example: Transcribe song lyrics

![image](https://github.com/user-attachments/assets/2ec34e49-fbea-465a-9653-6bc1fbb34a13)

-------------------------------

### Karaoke?
You can use this to generate files to use in a [Karaoke app](https://github.com/MNeMoNiCuZ/whisper-karaoke). 

![image](https://github.com/user-attachments/assets/e4d7160b-90ab-4630-8568-2a65b7a79575)
