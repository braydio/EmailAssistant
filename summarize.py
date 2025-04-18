# summarize.py

import re
import os
import shutil
import json
import time
import random
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
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, SPAM_DIR, TRASH_DIR, LOCAL_AI_BASE_URL
from draft_reply import generate_draft_reply

console = Console()

def summarize_all_unread_emails():
    """
    Summarizes all unread emails in the MAIN_INBOX, pausing after every 5 summaries.
    """
    inbox_path = MAIN_INBOX
    email_files = [
        f for f in os.listdir(inbox_path)
        if os.path.isfile(os.path.join(inbox_path, f))
    ]
    if not email_files:
        console.print("[yellow]No new emails found.[/yellow]")
        return

    for idx, email_file in enumerate(email_files, start=1):
        summarize_specific_email(email_file)
        if idx % 5 == 0 and idx < len(email_files):
            console.print(
                f"[blue]Processed {idx} emails; pausing for 20–30 seconds to prevent overheating…[/blue]"
            )
            time.sleep(random.uniform(20, 30))


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
    
def bulk_summarize_and_process_silent(num_emails=None, confirm_all=False):
    """
    Processes inbox silently in batches of 5,
    shows a table per batch, prompts execution, and throttles.
    """
    console.print("[blue]Applying filter rules...[/blue]")
    apply_filter_rules(MAIN_INBOX)
    emails = [
        f for f in os.listdir(MAIN_INBOX)
        if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if num_emails:
        emails = emails[:num_emails]
    if not emails:
        console.print("[yellow]No emails to process.[/yellow]")
        return

    batches = [emails[i:i+5] for i in range(0, len(emails), 5)]
    for batch_idx, batch in enumerate(batches, start=1):
        console.print(f"\n[bold]Batch {batch_idx}/{len(batches)} processing…[/bold]")
        results = []
        for email_file in batch:
            res = summarize_specific_email(email_file, silent=True)
            if res:
                results.append(res)

        table = Table(
            title=f"Batch {batch_idx} Recommendations", show_lines=True
        )
        table.add_column("No.", style="bold")
        table.add_column("From", style="cyan")
        table.add_column("Subject", style="magenta")
        table.add_column("Date", style="green")
        table.add_column("Action", style="yellow")
        for i, r in enumerate(results, start=1):
            act = r["recommended_action"]
            disp = act if act != "REVIEW" else "REVIEW (manual)"
            table.add_row(str(i), r["sender"], r["subject"], r["clean_date"], disp)
        console.print(table)

        if confirm_all or Confirm.ask("Execute ALL recommended actions for this batch?", default=True):
            for r in results:
                move_email_with_category(
                    r["email_file"],
                    {
                        'ARCHIVE': ARCHIVE_DIR,
                        'DELETE': TRASH_DIR,
                        'REVIEW': FOLLOWUP_DIR
                    }.get(r["recommended_action"])
                )
        else:
            if Confirm.ask("Execute SOME of the recommended actions?", default=False):
                for r in results:
                    if Confirm.ask(
                        f"Apply {r['recommended_action']} to {r['email_file']}?",
                        default=True
                    ):
                        move_email_with_category(
                            r["email_file"],
                            {
                                'ARCHIVE': ARCHIVE_DIR,
                                'DELETE': TRASH_DIR,
                                'REVIEW': FOLLOWUP_DIR
                            }.get(r["recommended_action"])
                        )

        if batch_idx < len(batches):
            console.print("[blue]Pausing 20–30 seconds before next batch…[/blue]")
            time.sleep(random.uniform(20, 30))

    console.print(
        f"\n[bold green]Processed {len(emails)} emails in {len(batches)} batches.[/bold green]"
    )
    
def summarize_specific_email(email_file=None, silent=False):
    """
    Summarizes a specific email, then determines an action via GPT.
    If not silent, executes the action immediately; otherwise returns a result dict.
    """
    if email_file is None:
        console.print("[red]No email file specified.[/red]")
        return None

    file_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File '{email_file}' not found in {MAIN_INBOX}.[/red]")
        return None

    subject, sender, body, date_str, _ = parse_email(file_path)

    # --- 1) Detailed summary prompt ---
    summary_prompt = (
        "You are an email assistant. Please provide a concise yet detailed summary "
        "of the following email. Include any requests, deadlines, or important context. "
        "Limit your summary to about 75 words.\n\n"
        f"Email details:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n"
        f"{body}\n\n"
        "If there are any actions, tasks, or urgent items mentioned, please highlight them."
    )

    console.print(
        f"[blue]\nGenerating summary for:[/blue] [yellow]{subject}[/yellow] from [cyan]{sender}[/cyan]"
    )
    summary_response = ask_gpt(summary_prompt)
    raw_summary = summary_response.get("text", "")
    summary_content = raw_summary.strip()

    console.print(f"[bold magenta]Summary:[/bold magenta] {summary_content}")

    # --- 2) Action prompt ---
    action_prompt = (
        "You are a specialized email triage assistant. Read the following email summary carefully.\n\n"
        "Decide which of the following 4 options best applies:\n"
        "1) DELETE — if this email has no importance, is spam, or can be safely ignored.\n"
        "2) REPLY — if this email requires a direct response or follow-up.\n"
        "3) REVIEW — if the email needs attention or reading but doesn't need a reply.\n"
        "4) ARCHIVE — if the email should simply be stored (e.g., informational content, no action needed).\n\n"
        "Summary:\n"
        f"{summary_content}\n\n"
        "Provide a short reason (1–2 sentences) in plain text for your choice, "
        "then a final line with EXACTLY 2 words, like:\n"
        "ACTION: REPLY\n\n"
        "Now please respond similarly, following the same format."
    )

    console.print("[blue]Determining recommended action...[/blue]")
    action_response = ask_gpt(action_prompt)
    raw_action = action_response.get("text", "").strip()

    # Parse final ACTION line
    pattern = r"ACTION:\s*(ARCHIVE|DELETE|REPLY|REVIEW)"
    match = re.search(pattern, raw_action, re.IGNORECASE)
    recommended_action = match.group(1).upper() if match else "NONE"

    # --- 3) If not silent, execute now ---
    if not silent:
        console.print(f"[bold green]Recommended Action:[/bold green] {recommended_action}")
        console.print(f"\n[bold]Summary:[/bold]\n{summary_content}\n")
        send_notification(
            subject,
            sender,
            f"Summary: {summary_content}\nAction: {recommended_action}"
        )

        if recommended_action == "ARCHIVE":
            move_email_with_category(email_file, ARCHIVE_DIR)
            console.print("[green]Email archived.[/green]\n")
        elif recommended_action == "REVIEW":
            move_email_with_category(email_file, FOLLOWUP_DIR)
            console.print("[yellow]Email moved to review (follow-up).[/yellow]\n")
        elif recommended_action == "DELETE":
            move_email_with_category(email_file, TRASH_DIR)
            console.print("[red]Email moved to trash.[/red]\n")
        elif recommended_action == "REPLY":
            if Prompt.ask("Send generated reply? (yes/no)", default="no").lower() == "yes":
                generate_draft_reply(
                    email_file=email_file,
                    view_original=True,
                    view_reply=True,
                    send=True
                )
                console.print("[green]Reply sent.[/green]\n")
        return None

    # --- 4) Silent result ---
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
        "action_text": raw_action
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

def summarize_specific_email(email_file=None, silent=False):
    """
    Summarizes a specific email, then determines an action via GPT.
    If not silent, executes the action immediately; otherwise returns a result dict.
    """
    if email_file is None:
        console.print("[red]No email file specified.[/red]")
        return None

    file_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File '{email_file}' not found in {MAIN_INBOX}.[/red]")
        return None

    subject, sender, body, date_str, _ = parse_email(file_path)

    # --- 1) Detailed summary prompt ---
    summary_prompt = (
        "You are an email assistant. Please provide a concise yet detailed summary "
        "of the following email. Include any requests, deadlines, or important context. "
        "Limit your summary to about 75 words.\n\n"
        f"Email details:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n"
        f"{body}\n\n"
        "If there are any actions, tasks, or urgent items mentioned, please highlight them."
    )

    console.print(f"[blue]\nGenerating summary for:[/blue] [yellow]{subject}[/yellow] from [cyan]{sender}[/cyan]")
    summary_response = ask_gpt(summary_prompt)
    raw_summary = summary_response.get("text", "")
    summary_content = raw_summary.strip()

    console.print(f"[bold magenta]Summary:[/bold magenta] {summary_content}")

    # --- 2) Action prompt ---
    action_prompt = (
        "You are a specialized email triage assistant. Read the following email summary carefully.\n\n"
        "Decide which of the following 4 options best applies:\n"
        "1) DELETE — if this email has no importance, is spam, or can be safely ignored.\n"
        "2) REPLY — if this email requires a direct response or follow-up.\n"
        "3) REVIEW — if the email needs attention or reading but doesn't need a reply.\n"
        "4) ARCHIVE — if the email should simply be stored (e.g., informational content, no action needed).\n\n"
        "Summary:\n"
        f"{summary_content}\n\n"
        "Provide a short reason (1–2 sentences) in plain text for your choice, "
        "then a final line with EXACTLY 2 words, like:\n"
        "ACTION: REPLY\n\n"
        "Now please respond similarly, following the same format."
    )

    console.print("[blue]Determining recommended action...[/blue]")
    action_response = ask_gpt(action_prompt)
    raw_action = action_response.get("text", "").strip()

    # Parse final ACTION line
    pattern = r"ACTION:\s*(ARCHIVE|DELETE|REPLY|REVIEW)"
    match = re.search(pattern, raw_action, re.IGNORECASE)
    recommended_action = match.group(1).upper() if match else "NONE"

    # --- 3) If not silent, execute now ---
    if not silent:
        console.print(f"[bold green]Recommended Action:[/bold green] {recommended_action}")
        console.print(f"\n[bold]Summary:[/bold]\n{summary_content}\n")
        send_notification(subject, sender, f"Summary: {summary_content}\nAction: {recommended_action}")

        if recommended_action == "ARCHIVE":
            move_email_with_category(email_file, ARCHIVE_DIR)
            console.print("[green]Email archived.[/green]\n")
        elif recommended_action == "REVIEW":
            move_email_with_category(email_file, FOLLOWUP_DIR)
            console.print("[yellow]Email moved to review (follow-up).[/yellow]\n")
        elif recommended_action == "DELETE":
            move_email_with_category(email_file, TRASH_DIR)
            console.print("[red]Email moved to trash.[/red]\n")
        elif recommended_action == "REPLY":
            if Prompt.ask("Send generated reply? (yes/no)", default="no").lower() == "yes":
                generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
                console.print("[green]Reply sent.[/green]\n")
        return None

    # --- 4) Silent result ---
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
        "action_text": raw_action
    }


def move_email_with_category(email_file, base_dir, category=None):
    """
    Moves email from MAIN_INBOX into base_dir (and subfolder if category).
    """
    src = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src):
        console.print(f"[red]Cannot move '{email_file}': source not found.[/red]")
        return
    dest_dir = os.path.join(base_dir, category) if category else base_dir
    os.makedirs(dest_dir, exist_ok=True)
    shutil.move(src, os.path.join(dest_dir, email_file))

