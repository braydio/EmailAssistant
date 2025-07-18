# manual_review.py
import os
import shutil
import json
import subprocess
from datetime import datetime
from display import console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from utils import parse_email, move_message_to_trash_via_imap
from config import (
    MAIN_INBOX,
    ARCHIVE_DIR,
    FOLLOWUP_DIR,
    IMPORTANT_DIR,
    TRASH_DIR,
    REMOTE_USER,
    REMOTE_HOST,
    REMOTE_PATH,
)
from embedding import send_embedding


def move_to_trash_via_maildir(email_file):
    src = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src):
        console.print(f"[red]Skip: file not found → {src}[/red]")
        return

    success = move_message_to_trash_via_imap(src)
    if not success:
        console.print(f"[red]IMAP deletion failed → skipping local move for {email_file}[/red]")
        return

    if not os.path.exists(src):
        console.print(f"[red]File already removed by IMAP: {email_file}[/red]")
        return

    try:
        dest_dir = os.path.join(TRASH_DIR, "cur")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(src, os.path.join(dest_dir, email_file))
        console.print(f"[red]Email moved to trash:[/red] {email_file}")
    except Exception as e:
        console.print(f"[bold red]Error moving to trash {email_file}: {e}[/bold red]")



def manual_review_process(num_emails):
    inbox_files = [
        f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    emails_to_review = inbox_files[:num_emails]
    review_log = []

    for email_file in emails_to_review:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)

        table = Table(title=f"Review: {email_file}", show_lines=True)
        table.add_column("Field", style="bold")
        table.add_column("Details", style="cyan")
        table.add_row("From", sender)
        table.add_row("Subject", subject)
        table.add_row("Date", date_str)
        console.print(table)

        console.print("1: REPLY   2: DELETE   3: REVIEW   4: ARCHIVE   5: IMPORTANT")
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4", "5"], default="3")

        actions = {
            "1": "REPLY",
            "2": "DELETE",
            "3": "REVIEW",
            "4": "ARCHIVE",
            "5": "IMPORTANT",
        }
        chosen = actions[choice]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review_log.append(
            {
                "email_file": email_file,
                "sender": sender,
                "subject": subject,
                "date": date_str,
                "action": chosen,
                "timestamp": timestamp,
            }
        )

        if chosen == "DELETE":
            move_to_trash_via_maildir(email_file)
        elif chosen == "ARCHIVE":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, email_file))
        elif chosen == "REVIEW":
            os.makedirs(FOLLOWUP_DIR, exist_ok=True)
            shutil.move(file_path, os.path.join(FOLLOWUP_DIR, email_file))
        elif chosen == "IMPORTANT":
            os.makedirs(IMPORTANT_DIR, exist_ok=True)
            shutil.move(file_path, os.path.join(IMPORTANT_DIR, email_file))
        # REPLY only logs; actual send is separate

    log_file = "manual_review_log.json"
    with open(log_file, "w") as f:
        json.dump(review_log, f, indent=2)

    subprocess.run(
        [
            "scp",
            log_file,
            f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/manual_review_log.json",
        ],
        check=True,
    )
    send_embedding("custom-documents/manual_review_log.json")


if __name__ == "__main__":
    num = IntPrompt.ask("Number to review", default=0)
    if num > 0:
        manual_review_process(num)
