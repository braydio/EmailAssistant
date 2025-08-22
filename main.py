"""Menu-driven command-line interface for managing email workflows."""

import json
import os
import shlex
import shutil
import subprocess
import sys

from rich import print
from rich.table import Table
from rich.console import Console
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, TRASH_DIR, IMPORTANT_DIR
from summarize import apply_filter_rules, reply_to_email, search_emails
from draft_reply import generate_draft_reply
from mail_rules import interactive_rule_application
from batch_cleanup import batch_cleanup_analysis

console = Console()


def launch_in_new_terminal(command):
    """Run ``command`` in a separate terminal window if possible.

    Attempts to open a new terminal on macOS, Windows, and Linux. If no
    suitable terminal emulator is found, falls back to running the command in
    the current window.
    """

    if sys.platform.startswith("darwin"):
        script = f'tell app "Terminal" to do script "{shlex.join(command)}"'
        subprocess.Popen(["osascript", "-e", script])
        return

    if os.name == "nt":
        subprocess.Popen(["start", "cmd", "/k", *command], shell=True)
        return

    terminal_candidates = [
        ["x-terminal-emulator", "-e"],
        ["gnome-terminal", "--"],
        ["konsole", "-e"],
        ["xfce4-terminal", "-e"],
        ["xterm", "-e"],
        ["lxterminal", "-e"],
        ["terminator", "-x"],
    ]

    for term in terminal_candidates:
        terminal_path = shutil.which(term[0])
        if terminal_path:
            subprocess.Popen([terminal_path, *term[1:], *command])
            return

    print("[yellow]No compatible terminal found. Running in current window.[/yellow]")
    subprocess.Popen(command)


def count_emails(directory):
    return len(
        [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    )


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

    table = Table(title=f"󰺘 Email Status", style="bold cyan")
    table.add_column("Category", style="bold white")
    table.add_column("Count", justify="right", style="magenta")

    for key, value in status.items():
        table.add_row(key, str(value))

    console.print(table)


def clear_archive():
    """
    Clears all emails in the archive folder.
    """
    email_files = [
        f
        for f in os.listdir(ARCHIVE_DIR)
        if os.path.isfile(os.path.join(ARCHIVE_DIR, f))
    ]
    if not email_files:
        console.print("[yellow]Archive folder is already empty.[/yellow]")
        return

    confirm = (
        input("Are you sure you want to clear the Archive folder? (yes/no): ")
        .strip()
        .lower()
    )
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
        "1": "Summarize all unread emails (New Process, new window)",
        "2": "Silent Bulk Summarize and Process emails (new window)",
        "3": "Fuzzy Find an email for reply",
        "4": "Generate and send a draft reply",
        "5": "Review Flagged Emails (AI-flagged, new window)",
        "6": "Search emails by keyword/date",
        "7": "Apply Filter Rules (Interactive)",
        "8": "Apply Mail Rule (Interactive)",
        "9": "Batch Cleanup Analysis (Top Senders)",
        "10": "Manual Review Process (with Embedding, new window)",
        "11": "Clear Archive Box",
        "12": "Review Important Emails (new window)",
        "13": "Run silent GPT summary & auto-apply (no confirm, new window)",  # <- NEW OPTION
        "0": "[bold red]Exit[/bold red]",
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
            # Uses the new two-step summarization (summary then action) for all unread emails.
            launch_in_new_terminal(
                [
                    "python",
                    "-c",
                    (
                        "from summarize import summarize_all_unread_emails; "
                        "summarize_all_unread_emails()"
                    ),
                ]
            )
        elif choice == "2":
            num = input(
                "Enter number of emails to process silently (or press Enter for all): "
            ).strip()
            num_emails = int(num) if num.isdigit() else None
            num_repr = repr(num_emails)
            launch_in_new_terminal(
                [
                    "python",
                    "-c",
                    (
                        "from summarize import bulk_summarize_and_process_silent; "
                        f"bulk_summarize_and_process_silent({num_repr})"
                    ),
                ]
            )
        elif choice == "3":
            reply_to_email()
        elif choice == "4":
            console.print(
                "\n[bold yellow]Generating and sending draft reply...[/bold yellow]"
            )
            generate_draft_reply(send=True)
        elif choice == "5":
            launch_in_new_terminal(
                [
                    "python",
                    "-c",
                    "import review_marked; review_marked.review_marked_emails()",
                ]
            )
        elif choice == "6":
            keyword = input(
                "Enter keyword or date (YYYY-MM-DD) / range (YYYY-MM-DD to YYYY-MM-DD): "
            ).strip()
            search_emails(keyword)
        elif choice == "7":
            apply_filter_rules(MAIN_INBOX)
        elif choice == "8":
            interactive_rule_application()
        elif choice == "9":
            batch_cleanup_analysis()
        elif choice == "10":
            launch_in_new_terminal(["python", "manual_review.py"])
        elif choice == "11":
            clear_archive()
        elif choice == "12":
            launch_in_new_terminal(
                [
                    "python",
                    "-c",
                    "import review_marked; review_marked.review_important_emails()",
                ]
            )
        elif choice == "13":
            console.print(
                "[bold yellow]Running silent mode — no confirmation, all actions will be applied.[/bold yellow]"
            )
            launch_in_new_terminal(
                [
                    "python",
                    "-c",
                    (
                        "from summarize import bulk_summarize_and_process_silent; "
                        "bulk_summarize_and_process_silent(num_emails=200, confirm_all=True)"
                    ),
                ]
            )
        elif choice == "0":
            console.print("[bold red]Goodbye! [/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")

        print_email_status()


if __name__ == "__main__":
    main()
