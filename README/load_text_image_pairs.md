## 🖼️+📝 Load Text-Image Pairs

Loads image and text pairs from a folder, or from separate inputs, and groups them together in a list.

This could be used to load and view datasets, or if you have a matching caption or description file to an image, or text generated in a workflow. Essentially you use this to pair up the data, and then you can step through it one by one, or all at once.

> [!IMPORTANT]
> To cycle through each input entry one by one in the list, you'll want to set the `seed` input to `increment`.

<img width="1646" height="982" alt="image" src="https://github.com/user-attachments/assets/5dfca806-2245-4c96-9e34-6216ec1609aa" />

-   **Inputs**:
    -   `image_input`: Image input override, has priority over path. Takes both single image and a list of images.
    -   `text_input`: Text input override, has priority over path. Takes both single string, or list of strings. The returned list will be the shorter of `image_input` and `text_input`.
    -   `seed`: Use this to control the starting index. Use the `increment` type to step through the images one by one each time you generate.
    -   `folder_path`: The path to the folder of text-image pairs
    -   `max_pair_count`: Limits the total number of outputs in the lists.
-   **Outputs**:
    -   `image_single_output`: The single image chosen by the index.
    -   `string_single_output`: The text matching the image above.
    -   `image_list_output`: All images in the chosen folder or input, limited by the `max_pair_count`.
    -   `max_pair_count`: A limit to the total number of image pairs in the list above.

You can also use the optional image + text manual inputs instead of paths. They have a higher priority if they are used.
<img width="2245" height="960" alt="image" src="https://github.com/user-attachments/assets/c285c150-dad2-4ca4-b475-c64cfb02ed24" />
