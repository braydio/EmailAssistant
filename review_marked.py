# review_marked.py
import os
import shutil
from display import console
from rich.table import Table
from rich.prompt import Prompt
from utils import parse_email
from config import FOLLOWUP_DIR, ARCHIVE_DIR, IMPORTANT_DIR, TRASH_DIR
from draft_reply import generate_draft_reply


def move_to_trash_via_maildir(source_dir, email_file):
    src = os.path.join(source_dir, email_file)
    dest_dir = os.path.join(TRASH_DIR, "cur")
    os.makedirs(dest_dir, exist_ok=True)
    base = email_file.split(":", 1)[0]
    new_name = f"{base}:2,T"
    shutil.move(src, os.path.join(dest_dir, new_name))


def review_marked_emails():
    for email_file in os.listdir(FOLLOWUP_DIR):
        file_path = os.path.join(FOLLOWUP_DIR, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        table = Table(title=f"Email: {email_file}", show_lines=True)
        table.add_column("Field", style="bold")
        table.add_column("Value", style="cyan")
        table.add_row("From", sender)
        table.add_row("Subject", subject)
        table.add_row("Date", date_str)
        table.add_row("Body", body)
        console.print(table)

        console.print("1: Reply   2: Delete   3: Archive   4: Skip")
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="4")

        if choice == "1":
            generate_draft_reply(
                email_file=email_file, view_original=True, view_reply=True, send=True
            )
        elif choice == "2":
            move_to_trash_via_maildir(FOLLOWUP_DIR, email_file)
        elif choice == "3":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, email_file))
        # skip does nothing


def review_important_emails():
    for email_file in os.listdir(IMPORTANT_DIR):
        file_path = os.path.join(IMPORTANT_DIR, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        table = Table(title=f"Important Email: {email_file}", show_lines=True)
        table.add_column("Field", style="bold")
        table.add_column("Value", style="cyan")
        table.add_row("From", sender)
        table.add_row("Subject", subject)
        table.add_row("Date", date_str)
        table.add_row("Body", body)
        console.print(table)

        console.print("1: Reply   2: Delete   3: Archive   4: Skip")
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="4")

        if choice == "1":
            generate_draft_reply(
                email_file=email_file, view_original=True, view_reply=True, send=True
            )
        elif choice == "2":
            move_to_trash_via_maildir(IMPORTANT_DIR, email_file)
        elif choice == "3":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, email_file))
        # skip does nothing


if __name__ == "__main__":
    review_marked_emails()
