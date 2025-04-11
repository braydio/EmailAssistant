
import os
import shutil
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from utils import (
    parse_email, 
    send_notification, 
    fuzzy_select_email, 
    record_filter_rule, 
    load_filter_rules,       
    matches_filter_rule
)
from gpt_api import ask_gpt
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, SPAM_DIR, TRASH_DIR
from draft_reply import generate_draft_reply

console = Console()

def summarize_all_unread_emails():
    """
    Summarizes all unread emails in the MAIN_INBOX.
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
        summarize_specific_email(os.path.basename(email_file))

def list_emails_for_summary(inbox_path=MAIN_INBOX):
    """
    Lists emails in the specified inbox directory (default: MAIN_INBOX) in a clean Rich table.
    Returns a list of [index, sender, subject, filename, date_str].
    """
    email_files = [
        f for f in os.listdir(inbox_path)
        if os.path.isfile(os.path.join(inbox_path, f))
    ]
    if not email_files:
        console.print("[yellow]No new emails found.[/yellow]")
        return None

    email_info = []
    table = Table(title="Available Emails", show_header=True, header_style="bold magenta")
    table.add_column("No.", style="bold")
    table.add_column("From", style="cyan")
    table.add_column("Subject", style="green")
    table.add_column("Date", style="yellow")

    for i, email_file in enumerate(email_files):
        subject, sender, _, date_str, _ = parse_email(os.path.join(inbox_path, email_file))
        email_info.append([i + 1, sender, subject, email_file, date_str])
        table.add_row(str(i + 1), sender, subject, date_str)

    console.print(table)
    return email_info

def summarize_specific_email(email_file=None, silent=False):
    """
    Summarizes a specific email and then (optionally) executes an action.
    In silent mode, returns a dict of details so the caller
    can handle the action instead of executing it directly.
    """
    inbox_path = MAIN_INBOX

    # --- Identify email ---
    if not email_file:
        email_info = list_emails_for_summary(inbox_path)
        if not email_info:
            return
        user_input = Prompt.ask(
            "\nEnter the number of the email to summarize (or press Enter to search)",
            default=""
        )
        if user_input == "":
            email_file = fuzzy_select_email(email_info)
            if not email_file:
                console.print("[yellow]No email selected via fuzzy search.[/yellow]")
                return
        else:
            try:
                selection = int(user_input) - 1
                if 0 <= selection < len(email_info):
                    email_file = email_info[selection][3]
                else:
                    console.print("[red]Invalid number. Please choose a valid email number.[/red]")
                    return
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or press Enter for fuzzy search.[/red]")
                return

    file_path = os.path.join(inbox_path, email_file)
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File '{email_file}' not found in {inbox_path}.[/red]")
        return None

    subject, sender, body, date_str, _ = parse_email(file_path)

    # --- Generate email summary ---
    summary_prompt = (
        "You are an email assistant. Summarize the following email in under 50 words."
        f"\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n{body}\n"
    )
    console.print(f"[blue]\nGenerating summary for:[/blue] [yellow]{subject}[/yellow] from [cyan]{sender}[/cyan]")
    summary_response = ask_gpt(summary_prompt)
    # Parse the response text from LocalAI (JSON string) to a dict.
    raw_summary = summary_response.get("text", "")
    summary_content = ""
    if raw_summary:
        try:
            parsed_summary = json.loads(raw_summary)
            summary_content = parsed_summary.get("choices", [{}])[0].get("message", {}).get("content", "")
        except json.JSONDecodeError:
            console.print("[red]Failed to parse JSON from LocalAI summary response.[/red]")
    console.print(f"[bold magenta]Summary:[/bold magenta] {summary_content}")

    # --- Generate action recommendation ---
    action_prompt = (
        "Read the following email summary.\n"
        "Based on the summary, which of the 4 options should be executed for this email?\n"
        "Choose DELETE if the email is not important.\n"
        "Choose REPLY if the email requires a reply.\n"
        "Choose REVIEW if the email should be reviewed but doesn't need a reply.\n"
        "Choose ARCHIVE if the email should be archived or if unsure.\n"
        f"\nEmail Summary: {summary_content}\n"
        "\nRespond with only 2 words formatted like:\n"
        "ACTION: ARCHIVE\nACTION: DELETE\nACTION: REPLY\nACTION: REVIEW\n"
    )
    console.print("[blue]Determining recommended action...[/blue]")
    action_response = ask_gpt(action_prompt)
    raw_action = action_response.get("text", "")
    action_text = ""
    if raw_action:
        try:
            parsed_action = json.loads(raw_action)
            action_text = parsed_action.get("choices", [{}])[0].get("message", {}).get("content", "")
        except json.JSONDecodeError:
            console.print("[red]Failed to parse JSON from LocalAI action response.[/red]")

    # --- Extract RULE/CATEGORY lines ---
    category_name = None
    for line in action_text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("RULE:"):
            record_filter_rule(line_stripped)
        elif line_stripped.startswith("CATEGORY:"):
            parts = line_stripped.split("CATEGORY:", 1)
            if len(parts) == 2:
                category_name = parts[1].strip()

    # --- Determine recommended action ---
    if "ACTION: ARCHIVE" in action_text:
        recommended_action = "ARCHIVE"
    elif "ACTION: REVIEW" in action_text:
        recommended_action = "REVIEW"
    elif "ACTION: DELETE" in action_text:
        recommended_action = "DELETE"
    elif "ACTION: REPLY" in action_text:
        recommended_action = "REPLY"
    else:
        recommended_action = "NONE"

    # --- If interactive, execute action immediately ---
    if not silent:
        console.print(f"[bold green]Recommended Action:[/bold green] {recommended_action}")
        console.print("\n[bold underline]Email Summary[/bold underline]")
        console.print(f"[cyan]From:[/cyan] {sender}   [green]Date:[/green] {date_str}")
        console.print(f"[magenta]Subject:[/magenta] {subject}\n")
        console.print(f"[bold]Summary:[/bold]\n{summary_content}\n")
        console.print(f"[bold]Recommended Action:[/bold] {recommended_action}\n")
        send_notification(subject, sender, f"Summary: {summary_content}\nAction: {recommended_action}")

        if recommended_action == "ARCHIVE":
            move_email_with_category(email_file, ARCHIVE_DIR, category_name)
            console.print("[green]Email archived.[/green]\n")
        elif recommended_action == "REVIEW":
            move_email_with_category(email_file, FOLLOWUP_DIR, category_name)
            console.print("[yellow]Email moved to review (follow-up folder).[/yellow]\n")
        elif recommended_action == "DELETE":
            move_email_with_category(email_file, TRASH_DIR, category_name)
            console.print("[red]Email moved to trash.[/red]\n")
        elif recommended_action == "REPLY":
            send_input = Prompt.ask("Send generated reply? (yes/no)", default="no")
            if send_input.lower() == "yes":
                generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
                console.print("[green]Reply sent.[/green]\n")
            else:
                console.print("[italic]Reply generation skipped.[/italic]\n")
        return None

    # --- If silent, return a dictionary of results ---
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        clean_date = f"{dt.month}-{dt.day}-{str(dt.year)[2:]}"
    except Exception:
        clean_date = date_str

    return {
        "email_file": email_file,
        "sender": sender,
        "subject": subject,
        "date_str": date_str,
        "clean_date": clean_date,
        "summary": summary_content,
        "recommended_action": recommended_action,
        "category": category_name,
        "action_text": action_text
    }

def move_email_with_category(email_file, base_dir, category=None):
    """
    Moves the given email_file from MAIN_INBOX into the specified base_dir.
    If a category is provided, a subdirectory is created under base_dir.
    """
    from config import MAIN_INBOX
    src_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src_path):
        console.print(f"[red]Cannot move '{email_file}': source does not exist.[/red]")
        return
    target_dir = os.path.join(base_dir, category) if category else base_dir
    os.makedirs(target_dir, exist_ok=True)
    dst_path = os.path.join(target_dir, email_file)
    shutil.move(src_path, dst_path)

def apply_filter_rules(inbox_path=MAIN_INBOX):
    """
    Applies pre-defined filter rules to each email in the inbox.
    Moves the email based on matching rules.
    """
    rules = load_filter_rules()
    email_files = [
        f for f in os.listdir(inbox_path)
        if os.path.isfile(os.path.join(inbox_path, f))
    ]
    for email_file in email_files:
        file_path = os.path.join(inbox_path, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        email_text = f"From: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
        for rule in rules:
            action = matches_filter_rule(email_text, rule)
            if action == "DELETE":
                move_email_with_category(email_file, TRASH_DIR)
                console.print(f"[red]Filtered to DELETE (trash): {email_file}[/red]")
                break
            elif action == "ARCHIVE":
                move_email_with_category(email_file, ARCHIVE_DIR)
                console.print(f"[green]Filtered to ARCHIVE: {email_file}[/green]")
                break
            elif action == "REVIEW":
                move_email_with_category(email_file, FOLLOWUP_DIR)
                console.print(f"[yellow]Filtered to REVIEW (follow-up): {email_file}[/yellow]")
                break

def search_emails(query, inbox_path=MAIN_INBOX):
    """
    Searches emails in the MAIN_INBOX by subject and sender.
    Displays matching filenames in a clean format.
    """
    matches = []
    email_files = [
        f for f in os.listdir(inbox_path)
        if os.path.isfile(os.path.join(inbox_path, f))
    ]
    query_lower = query.lower()
    for email_file in email_files:
        subject, sender, body, date_str, _ = parse_email(os.path.join(inbox_path, email_file))
        if (query_lower in subject.lower()) or (query_lower in sender.lower()):
            matches.append(email_file)
    if matches:
        console.print(f"[bold]Search results for '{query}':[/bold]")
        for m in matches:
            console.print(f"  • {m}")
        return matches
    else:
        console.print(f"[yellow]No emails found matching '{query}'.[/yellow]")
        return None

def reply_to_email(email_file=None):
    """
    Uses GPT to generate a draft reply for the specified email.
    If no email_file is provided, prompts the user to choose one.
    """
    inbox_path = MAIN_INBOX
    if not email_file:
        email_info = list_emails_for_summary(inbox_path)
        if not email_info:
            return
        user_input = Prompt.ask("\nEnter the number of the email to reply to (or press Enter to search)", default="")
        if user_input == "":
            email_file = fuzzy_select_email(email_info)
            if not email_file:
                console.print("[yellow]No email selected via fuzzy search.[/yellow]")
                return
        else:
            try:
                selection = int(user_input) - 1
                if 0 <= selection < len(email_info):
                    email_file = email_info[selection][3]
                else:
                    console.print("[red]Invalid number. Please choose a valid email number.[/red]")
                    return
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or press Enter for fuzzy search.[/red]")
                return

    file_path = os.path.join(inbox_path, email_file)
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File '{email_file}' not found in {inbox_path}.[/red]")
        return

    subject, sender, body, date_str, _ = parse_email(file_path)
    prompt = (
        f"Compose a brief, polite email reply with a greeting and relevant details.\n\n"
        f"Original Email:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}\n"
    )
    draft = ask_gpt(prompt)
    if draft:
        console.print("\n[bold underline]Draft Reply:[/bold underline]")
        console.print(draft)
        console.print("[italic]Please copy/paste this into your email client or adjust as needed.[/italic]\n")
    else:
        console.print("[red]Failed to generate a draft reply.[/red]")

def bulk_summarize_and_process(limit=None):
    """
    Processes every email in MAIN_INBOX:
      1. Applies filter rules.
      2. Summarizes and recommends an action for remaining emails.
    Optionally limits the number of processed emails.
    """
    console.print("[blue]Applying filter rules...[/blue]")
    apply_filter_rules(MAIN_INBOX)
    remaining_emails = [
        f for f in os.listdir(MAIN_INBOX)
        if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if not remaining_emails:
        console.print("[yellow]No emails left in inbox after filter rules.[/yellow]")
        return
    if limit is None:
        user_limit = Prompt.ask("Enter number of emails to process (or press Enter for all)", default="")
        if user_limit.isdigit():
            limit = int(user_limit)
    if limit is not None:
        remaining_emails = remaining_emails[:limit]
    console.print("\n[bold]Summarizing remaining emails...[/bold]")
    for email_file in remaining_emails:
        summarize_specific_email(email_file)

def bulk_summarize_and_process_silent(num_emails=None):
    """
    Processes emails silently in MAIN_INBOX.
    Collects GPT responses and shows a summary table of recommended actions.
    Prompts the user to execute those actions.
    """
    console.print("[blue]Applying filter rules...[/blue]")
    apply_filter_rules(MAIN_INBOX)
    remaining_emails = [
        f for f in os.listdir(MAIN_INBOX)
        if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if not remaining_emails:
        console.print("[yellow]No emails left in inbox after filter rules.[/yellow]")
        return
    if num_emails is not None:
        remaining_emails = remaining_emails[:num_emails]
    results = []
    console.print("\n[bold]Processing emails silently...[/bold]")
    for email_file in remaining_emails:
        result = summarize_specific_email(email_file, silent=True)
        if result:
            results.append(result)
    if not results:
        console.print("[yellow]No emails processed.[/yellow]")
        return

    table = Table(title="Recommended Actions Summary", show_lines=True)
    table.add_column("No.", style="bold")
    table.add_column("From", style="cyan")
    table.add_column("Subject", style="magenta")
    table.add_column("Date", style="green")
    table.add_column("Action", style="yellow")

    for idx, res in enumerate(results, start=1):
        action = res["recommended_action"]
        action_display = action if action != "REVIEW" else "REVIEW (manual review)"
        table.add_row(
            str(idx),
            res["sender"],
            res["subject"],
            res.get("clean_date", res["date_str"]),
            action_display
        )
    console.print(table)

    if Confirm.ask("\nExecute all recommended actions?"):
        for res in results:
            action = res["recommended_action"]
            if action == "ARCHIVE":
                move_email_with_category(res["email_file"], ARCHIVE_DIR, res["category"])
                console.print(f"[green]Email {res['email_file']} archived.[/green]")
            elif action == "DELETE":
                move_email_with_category(res["email_file"], TRASH_DIR, res["category"])
                console.print(f"[red]Email {res['email_file']} moved to trash.[/red]")
            elif action == "REPLY":
                generate_draft_reply(email_file=res["email_file"], view_original=False, view_reply=False, send=True)
                console.print(f"[green]Reply sent for {res['email_file']}.[/green]")
            elif action == "REVIEW":
                move_email_with_category(res["email_file"], FOLLOWUP_DIR, res["category"])
                console.print(f"[yellow]Email {res['email_file']} moved to review folder.[/yellow]")
            else:
                console.print(f"[italic]No action taken for {res['email_file']}.[/italic]")
    else:
        if Confirm.ask("Execute some of the recommended actions?"):
            for res in results:
                if Confirm.ask(f"Execute recommended action for email {res['email_file']}? (default yes)", default=True):
                    action = res["recommended_action"]
                    if action == "ARCHIVE":
                        move_email_with_category(res["email_file"], ARCHIVE_DIR, res["category"])
                        console.print(f"[green]Email {res['email_file']} archived.[/green]")
                    elif action == "DELETE":
                        move_email_with_category(res["email_file"], TRASH_DIR, res["category"])
                        console.print(f"[red]Email {res['email_file']} moved to trash.[/red]")
                    elif action == "REPLY":
                        generate_draft_reply(email_file=res["email_file"], view_original=False, view_reply=False, send=True)
                        console.print(f"[green]Reply sent for {res['email_file']}.[/green]")
                    elif action == "REVIEW":
                        move_email_with_category(res["email_file"], FOLLOWUP_DIR, res["category"])
                        console.print(f"[yellow]Email {res['email_file']} moved to review folder.[/yellow]")
                    else:
                        console.print(f"[italic]No action taken for {res['email_file']}.[/italic]")
                else:
                    console.print(f"[italic]Skipped email {res['email_file']}.[/italic]")
        else:
            console.print("[italic]No actions executed.[/italic]")

