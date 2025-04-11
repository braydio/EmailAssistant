
import os
import shutil
import json
import subprocess
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from utils import parse_email
from config import MAIN_INBOX, ARCHIVE_DIR, TRASH_DIR, FOLLOWUP_DIR, IMPORTANT_DIR
from embedding import send_embedding

console = Console()

def review_suggestions():
    """
    Legacy manual review process updated with Rich for styling.
    """
    inbox_path = MAIN_INBOX
    email_files = [
        os.path.join(inbox_path, f)
        for f in os.listdir(inbox_path)
        if os.path.isfile(os.path.join(inbox_path, f))
    ]
    if not email_files:
        console.print("[yellow]No new emails found.[/yellow]")
        return
    for email_file in email_files:
        subject, sender, _, date_str, _ = parse_email(email_file)
        table = Table(show_header=False)
        table.add_row("[cyan]From:[/cyan]", sender)
        table.add_row("[green]Date:[/green]", date_str)
        table.add_row("[magenta]Subject:[/magenta]", subject)
        console.print(table)
        action = Prompt.ask("Action (archive/delete/important/skip)", default="skip").strip().lower()
        if action == "archive":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            archive_path = os.path.join(ARCHIVE_DIR, os.path.basename(email_file))
            shutil.move(email_file, archive_path)
            console.print(f"[green]Email archived:[/green] {archive_path}")
        elif action == "delete":
            os.remove(email_file)
            console.print(f"[red]Email deleted:[/red] {email_file}")
        elif action == "important":
            os.makedirs(IMPORTANT_DIR, exist_ok=True)
            important_path = os.path.join(IMPORTANT_DIR, os.path.basename(email_file))
            shutil.move(email_file, important_path)
            console.print(f"[blue]Email moved to Important mailbox:[/blue] {important_path}")
        else:
            console.print("[italic]Skipped.[/italic]")

def manual_review_process(num_emails):
    """
    Performs manual review for a specified number of emails from MAIN_INBOX.
    For each email, displays details and prompts the reviewer to select an action.
    The decision is logged in JSON format, transferred to a remote server via SCP,
    and then the file reference is sent to the embedding endpoint.
    """
    inbox_files = [
        f
        for f in os.listdir(MAIN_INBOX)
        if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if not inbox_files:
        console.print("[yellow]No emails found in inbox for manual review.[/yellow]")
        return

    review_log = []  # Collect log entries
    emails_to_review = inbox_files[:num_emails]

    for email_file in emails_to_review:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)

        # Display email details using a Rich table
        table = Table(title=f"Review: {email_file}", show_lines=True)
        table.add_column("Field", style="bold")
        table.add_column("Details", style="cyan")
        table.add_row("From", sender)
        table.add_row("Subject", subject)
        table.add_row("Date", date_str)
        console.print(table)

        console.print("Select an action for this email:")
        console.print("1. ACTION: REPLY   - Email requires a reply.")
        console.print("2. ACTION: DELETE  - Email should be deleted.")
        console.print("3. ACTION: REVIEW  - Email should be manually reviewed (flagged).")
        console.print("4. ACTION: ARCHIVE - Email should be archived (no further action).")
        console.print("5. ACTION: IMPORTANT - Email should be moved to the Important mailbox.")
        action_choice = Prompt.ask("Enter your choice (1-5)", default="3").strip()

        if action_choice == "1":
            chosen_action = "ACTION: REPLY"
        elif action_choice == "2":
            chosen_action = "ACTION: DELETE"
        elif action_choice == "3":
            chosen_action = "ACTION: REVIEW"
        elif action_choice == "4":
            chosen_action = "ACTION: ARCHIVE"
        elif action_choice == "5":
            chosen_action = "ACTION: IMPORTANT"
        else:
            console.print("[red]Invalid choice, defaulting to ACTION: REVIEW.[/red]")
            chosen_action = "ACTION: REVIEW"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "email_file": email_file,
            "sender": sender,
            "subject": subject,
            "date": date_str,
            "chosen_action": chosen_action,
            "timestamp": timestamp,
        }
        review_log.append(log_entry)

        # Execute the chosen action
        if chosen_action == "ACTION: DELETE":
            try:
                os.remove(file_path)
                console.print("[red]Email deleted.[/red]")
            except Exception as e:
                console.print(f"[red]Error deleting email: {e}[/red]")
        elif chosen_action == "ACTION: ARCHIVE":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            dest_path = os.path.join(ARCHIVE_DIR, email_file)
            shutil.move(file_path, dest_path)
            console.print("[green]Email archived.[/green]")
        elif chosen_action == "ACTION: REVIEW":
            os.makedirs(FOLLOWUP_DIR, exist_ok=True)
            dest_path = os.path.join(FOLLOWUP_DIR, email_file)
            shutil.move(file_path, dest_path)
            console.print("[yellow]Email moved to review (follow-up).[/yellow]")
        elif chosen_action == "ACTION: IMPORTANT":
            os.makedirs(IMPORTANT_DIR, exist_ok=True)
            dest_path = os.path.join(IMPORTANT_DIR, email_file)
            shutil.move(file_path, dest_path)
            console.print("[blue]Email moved to Important mailbox.[/blue]")
        elif chosen_action == "ACTION: REPLY":
            console.print("[blue]Action set to reply; no automatic reply generated in manual review.[/blue]")
        else:
            console.print("[italic]No action taken.[/italic]")

    # Save the review log to a file
    log_file = "manual_review_log.json"
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(review_log, f, indent=2)
        console.print(f"[green]Manual review log saved to {log_file}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving manual review log: {e}[/red]")

    # Transfer the log file to the remote server using SCP
    scp_command = [
        "scp",
        log_file,
        f"{os.getenv('REMOTE_USER')}@{os.getenv('REMOTE_HOST')}:{os.getenv('REMOTE_PATH')}/manual_review_log.json",
    ]
    try:
        result = subprocess.run(scp_command, check=True, capture_output=True, text=True)
        console.print("[green]Manual review log transferred to remote server successfully.[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]File transfer failed: {e.stderr}[/red]")
        return

    # Send the log to the embedding endpoint.
    # Note: The file reference must include the folder prefix per API docs.
    embedding_response = send_embedding("custom-documents/manual_review_log.json")
    if embedding_response:
        console.print("[green]Manual review log successfully sent to embedding endpoint.[/green]")
    else:
        console.print("[red]Failed to send manual review log to embedding endpoint.[/red]")

if __name__ == "__main__":
    try:
        num = IntPrompt.ask("Enter number of emails to review manually", default=0)
    except Exception:
        console.print("[red]Invalid number.[/red]")
        num = 0
    if num > 0:
        manual_review_process(num)

