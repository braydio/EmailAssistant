"""Utility functions for interacting with language models.

This module provides helper functions for calling either OpenAI's hosted
models or a locally hosted Ollama server, depending on configuration.
"""

import openai
from openai import OpenAI
import os
import json
import requests
import logging
import tiktoken
import time
from datetime import datetime
from dotenv import load_dotenv
from config import USE_LOCAL_LLM, OLLAMA_BASE_URL
from rich.console import Console

# Setup rich console for pretty output
console = Console()

# Load environment variables from .env file
project_dir = os.path.dirname(__file__)
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)

username = os.getenv("WEBUI_USR")
password = os.getenv("WEBUI_PSWD")
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

if not API_KEY and not USE_LOCAL_LLM:
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
    prompt,
    api_response,
    token_count,
    elapsed_time,
    model_name=None,
    log_file_path="gpt_requests.log",
):
    """Log details of a model interaction for auditing and timing analysis."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    model_used = model_name or api_response.get("model", "Unknown Model")
    total_tokens = api_response.get("usage", {}).get("total_tokens", "Unknown")
    server_time_ns = api_response.get("total_duration")
    server_time_ms = (
        f"{server_time_ns / 1_000_000:.2f}" if server_time_ns else "Unknown"
    )
    log_entry = (
        "\n=== GPT Interaction ===\n"
        f"Timestamp           : {timestamp}\n"
        f"Model               : {model_used}\n"
        f"Request Tokens      : {token_count}\n"
        f"Total Tokens Used   : {total_tokens}\n"
        f"Elapsed Time (s)    : {elapsed_time:.3f}\n"
        f"Server Time (ms)    : {server_time_ms}\n\n"
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


def call_ollama_embedding(text, model="nomic-embed-text"):
    """Request embeddings from the local Ollama server."""
    try:
        url = f"{OLLAMA_BASE_URL}/v1/embeddings"
        payload = {"model": model, "input": text}
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Ollama embedding call failed: {e}")
        return {"error": str(e)}


def call_ollama_llm(prompt, model="llama3.1"):
    """Send a chat request to the local Ollama server."""
    try:
        url = f"{OLLAMA_BASE_URL}/v1/chat/completions"
        console.print(
            f"[blue]Sending to Ollama at: {url}\n Message: {prompt}[/blue]"
        )
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Ollama LLM call failed: {e}")
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
            if "message" in api_response and "content" in api_response["message"]:
                return {
                    "text": api_response["message"]["content"].strip(),
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


def ask_gpt(prompt, model=None):
    """Send a prompt to the configured language model and return a response."""

    if USE_LOCAL_LLM:
        model_to_use = model or get_active_model()
        token_count = count_tokens(prompt, model=model_to_use)
        try:
            console.print(
                f"[bold green]Calling {model_to_use} at {OLLAMA_BASE_URL}[/bold green]"
            )
            start = time.perf_counter()
            api_response = call_ollama_llm(prompt, model=model_to_use)
            elapsed = time.perf_counter() - start
            formatted_response = format_api_response(api_response)
            log_gpt_request(
                prompt, api_response, token_count, elapsed, model_to_use
            )
            return formatted_response
        except Exception as e:
            logging.error(f"Error during Ollama call: {e}")
            return None
    else:
        model_to_use = model or "gpt-4o-mini"
        token_count = count_tokens(prompt, model=model_to_use)
        if not API_KEY:
            raise RuntimeError(
                "OpenAI API key is not set. Please check .env and environment variables."
            )
        try:
            start = time.perf_counter()
            api_response = client.chat.completions.create(
                model=model_to_use, messages=[{"role": "user", "content": prompt}]
            )
            elapsed = time.perf_counter() - start
            api_dict = api_response.model_dump()
            log_gpt_request(
                prompt, api_dict, token_count, elapsed, model_to_use
            )
            return format_api_response(api_dict)
        except Exception as e:
            logging.error(f"Error during GPT API call: {e}")
            return None


def get_active_model():
    """Return the first available model reported by the local Ollama server."""
    try:
        url = f"{OLLAMA_BASE_URL}/v1/models"
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        models = response.json().get("data", [])
        if models:
            return models[0].get("id", "Unknown")
        return "Unknown"
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
