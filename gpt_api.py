
# gpt_api.py
import openai
import os
import json
import requests
import base64
import logging
import tiktoken
from datetime import datetime
from dotenv import load_dotenv
from config import USE_LOCAL_LLM, LOCAL_WEB_UI_URL

# Load environment variables from .env file
project_dir = os.path.dirname(__file__)
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)

username = os.getenv("WEBUI_USR")
password = os.getenv("WEBUI_PSWD")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key and not USE_LOCAL_LLM:
    raise ValueError("OPENAI_API_KEY environment variable not set or failed to load from .env.")

# Log file for GPT requests and responses
gpt_request_log_path = os.path.join(project_dir, "gpt_requests.log")
TIMESTAMP = datetime.now()

def count_tokens(prompt, model="gpt-4o-mini"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))

def log_gpt_request(prompt, api_response, token_count, log_file_path="gpt_requests.log"):
    """
    Logs detailed information about GPT interactions to the specified log file.

    Args:
        prompt (str): The prompt sent to GPT.
        api_response (dict): The raw response object from GPT.
        token_count (int): Token count used in request.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    model_used = api_response.get("model", "Unknown Model")
    total_tokens = api_response.get("usage", {}).get("total_tokens", "Unknown")

    log_entry = (
        "\n=== GPT Interaction ===\n"
        f"Timestamp      : {timestamp}\n"
        f"Model: {model_used}\n"
        f"Request Tokens: {token_count}\n"
        f"Total Tokens Used: {total_tokens}\n\n"
        "--- PROMPT START ---\n"
        f"{prompt}\n"
        "--- PROMPT END ---\n\n"
        "--- RESPONSE START ---\n"
        f"{json.dumps(api_response, indent=2)}\n"
        "--- RESPONSE END ---\n"
        "=== END OF GPT INTERACTION ===\n"
        "\n"
    )

    try:
        with open(gpt_request_log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        logging.error(f"Error writing GPT log entry: {e}")

def get_token(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return token

def call_local_webui(url, username, password, message):
    payload = {
        "prompt": message,
        "max_tokens": 1000
    }
    response = requests.post(url, json=payload)
    print(response.json())
    if response.status_code != 200:
        raise Exception(f"Request failed with status code: {response.status_code}")
    return response.json()

def format_api_response(api_response):
    try:
        text = api_response["choices"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error formatting API response: {e}")
        text = None
    return text

def ask_gpt(prompt):
    token_count = count_tokens(prompt, model="gpt-4o-mini")
    if USE_LOCAL_LLM:
        try:
            print(f"Sending request to GPT at url: {LOCAL_WEB_UI_URL}")
            api_response = call_local_webui(LOCAL_WEB_UI_URL, username, password, prompt)
            formatted_response = format_api_response(api_response)
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during local web UI call: {e}")
            return None
    else:
        if not openai.api_key:
            raise RuntimeError("OpenAI API key is not set. Please check .env and environment variables.")
        try:
            api_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            formatted_response = api_response['choices'][0]['message']['content']
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during GPT API call: {e}")
            return None

