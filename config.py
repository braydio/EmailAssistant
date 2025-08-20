"""Application configuration utilities.

This module centralizes environment configuration for the project. It loads
settings from a ``.env`` file when present and exposes constants used
throughout the codebase.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

# Email directories and sender configuration
MAIN_INBOX = os.getenv("MAIN_INBOX", os.path.expanduser("~/.mail/Gmail/AllMail/new"))
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", os.path.expanduser("~/.mail/Gmail/Archive"))
FOLLOWUP_DIR = os.getenv("FOLLOWUP_DIR", os.path.expanduser("~/.mail/Gmail/FollowUp"))
SPAM_DIR = os.getenv("SPAM_DIR", os.path.expanduser("~/.mail/Gmail/Spam"))
TRASH_DIR = os.getenv("TRASH_DIR", os.path.expanduser("~/.mail/Gmail/Trash"))
SENT_EMAIL = os.getenv("SENT_EMAIL", "chaffee.brayden@gmail.com")

# Additional directories for mail rules
IMPORTANT_DIR = os.getenv(
    "IMPORTANT_DIR", os.path.expanduser("~/.mail/Gmail/Important/new")
)
SENT_DIR = os.getenv("SENT_DIR", os.path.expanduser("~/.mail/Gmail/Sent"))
FROMGPT_DIR = os.getenv("FROMGPT_DIR", os.path.expanduser("~/.mail/Gmail/FromGPT"))

# IMAP configuration for server-side operations
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")

# LLM Configuration
LOCAL_AI_IP = os.getenv("LOCAL_AI_IP", "192.168.1.69")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
TEXTGEN_PORT = os.getenv("TEXTGEN_PORT", "5150")

# Whether to use a locally hosted language model
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() in {"1", "true", "yes"}

# Base URLs for local model servers
OLLAMA_BASE_URL = f"http://{LOCAL_AI_IP}:{OLLAMA_PORT}"
# Maintained for backward compatibility
LOCAL_AI_BASE_URL = OLLAMA_BASE_URL
ANYTHING_API_URL = os.getenv("ANYTHING_API_URL")
ANYTHING_API_KEY = os.getenv("ANYTHING_API_KEY")

# Embedding details
REMOTE_HOST = os.getenv("REMOTE_HOST")
REMOTE_USER = os.getenv("REMOTE_USER")
REMOTE_PATH = os.getenv("REMOTE_PATH")
