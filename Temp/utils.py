
import re
import logging
from email import message_from_file
from email.policy import default
import subprocess
from gpt_api import log_gpt_request

def format_email_body(body):
    # Remove quoted text (replies, forwards)
    body = re.sub(r'(>.*\n)+', '', body)

    # Remove long greetings and disclaimers
    body = re.sub(r'(?i)(cheers|best regards|sent from my|--|disclaimer).*$', '', body)

    # Remove URLs and "view in browser" links
    body = re.sub(r'http[s]?://\S+', '', body)
    body = re.sub(r'(?i)(view in browser|click here|trouble viewing|manage preferences).*$', '', body)

    # Remove headers or promotional text
    body = re.sub(r'(?i)(subject to terms and conditions|privacy policy|unsubscribe).*$', '', body)

    # Remove multiple newlines/whitespace
    body = re.sub(r'\n+', '\n', body).strip()

    # Truncate the body
    max_length = 600  # Adjusted to 600 characters
    if len(body) > max_length:
        body = body[:max_length] + "\n[Content Truncated...]"

    return body
def parse_email(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        msg = message_from_file(f, policy=default)
        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown Sender")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        formatted_body = format_email_body(body)
        return subject, sender, formatted_body

def send_notification(subject, sender, recommendation):
    subprocess.run(["notify-send", "New Email Recommendation", f"From: {sender}\nSubject: {subject}\nAction: {recommendation}"])
