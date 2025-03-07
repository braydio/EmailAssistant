
from bs4 import BeautifulSoup
import re
import logging
from email import message_from_file
from email.policy import default
import subprocess

def format_email_body(body):
    # If body contains HTML, strip tags
    if "<html" in body.lower():
        soup = BeautifulSoup(body, "html.parser")
        body = soup.get_text(separator="\n")

    # Remove quoted replies and forwards
    body = re.sub(r'(>.*\n)+', '', body)

    # Remove URLs
    body = re.sub(r'http[s]?://\S+', '', body)

    # Remove common marketing phrases and footers
    body = re.sub(r'(?i)(view in browser|unsubscribe|privacy policy|manage preferences|click here|trouble viewing).*$', '', body, flags=re.MULTILINE)

    # Remove long greetings and disclaimers
    body = re.sub(r'(?i)(cheers|best regards|sent from my|disclaimer).*$', '', body, flags=re.MULTILINE)

    # Collapse multiple newlines
    body = re.sub(r'\n+', '\n', body).strip()

    # Truncate the body to avoid overloading GPT
    max_length = 1000
    if len(body) > max_length:
        body = body[:max_length] + "\n[Content Truncated...]"

    return body

def parse_email(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            msg = message_from_file(f, policy=default)
            subject = msg.get("Subject", "No Subject")
            sender = msg.get("From", "Unknown Sender")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
            formatted_body = format_email_body(body)
            # Extract and format the date header
            date_str = msg.get("Date", "Unknown Date")
            from email.utils import parsedate_to_datetime
            try:
                date_obj = parsedate_to_datetime(date_str)
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_date = date_str
                date_obj = None
            return subject, sender, formatted_body, formatted_date, date_obj
    except Exception as e:
        logging.error(f"Error parsing email {file_path}: {e}")
        return "Error", "Error", "", "Unknown Date", None

def send_notification(subject, sender, recommendation):
    try:
        # Set duration (-t) to 5000ms (5 seconds)
        subprocess.run(["notify-send", "-t", "5000", "New Email Recommendation", f"From: {sender}\nSubject: {subject}\nAction: {recommendation}"])
    except Exception as e:
        logging.error(f"Error sending notification: {e}")

def fuzzy_select_email(email_info):
    """
    Uses fzf to allow the user to select an email based on sender, subject, and date.
    """
    lines = []
    for idx, sender, subject, email_file, date_str in email_info:
        line = f"{idx}. From: {sender} | Subject: {subject} | Date: {date_str} | File: {email_file}"
        lines.append(line)
    try:
        process = subprocess.Popen(
            ["fzf"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        input_data = "\n".join(lines)
        output, _ = process.communicate(input=input_data)
        if output:
            parts = output.strip().split(" | ")
            for part in parts:
                if part.startswith("File: "):
                    selected_file = part.replace("File: ", "").strip()
                    return selected_file
    except Exception as e:
        print(f"Fuzzy selection failed: {e}")
    return None

def record_filter_rule(rule, file_path="filter_rules.txt"):
    """
    Appends a suggested filter rule to a file for later review.
    """
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(rule + "\n")
        print("Filter rule recorded:", rule)
    except Exception as e:
        logging.error(f"Error recording filter rule: {e}")

