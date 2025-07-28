
import requests
import logging
from config import ANYTHING_API_URL, ANYTHING_API_KEY
from display import console

WORKSPACE_SLUG = "emailgpt"

def send_embedding(file_reference):
    """
    Sends a file reference to the EverythingLLM embedding endpoint for the 'emailgpt' workspace.
    
    Parameters:
        file_reference (str): A string representing the file path (relative to the custom documents folder)
                              e.g., "custom-documents/manual_review_log.json".
    
    The payload is built as:
    {
        "adds": [ <file_reference> ],
        "deletes": []
    }
    """
    embed_url = f"{ANYTHING_API_URL}/v1/workspace/{WORKSPACE_SLUG}/update-embeddings"

    headers = {
        'Authorization': f'Bearer {ANYTHING_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "adds": [file_reference],
        "deletes": []
    }
    try:
        response = requests.post(embed_url, headers=headers, json=payload)
        if response.status_code == 200:
            console.print("Embedding sent successfully.")
            return response.json()
        else:
            console.print(
                f"Embedding request failed with status code: {response.status_code}"
            )
            console.print(f"Response content: {response.content}")
            return None
    except Exception as e:
        logging.error(f"Error sending embedding: {e}")
        return None

