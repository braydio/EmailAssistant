"""Utility script to list available models on the local Ollama server."""

import requests

from config import OLLAMA_BASE_URL

list_models_endpoint = f"{OLLAMA_BASE_URL}/api/tags"

response = requests.get(list_models_endpoint)
print(response.json())
