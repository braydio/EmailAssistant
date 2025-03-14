
# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

# Email directories and sender configuration
MAIN_INBOX = os.getenv("MAIN_INBOX", os.path.expanduser("~/.mail/Gmail/All/new"))
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", os.path.expanduser("~/.mail/Gmail/Archive"))
FOLLOWUP_DIR = os.getenv("FOLLOWUP_DIR", os.path.expanduser("~/.mail/Gmail/FollowUp"))
SPAM_DIR = os.getenv("SPAM_DIR", os.path.expanduser("~/.mail/Gmail/Spam"))
TRASH_DIR = os.getenv("TRASH_DIR", os.path.expanduser("~/.mail/Gmail/Trash"))
SENT_EMAIL = os.getenv("SENT_EMAIL", "chaffee.brayden@gmail.com")

# Additional directories for mail rules
IMPORTANT_DIR = os.getenv("IMPORTANT_DIR", os.path.expanduser("~/.mail/Gmail/Important"))
SENT_DIR = os.getenv("SENT_DIR", os.path.expanduser("~/.mail/Gmail/Sent"))
FROMGPT_DIR = os.getenv("FROMGPT_DIR", os.path.expanduser("~/.mail/Gmail/FromGPT"))

# LLM Configuration
# LOCAL_WEBUI_URL = os.getenv("LOCAL_WEBUI_URL", "http://localhost:5000/api/chat")
# USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
USE_LOCAL_LLM = "true"
LOCAL_WEB_UI_URL = os.getenv("LOCAL_WEB_UI_URL")  # e.g., "http://192.168.1.68:7860/v1/completions"

