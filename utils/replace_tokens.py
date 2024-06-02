import socket
import re
import datetime

def replace_tokens(string, custom_tokens=None):
    tokens = {
        '[hostname]': socket.gethostname()
    }
    if custom_tokens:
        tokens.update(custom_tokens)

    for token, value in tokens.items():
        string = string.replace(token, value)

    time_format_pattern = r'\[time\((.*?)\)\]'
    matches = re.findall(time_format_pattern, string)
    for match in matches:
        time_token = f'[time({match})]'
        formatted_time = datetime.datetime.now().strftime(match)
        string = string.replace(time_token, formatted_time)

    return string
