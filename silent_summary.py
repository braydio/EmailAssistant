# silent_summary.py
import os
import json
import subprocess
from datetime import datetime
from summarize import bulk_summarize_and_process_silent
from config import MAIN_INBOX
from utils import parse_email

summary_file_path = os.path.expanduser("~/.cache/email_summary_log.json")

def generate_email_snapshot():
    summary = []
    try:
        email_files = [
            f for f in os.listdir(MAIN_INBOX)
            if os.path.isfile(os.path.join(MAIN_INBOX, f))
        ]
        for f in email_files:
            subject, sender, _, date_str, _ = parse_email(os.path.join(MAIN_INBOX, f))
            summary.append({
                "file": f,
                "subject": subject,
                "sender": sender,
                "date": date_str
            })
    except Exception as e:
        summary.append({"error": str(e)})

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "remaining_inbox": summary
    }

    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
    with open(summary_file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return len(summary)

def send_notification(count):
    try:
        summary_text = f"{count} emails remain in inbox."
        subprocess.run([
            "notify-send", "-u", "low", "-a", "Email Assistant",
            "󰶊 Silent Email Summary Complete", summary_text
        ])
    except Exception as e:
        print(f"Notification failed: {e}")

if __name__ == "__main__":
    bulk_summarize_and_process_silent()
    count = generate_email_snapshot()
    send_notification(count)

