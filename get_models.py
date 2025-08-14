"""Utility script to list available models on the local text generation server."""

import requests

from config import LOCAL_AI_BASE_URL

list_models_endpoint = f"{LOCAL_AI_BASE_URL}/v1/internal/model/info"

response = requests.get(list_models_endpoint)
print(response.json())
