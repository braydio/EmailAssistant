
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env
project_dir = os.path.dirname(__file__)  # Get the directory where this file is located
env_path = os.path.join(project_dir, ".env")  # Path to the .env file
load_dotenv(env_path)  # Load the .env file

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set or failed to load from .env.")

# Logging setup for GPT requests
gpt_request_log_path = os.path.join(project_dir, "gpt_requests.log")

def log_gpt_request(prompt, token_count):
    with open(gpt_request_log_path, "a") as log_file:
        log_file.write(f"--- GPT Request ---\n")
        log_file.write(f"Token Count: {token_count}\n")
        log_file.write(f"Prompt Sent:\n{prompt}\n")
        log_file.write(f"--- End of Request ---\n\n")

def ask_gpt(prompt):
    log_gpt_request(prompt, len(prompt))
    
    # Make sure API key is not None before calling
    if not openai.api_key:
        raise RuntimeError("OpenAI API key is not set. Please check .env and environment variables.")
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']
