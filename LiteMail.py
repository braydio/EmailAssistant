
import json
import os
from rich import print
from rich.table import Table
from rich.console import Console
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, TRASH_DIR, IMPORTANT_DIR
from summarize import (
    summarize_all_unread_emails, 
    bulk_summarize_and_process_silent,  # For processing a range of unread emails
    reply_to_email, 
    search_emails
)
from manual_review import manual_review_process
import review_marked
from draft_reply import generate_draft_reply

console = Console()

def count_emails(directory):
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

def get_email_status():
    return {
        " Inbox": count_emails(MAIN_INBOX),
        "⭐ Important": count_emails(IMPORTANT_DIR),
        "󰇱 Archive": count_emails(ARCHIVE_DIR),
        "󰇯 Review": count_emails(FOLLOWUP_DIR),
        "󰗩 Trash": count_emails(TRASH_DIR),
    }

def print_email_status():
    status = get_email_status()
    with open("email_summary.json", "w") as summary:
        json.dump(status, summary, indent=4)

    table = Table(title="󰺘 Email Status", style="bold cyan")
    table.add_column("Category", style="bold white")
    table.add_column("Count", justify="right", style="magenta")
    for key, value in status.items():
        table.add_row(key, str(value))
    console.print(table)

def clear_archive():
    """
    Clears all emails in the archive folder.
    """
    email_files = [f for f in os.listdir(ARCHIVE_DIR) if os.path.isfile(os.path.join(ARCHIVE_DIR, f))]
    if not email_files:
        console.print("[yellow]Archive folder is already empty.[/yellow]")
        return

    confirm = input("Are you sure you want to clear the Archive folder? (yes/no): ").strip().lower()
    if confirm == "yes":
        for email_file in email_files:
            file_path = os.path.join(ARCHIVE_DIR, email_file)
            try:
                os.remove(file_path)
                console.print(f"[red]Deleted archived email:[/red] {email_file}")
            except Exception as e:
                console.print(f"[bold red]Error deleting {email_file}: {e}[/bold red]")
        console.print("[green]Archive folder cleared.[/green]")
    else:
        console.print("[yellow]Clear archive cancelled.[/yellow]")

def print_menu():
    table = Table(title="📌 Email Assistant Menu", style="bold green")
    table.add_column("Option", style="bold cyan")
    table.add_column("Action", style="bold white")

    menu_options = {
        "1": "Summarize all unread emails",
        "2": "Process a range of unread emails",
        "3": "Review flagged emails",
        "4": "Review important emails",
        "5": "Manual review process",
        "6": "Search emails",
        "7": "Clear archived emails",
        "8": "GPT reply to an email",
        "0": "[bold red]Exit[/bold red]"
    }

    for key, value in menu_options.items():
        table.add_row(key, value)
    console.print(table)

def main():
    console.print("[bold cyan]Welcome to the Email Assistant![/bold cyan]")
    print_email_status()

    while True:
        print_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            summarize_all_unread_emails()
        elif choice == "2":
            num = input("Enter number of emails to process (range): ").strip()
            num_emails = int(num) if num.isdigit() else None
            bulk_summarize_and_process_silent(num_emails)
        elif choice == "3":
            review_marked.review_marked_emails()
        elif choice == "4":
            review_marked.review_important_emails()
        elif choice == "5":
            try:
                num = int(input("Enter number of emails to review manually: ").strip())
            except ValueError:
                console.print("[bold red]Invalid number.[/bold red]")
                num = 0
            if num > 0:
                manual_review_process(num)
        elif choice == "6":
            keyword = input("Enter keyword or date (YYYY-MM-DD) / range (YYYY-MM-DD to YYYY-MM-DD): ").strip()
            search_emails(keyword)
        elif choice == "7":
            clear_archive()
        elif choice == "8":
            console.print("\n[bold yellow]Generating GPT reply...[/bold yellow]")
            reply_to_email()
        elif choice == "0":
            console.print("[bold red]Goodbye! [/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")

        print_email_status()

if __name__ == "__main__":
    main()
