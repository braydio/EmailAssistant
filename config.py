
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
IMPORTANT_DIR = os.getenv("IMPORTANT_DIR", os.path.expanduser("~/.mail/Gmail/Important/new"))
SENT_DIR = os.getenv("SENT_DIR", os.path.expanduser("~/.mail/Gmail/Sent"))
FROMGPT_DIR = os.getenv("FROMGPT_DIR", os.path.expanduser("~/.mail/Gmail/FromGPT"))

# LLM Configuration
USE_LOCAL_LLM = "true"

LOCAL_AI_BASE_URL = os.getenv("LOCAL_AI_URL")
# The EverythingLLM API endpoint (e.g., http://192.168.1.239:3001/api/v1)
ANYTHING_API_URL = os.getenv("ANYTHING_API_URL")
ANYTHING_API_KEY = os.getenv("ANYTHING_API_KEY")

