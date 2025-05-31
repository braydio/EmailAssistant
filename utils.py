import os
import re
import logging
import json
import subprocess
import imaplib
from bs4 import BeautifulSoup
from email import message_from_file
from email.policy import default
from config import IMAP_HOST, IMAP_USER, IMAP_PASS
from rich.console import Console

console = Console()
RULES_FILE = "filter_rules.json"


def format_email_body(body):
    if "<html" in body.lower():
        soup = BeautifulSoup(body, "html.parser")
        body = soup.get_text(separator="\n")
    body = re.sub(r"(>.*\n)+", "", body)
    body = re.sub(r"http[s]?://\S+", "", body)
    body = re.sub(
        r"(?i)(view in browser|unsubscribe|privacy policy|manage preferences|click here|trouble viewing).*$",
        "",
        body,
        flags=re.MULTILINE,
    )
    body = re.sub(
        r"(?i)(cheers|best regards|sent from my|disclaimer).*$",
        "",
        body,
        flags=re.MULTILINE,
    )
    body = re.sub(r"\n+", "\n", body).strip()
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
        notification_msg = f"{subject} | Action: {recommendation}"
        subprocess.run(
            ["notify-send", "Email Action Recommended", notification_msg, "-t", "1000"],
            check=True,
        )
        console.print(f"[green]Notification sent:[/green] {notification_msg}")
    except Exception as e:
        console.print(f"[red]Notification failed:[/red] {e}")


def fuzzy_select_email(email_info):
    lines = []
    for idx, sender, subject, email_file, date_str in email_info:
        lines.append(
            f"{idx}. From: {sender} | Subject: {subject} | Date: {date_str} | File: {email_file}"
        )
    try:
        process = subprocess.Popen(
            ["fzf"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        input_data = "\n".join(lines)
        output, _ = process.communicate(input=input_data)
        if output:
            for part in output.strip().split(" | "):
                if part.startswith("File: "):
                    return part.replace("File: ", "").strip()
    except Exception as e:
        console.print(f"[red]Fuzzy selection failed:[/red] {e}")
    return None


def load_filter_rules():
    """Load all filter rules from a JSON array in RULES_FILE."""
    if not os.path.exists(RULES_FILE):
        return []
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing {RULES_FILE}: {e}[/red]")
        return []


def record_filter_rule(rule_dict):
    """Append a rule dict into RULES_FILE JSON array."""
    rules = load_filter_rules()
    rules.append(rule_dict)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
    console.print(f"[green]Wrote new rule to {RULES_FILE}[/green]")


def matches_filter_rule(email_text, rule):
    pattern = rule.get("pattern")
    action = rule.get("action")
    if pattern and re.search(pattern, email_text, re.IGNORECASE):
        return action.upper()
    return None


def move_message_to_trash_via_imap(file_path):
    """
    Attempts IMAP-based deletion. Falls back to local trash if it fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            msg = message_from_file(f, policy=default)
            msg_id = msg.get("Message-ID")

        if not msg_id:
            raise ValueError("Missing Message-ID header")

        assert IMAP_USER and IMAP_PASS, "Missing IMAP credentials"

        M = imaplib.IMAP4_SSL(IMAP_HOST)
        M.login(IMAP_USER, IMAP_PASS)
        M.select("INBOX")

        typ, data = M.search(None, "HEADER", "Message-ID", msg_id)
        if typ != "OK" or not data or not data[0]:
            raise ValueError("Message not found via IMAP")

        for num in data[0].split():
            M.copy(num, "[Gmail]/Trash")
            M.store(num, "+FLAGS", "\\Deleted")
        M.expunge()
        M.logout()
        console.print(f"[green]Message {msg_id} moved to Trash via IMAP.[/green]")
        return True
    except Exception as e:
        # Fallback to local trash move
        from config import TRASH_DIR

        try:
            os.makedirs(os.path.join(TRASH_DIR, "cur"), exist_ok=True)
            fallback_dest = os.path.join(TRASH_DIR, "cur", os.path.basename(file_path))
            os.rename(file_path, fallback_dest)
            console.print(
                f"[yellow]IMAP failed, moved locally to trash: {file_path}[/yellow]"
            )
        except Exception as e2:
            console.print(f"[red]Failed fallback move: {e2}[/red]")
        return False
