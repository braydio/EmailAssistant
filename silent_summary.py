#!/usr/bin/env python3
import os
import json
import subprocess
import threading
from datetime import datetime
import time as systime
import json.decoder
from summarize import bulk_summarize_and_process_silent
from config import MAIN_INBOX
from utils import parse_email

summary_file_path = os.path.expanduser("~/.cache/email_summary_log.json")
status_path = os.path.expanduser("~/Projects/GPTMail/email_status.json")


def update_status(icon, text="", tooltip="", processing=False):
    status_class = "processing" if processing else "idle"
    data = {
        "text": f"{icon} {text}".strip(),
        "tooltip": tooltip,
        "processing": processing,
        "class": status_class,
    }
    tmp = f"{status_path}.tmp"
    try:
        json_data = json.dumps(data)
        json.loads(json_data)  # sanity check
        with open(tmp, "w") as f:
            f.write(json_data)
        os.replace(tmp, status_path)
    except json.decoder.JSONDecodeError as e:
        print(f"[status] JSON encoding error: {e}")


def start_icon_animation(stop_event):
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop_event.is_set():
        icon = spinner[i % len(spinner)]
        update_status(f"{icon} ", "", "Processing emails")
        i += 1
        systime.sleep(0.1)


def generate_email_snapshot():
    summary = []
    try:
        email_files = [
            f
            for f in os.listdir(MAIN_INBOX)
            if os.path.isfile(os.path.join(MAIN_INBOX, f))
        ]
        for f in email_files:
            subject, sender, _, date_str, _ = parse_email(os.path.join(MAIN_INBOX, f))
            summary.append(
                {"file": f, "subject": subject, "sender": sender, "date": date_str}
            )
    except Exception as e:
        summary.append({"error": str(e)})

    snapshot = {"timestamp": datetime.now().isoformat(), "remaining_inbox": summary}

    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
    with open(summary_file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return len(summary)


def send_notification(count):
    try:
        summary_text = f"{count} emails remain in inbox."
        subprocess.run(
            [
                "notify-send",
                "-u",
                "low",
                "-a",
                "Email Assistant",
                "󰶊 Silent Email Summary Complete",
                summary_text,
            ]
        )
    except Exception as e:
        print(f"Notification failed: {e}")


if __name__ == "__main__":
    stop_event = threading.Event()
    thread = threading.Thread(target=start_icon_animation, args=(stop_event,))
    thread.start()

    try:
        bulk_summarize_and_process_silent(num_emails=10, confirm_all=True)
        count = generate_email_snapshot()
        send_notification(count)
        update_status(
            "", f"{count}", f"{count} emails remain in inbox.", processing=False
        )
    finally:
        stop_event.set()
        thread.join()
