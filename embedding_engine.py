"""Utilities for generating text embeddings.

This module provides helpers to obtain embeddings from either OpenAI or a
locally hosted model. The choice is controlled by the ``USE_LOCAL_LLM`` flag in
``config.py``.
"""

import os
import requests
import logging
import openai
from dotenv import load_dotenv
from config import USE_LOCAL_LLM, LOCAL_AI_BASE_URL

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def embed_with_openai(text):
    """Return an embedding for ``text`` using OpenAI."""

    try:
        response = openai.Embedding.create(model="text-embedding-3-small", input=text)
        return response["data"][0]["embedding"]
    except Exception as e:
        logging.error(f"OpenAI embedding failed: {e}")
        return None


def embed_with_local_model(text):
    """Return an embedding for ``text`` using a locally hosted model."""

    try:
        url = f"{LOCAL_AI_BASE_URL}/v1/embeddings"
        payload = {"model": "nomic-embed-text-v1.5", "input": text}
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as e:
        logging.error(f"Local embedding failed: {e}")
        return None


def embed_text(text):
    """Embed ``text`` using the configured provider."""

    if USE_LOCAL_LLM:
        return embed_with_local_model(text)
    return embed_with_openai(text)


def embed_file_as_text(filepath):
    """Embed the contents of ``filepath`` as plain text."""

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return embed_text(content)
    except Exception as e:
        logging.error(f"Failed to embed file {filepath}: {e}")
        return None
