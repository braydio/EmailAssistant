# embedding.py
import requests
import logging
from config import ANYTHING_API_URL, ANYTHING_API_KEY

WORKSPACE_SLUG = "emailgpt"

def send_embedding(log_data):
    """
    Sends log data to the EverythingLLM /v1/embed endpoint for the 'emailgpt' workspace.
    log_data should be a JSON-serializable object.
    """
    embed_url = f"{ANYTHING_API_URL}/v1/workspace/{WORKSPACE_SLUG}/update-embeddings"

    headers = {
        'Authorization': f'Bearer {ANYTHING_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "adds": ["manual_review_log.json"],
        "deletes": []
    }
    try:
        response = requests.post(embed_url, headers=headers, json=payload)
        if response.status_code == 200:
            print("Embedding sent successfully.")
            return response.json()
        else:
            print(f"Embedding request failed with status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error sending embedding: {e}")
        return None
