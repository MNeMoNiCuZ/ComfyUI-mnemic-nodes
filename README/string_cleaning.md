# 🧹 String Cleaning
This node helps you quickly clean up and format strings by letting you remove leading or trailing spaces, periods, commas, or custom text, as well as removing linebreaks, or replacing them with a period.
- `input_string`: Your input string. Use [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) for looping through a list of strings.
- `collapse_sequential_spaces`: Collapses sequential spaces (" ") in a string into one.
- `strip_leading_spaces`: Removes any leading spaces from each line of the input string.
- `strip_trailing_spaces`: Removes any trailing spaces from each line of the input string.
- `strip_leading_symbols`: Removes leading punctuation symbols (, . ! ? : ;) from each line of the input string.
- `strip_trailing_symbols`: Removes leading punctuation symbols (, . ! ? : ;) from each line of the input string.
- `strip_inside_tags`: Removes any tags and the characters inside. <> would strip out anything like `<html>` or `</div>`, including the `<` and `>`
- `strip_newlines`: Removes any linebreaks in the input string.
- `replace_newlines_with_period_space`: Replaces any linebreaks in the input string with a ". ". If multiple linebreaks are found in a row, they will be replaced with a single ". ".
- `strip_leading_custom`: Removes any leading characters, words or symbols from each line of the input string. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `strip_trailing_custom`: Removes any trailing characters, words or symbols from each line of the input string. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `strip_all_custom`: Removes any characters, words or symbols found anywhere in the text. One entry per line. Space (" ") is supported. Will be processed in order, so you can combine multiple lines. Does not support linebreak removal.
- `multiline_find`: Find and replace for multiple entries. Will be processed in order.
- `multiline_replace`: Find and replace for multiple entries. Will be processed in order.

---
### Remove \<think\> tags
![image](https://github.com/user-attachments/assets/fe120033-c6c8-4ea6-a204-a8dbb270a6a9)

---

### Clean up HTML
![image](https://github.com/user-attachments/assets/3d622652-5e49-41f0-9f9b-4aabcdd978ac)

---

### Make a salad
![image](https://github.com/user-attachments/assets/ba7678d4-d027-42cb-9330-b62de1a26a36)

---

### Work on your novel
![image](https://github.com/user-attachments/assets/c5a250f8-2aee-43c3-9394-f5a728e68a91)
