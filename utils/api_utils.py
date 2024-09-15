import requests
import json
import time

def make_api_request(data, headers, url, max_retries):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        print(f"Response status: {response.status_code}, Response body: {response.text}")
        if response.status_code == 200:
            try:
                response_json = json.loads(response.text)
                if 'choices' in response_json and response_json['choices']:
                    assistant_message = response_json['choices'][0]['message']['content']
                    print(f"Extracted message: {assistant_message}")
                    return assistant_message, True, "200 OK"
                else:
                    return "No valid response content found.", False, "200 OK but no content"
            except Exception as e:
                print(f"Error parsing response: {str(e)}")
                return "Error parsing JSON response.", False, "200 OK but failed to parse JSON"
        else:
            return "ERROR", False, f"{response.status_code} {response.reason}"
        time.sleep(2)
    return "Failed after all retries.", False, "Failed after all retries"

def load_prompt_options(prompt_files):
    prompt_options = {}
    for json_file in prompt_files:
        try:
            with open(json_file, 'r') as file:
                prompts = json.load(file)
                prompt_options.update({prompt['name']: prompt['content'] for prompt in prompts})
        except Exception as e:
            print(f"Failed to load prompts from {json_file}: {str(e)}")
    return prompt_options

def get_prompt_content(prompt_options, prompt_name):
    return prompt_options.get(prompt_name, "No content found for selected prompt")