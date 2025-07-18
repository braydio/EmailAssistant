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
from config import USE_LOCAL_LLM, LOCAL_AI_BASE_URL
from display import console

# Shared console provided by display module

# Load environment variables from .env file
project_dir = os.path.dirname(__file__)
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)

username = os.getenv("WEBUI_USR")
password = os.getenv("WEBUI_PSWD")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key and not USE_LOCAL_LLM:
    raise ValueError(
        "OPENAI_API_KEY environment variable not set or failed to load from .env."
    )

gpt_request_log_path = os.path.join(project_dir, "gpt_requests.log")
TIMESTAMP = datetime.now()
WORKSPACE_SLUG = "emailgpt"


def count_tokens(prompt, model="gpt-4o-mini"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))


def log_gpt_request(
    prompt, api_response, token_count, log_file_path="gpt_requests.log"
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    model_used = api_response.get("model", "Unknown Model")
    total_tokens = api_response.get("usage", {}).get("total_tokens", "Unknown")
    log_entry = (
        "\n=== GPT Interaction ===\n"
        f"Timestamp           : {timestamp}\n"
        f"Model               : {model_used}\n"
        f"Request Tokens      : {token_count}\n"
        f"Total Tokens Used   : {total_tokens}\n\n"
        "--- PROMPT START ---\n"
        f"{prompt}\n"
        "--- PROMPT END ---\n\n"
        "--- RESPONSE START ---\n"
        f"{json.dumps(api_response, indent=2)}\n"
        "--- RESPONSE END ---\n"
        "=== END OF GPT INTERACTION ===\n\n"
    )
    try:
        with open(gpt_request_log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        logging.error(f"Error writing GPT log entry: {e}")


def call_local_embedding(text):
    try:
        url = f"{LOCAL_AI_BASE_URL}/v1/embeddings"
        payload = {"model": "nomic-embed-text-v1.5", "input": text}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Local Embedding call failed: {e}")
        return {"error": str(e)}


def call_local_llm(prompt, model="mistral"):
    try:
        url = f"{LOCAL_AI_BASE_URL}/v1/chat/completions"
        console.print(
            f"[blue]Sending to URL LocalAI at: {url}\n Message: {prompt}[/blue]"
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2,
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Local LLM call failed: {e}")
        return {"error": str(e)}


def format_api_response(api_response):
    """
    Format the API response into a standard structure.
    For local LLM responses, we expect keys: textResponse or text.
    For OpenAI responses, we simply use the content of the message.
    """
    try:
        if isinstance(api_response, dict):
            if "choices" in api_response and "message" in api_response["choices"][0]:
                return {
                    "text": api_response["choices"][0]["message"]["content"].strip(),
                    "sources": [],
                    "close": False,
                }
            if "textResponse" in api_response:
                return {
                    "text": api_response["textResponse"].strip(),
                    "sources": [],
                    "close": False,
                }
        return {"text": json.dumps(api_response), "sources": [], "close": False}
    except Exception as e:
        logging.error(f"Error formatting API response: {e}")
        return {"text": None, "sources": [], "close": False, "error": str(e)}


def ask_gpt(prompt, model=""):  # Qwen2.5-Coder-7B-Instruct
    token_count = count_tokens(prompt, model=model)
    if USE_LOCAL_LLM:
        try:
            console.print(
                f"[bold green]Calling {model} at {LOCAL_AI_BASE_URL}[/bold green]"
            )
            api_response = call_local_llm(prompt, model=model)
            formatted_response = format_api_response(api_response)
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logging.error(f"Error during LocalAI call: {e}")
            return None
    else:
        if not openai.api_key:
            raise RuntimeError(
                "OpenAI API key is not set. Please check .env and environment variables."
            )
        try:
            api_response = openai.ChatCompletion.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            text = api_response["choices"][0]["message"]["content"]
            log_gpt_request(prompt, api_response, token_count)
            return format_api_response(text)
        except Exception as e:
            logging.error(f"Error during GPT API call: {e}")
            return None


def get_active_model():
    try:
        url = f"{LOCAL_AI_BASE_URL}/v1/internal/model/info"
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        return response.json().get("model_name", "mistral")
    except Exception as e:
        logging.warning(f"Could not get active model: {e}")
        return "Unknown"


def display_summary_report(response):
    """
    Displays a neat summary report of the GPT response.
    """
    console.print("\n[bold underline]Summary Report:[/bold underline]")
    if response.get("error"):
        console.print(f"[red]Error: {response.get('error')}[/red]")
        return

    # Main text output
    text = response.get("text", "").strip()
    if text:
        console.print(f"\n[bold]Response:[/bold]\n{text}\n")
    else:
        console.print("[yellow]No main response text provided.[/yellow]")

    # List the sources if any
    sources = response.get("sources", [])
    if sources:
        console.print("[bold]Sources:[/bold]")
        for i, source in enumerate(sources, start=1):
            console.print(f"{i}. {source}")
    else:
        console.print("[italic]No sources available.[/italic]")


def interactive_acceptance(response):
    """
    Allows the user to interactively accept all results or select specific entries.
    Returns a list of accepted items.
    """
    accepted_results = []

    # Accept the main response text if present
    main_text = response.get("text", "").strip()
    if main_text:
        console.print("\n[bold]Main Response:[/bold]")
        console.print(main_text)

    # Accept sources individually if available
    sources = response.get("sources", [])
    if sources:
        console.print("\n[bold]Review the following sources:[/bold]")
        for i, source in enumerate(sources, start=1):
            console.print(f"{i}. {source}")
        choice = console.input(
            "\nAccept all sources? (Y/n) or type numbers separated by comma: "
        ).strip()
        if choice.lower() in ["y", "yes", ""]:
            accepted_results = sources
        else:
            # Process specific numbers input
            try:
                indices = [
                    int(x.strip()) for x in choice.split(",") if x.strip().isdigit()
                ]
                accepted_results = [
                    sources[i - 1] for i in indices if 0 < i <= len(sources)
                ]
            except Exception as e:
                console.print(
                    f"[red]Invalid input. No sources accepted due to error: {e}[/red]"
                )
    else:
        console.print("[italic]No additional sources to review.[/italic]")

    # Return a dictionary with the accepted main text and the accepted sources
    accepted = {"main_text": main_text, "accepted_sources": accepted_results}
    console.print("\n[bold green]Accepted Results:[/bold green]")
    console.print(json.dumps(accepted, indent=2))
    return accepted


# Example usage:
if __name__ == "__main__":
    main()
