
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

# Email directories and sender configuration
MAIN_INBOX = os.getenv("MAIN_INBOX", os.path.expanduser("~/.mail/Gmail/RecentInbox/new"))
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", os.path.expanduser("~/.mail/Gmail/Archive"))
FOLLOWUP_DIR = os.getenv("FOLLOWUP_DIR", os.path.expanduser("~/.mail/Gmail/FollowUp"))
SPAM_DIR = os.getenv("SPAM_DIR", os.path.expanduser("~/.mail/Gmail/Spam"))
SENT_EMAIL = os.getenv("SENT_EMAIL", "chaffee.brayden@gmail.com")

# LLM Configuration
# LOCAL_WEBUI_URL = os.getenv("LOCAL_WEBUI_URL", "http://localhost:5000/api/chat")
# USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
USE_LOCAL_LLM = "true"
LOCAL_WEB_UI_URL = "http://192.168.1.68:7860/v1/completions"
