## ✨📷 Groq VLM API
> [!IMPORTANT]
> #### 2024-09-27 - Version 1.2.1
> Added new Llama 3.2 vision model to the list, but this model is not yet officially available. Once it is, this should automatically work.

[Groq Vision Documentation](https://console.groq.com/docs/vision)

This node makes an API call to groq with an attached image and then uses Vision Language Models to return a description of the image, or answer to a question about the image in text format.

### Setup
You need to manually enter your [groq API key](https://console.groq.com/keys) into the `.env` file. A template file is provided and can be renamed to `.env` for use.

Currently, the Groq API can be used for free, with very friendly and generous [rate limits](https://console.groq.com/docs/rate-limits).

### Restrictions
**Image Size Limit**: The maximum allowed size for a request containing an image URL as input is 20MB. Requests larger than this limit will return a 400 error.

**Request Size Limit (Base64 Enconded Images)**: The maximum allowed size for a request containing a base64 encoded image is 4MB. Requests larger than this limit will return a 413 error.

### Example: Custom prompt
![image](https://github.com/user-attachments/assets/783c85ea-cb3e-4338-903c-e8c9b30eaff3)

-------------------------------

### Example: Short Caption

![image](https://github.com/user-attachments/assets/e1c86199-1b1b-4e45-9203-f766bcc1f1ad)

-------------------------------

### Example: Medium Caption

![image](https://github.com/user-attachments/assets/804c38c9-5923-47fd-93a4-1716fff7508c)

-------------------------------

### Example: Long Caption

![image](https://github.com/user-attachments/assets/7cd027b3-a1df-48e3-a699-95d9a15350e9)

-------------------------------

### Example: Primary Color

![image](https://github.com/user-attachments/assets/b5e212f9-8d3f-47c5-8666-7762467cddc2)


-------------------------------
