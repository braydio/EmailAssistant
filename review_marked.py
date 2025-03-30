# review_marked.py v1.0.0
import os
import shutil
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from utils import parse_email
from config import FOLLOWUP_DIR, ARCHIVE_DIR, IMPORTANT_DIR
from draft_reply import generate_draft_reply

console = Console()

def review_marked_emails():
    """
    Reviews emails marked for review by ChatGPT.
    Displays each email (with HTML/CSS stripped) in a clean table,
    then prompts the user to:
      1. Reply (calls the draft reply generator with sending enabled)
      2. Delete the email
      3. Archive the email (move to ARCHIVE_DIR)
      4. Skip (take no action)
    """
    email_files = [f for f in os.listdir(FOLLOWUP_DIR) if os.path.isfile(os.path.join(FOLLOWUP_DIR, f))]
    if not email_files:
        console.print("[yellow]No emails found in the review folder.[/yellow]")
        return

    for email_file in email_files:
        file_path = os.path.join(FOLLOWUP_DIR, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        
        # Display email details in a table
        table = Table(title=f"Email: {email_file}", show_lines=True)
        table.add_column("Field", style="bold")
        table.add_column("Value", style="cyan")
        table.add_row("From", sender)
        table.add_row("Subject", subject)
        table.add_row("Date", date_str)
        table.add_row("Body", body)
        console.print(table)
        
        console.print("Select an action for this email:")
        console.print("1. [bold]Reply[/bold]")
        console.print("2. [bold red]Delete[/bold red]")
        console.print("3. [bold green]Archive[/bold green]")
        console.print("4. [italic]Skip[/italic]")
        
        action_choice = Prompt.ask("Enter your choice (1-4)", default="4").strip()
        if action_choice == "1":
            generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
        elif action_choice == "2":
            try:
                os.remove(file_path)
                console.print(f"[red]Email {email_file} deleted.[/red]")
            except Exception as e:
                console.print(f"[red]Error deleting email {email_file}: {e}[/red]")
        elif action_choice == "3":
            try:
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                dest_path = os.path.join(ARCHIVE_DIR, email_file)
                shutil.move(file_path, dest_path)
                console.print(f"[green]Email {email_file} archived.[/green]")
            except Exception as e:
                console.print(f"[red]Error archiving email {email_file}: {e}[/red]")
        else:
            console.print("[italic]Skipping email.[/italic]")

def review_important_emails():
    """
    Reviews emails in the Important mailbox.
    Displays each email in a clean table, then prompts the user to:
      1. Reply (with draft reply generation)
      2. Delete the email
      3. Archive the email (move to ARCHIVE_DIR)
      4. Skip (take no action)
    """
    email_files = [f for f in os.listdir(IMPORTANT_DIR) if os.path.isfile(os.path.join(IMPORTANT_DIR, f))]
    if not email_files:
        console.print("[yellow]No emails found in the Important mailbox.[/yellow]")
        return

    for email_file in email_files:
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
        
        console.print("Select an action for this email:")
        console.print("1. [bold]Reply[/bold]")
        console.print("2. [bold red]Delete[/bold red]")
        console.print("3. [bold green]Archive[/bold green]")
        console.print("4. [italic]Skip[/italic]")
        
        action_choice = Prompt.ask("Enter your choice (1-4)", default="4").strip()
        if action_choice == "1":
            generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
        elif action_choice == "2":
            try:
                os.remove(file_path)
                console.print(f"[red]Important email {email_file} deleted.[/red]")
            except Exception as e:
                console.print(f"[red]Error deleting email {email_file}: {e}[/red]")
        elif action_choice == "3":
            try:
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                dest_path = os.path.join(ARCHIVE_DIR, email_file)
                shutil.move(file_path, dest_path)
                console.print(f"[green]Important email {email_file} archived.[/green]")
            except Exception as e:
                console.print(f"[red]Error archiving email {email_file}: {e}[/red]")
        else:
            console.print("[italic]Skipping email.[/italic]")

if __name__ == "__main__":
    review_marked_emails()

