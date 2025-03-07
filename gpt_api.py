import openai
import os
import json
import requests
import base64
import logging
import tiktoken
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

def count_tokens(prompt, model="gpt-4"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))

def log_gpt_request(prompt, api_response, token_count):
    with open(gpt_request_log_path, "a") as log_file:
        log_file.write(f"--- GPT Request ---\n")
        log_file.write(f"Token Count: {token_count}\n")
        log_file.write(f"Prompt Sent:\n{prompt}\n")
        log_file.write(f"--- GPT Response ---\n")
        log_file.write(f"{json.dumps(api_response, indent=2)}\n")
        log_file.write(f"--- End of GPT Interaction ---\n\n")

def get_token(username, password):
    # Example token generation using base64 encoding. Adjust as needed.
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return token

def call_local_webui(url, username, password, message):
    print(f"Not needed username, pswd: {username} {password}")
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
    """
    Extracts the response text from the API response.
    Assumes the local LLM returns a structure similar to:
    {
      "choices": [
         { "text": "Your generated reply...", ... }
      ],
      ...
    }
    """
    try:
        text = api_response["choices"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error formatting API response: {e}")
        text = None
    return text

def ask_gpt(prompt):
    token_count = count_tokens(prompt, model="gpt-4")
    if USE_LOCAL_LLM:
        try:
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
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            formatted_response = api_response['choices'][0]['message']['content']
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during GPT API call: {e}")
            return None
