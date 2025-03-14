# embedding.py
import requests
import logging
from config import ANYTHING_API_URL

def send_embedding(log_data):
    """
    Sends log data to the EverythingLLM /v1/embed endpoint for the 'emailgpt' workspace.
    log_data should be a JSON-serializable object.
    """
    embed_url = ANYTHING_API_URL.rstrip("/") + "/v1/embed"
    payload = {
        "workspace": "emailgpt",
        "data": log_data
    }
    try:
        response = requests.post(embed_url, json=payload)
        if response.status_code == 200:
            print("Embedding sent successfully.")
            return response.json()
        else:
            print(f"Embedding request failed with status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error sending embedding: {e}")
        return None
