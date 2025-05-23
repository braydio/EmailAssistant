# summarize.py (refined with rich aesthetics)
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
from rich.panel import Panel
from rich.text import Text
from prompt_setup import get_summary_prompt, get_action_prompt
from utils import (
    parse_email,
    send_notification,
    fuzzy_select_email,
    load_filter_rules,
    matches_filter_rule,
    move_message_to_trash_via_imap,
)
from gpt_api import ask_gpt, get_active_model
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, TRASH_DIR
from draft_reply import generate_draft_reply

console = Console()
STATS_FILE = os.path.expanduser("~/Projects/GPTMail/email_batch_stats.json")


def stylize_console(message, style="green"):
    console.print(f"[{style}]{message}[/{style}]")


def summarize_all_unread_emails():
    """
    Legacy entrypoint preserved for compatibility. Routes to silent bulk process.
    """
    bulk_summarize_and_process_silent()


def summarize_specific_email(email_file=None, silent=False):
    if email_file is None:
        stylize_console("No email file specified.", "red")
        return None

    file_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(file_path):
        stylize_console(f"Error: File '{email_file}' not found in {MAIN_INBOX}.", "red")
        return None

    subject, sender, body, date_str, _ = parse_email(file_path)

    summary_prompt = get_summary_prompt(sender, date_str, subject, body)

    raw_match = re.search(
        r"EMAIL DETAILS:\n(.*?)If there are any actions, tasks, or urgent items mentioned, please highlight them\.",
        summary_prompt,
        re.DOTALL,
    )
    raw_email_block = (
        raw_match.group(1).strip() if raw_match else "[Could not extract email block]"
    )

    console.print(
        Panel(
            Text(summary_prompt),
            title="🧠 [bold blue]System Summary Prompt[/bold blue]",
            style="blue",
        )
    )
    console.print(
        Panel(
            Text(raw_email_block),
            title="📩 [bold white]Email Details Block[/bold white]",
            style="dim cyan",
        )
    )

    summary_response = ask_gpt(summary_prompt)
    used_model = summary_response.get("model", "unknown")

    summary_content = (
        summary_response.get("choices", [{}])[0].get("message", {}).get("content")
        or summary_response.get("text")
        or ""
    ).strip()

    console.print(
        Panel(
            Text(summary_content),
            title="🤖 [bold green]GPT Summary Response[/bold green]",
            style="green",
        )
    )

    action_prompt = get_action_prompt(summary_content)
    console.print(Panel(Text(action_prompt), title="🟡 Action Prompt", style="yellow"))

    action_response = ask_gpt(action_prompt)
    action_text = (
        action_response.get("choices", [{}])[0].get("message", {}).get("content")
        or action_response.get("text")
        or ""
    ).strip()

    console.print(
        Panel(
            Text(action_text),
            title="🔴 [bold red]GPT Action Response[/bold red]",
            style="red",
        )
    )

    used_model = action_response.get("model", used_model)
    match = re.search(
        r"ACTION:\s*(ARCHIVE|DELETE|REPLY|REVIEW)", action_text, re.IGNORECASE
    )
    recommended_action = (
        match.group(1).upper()
        if match
        else next(
            (
                w
                for w in ["ARCHIVE", "DELETE", "REPLY", "REVIEW"]
                if re.search(rf"\b{w}\b", action_text, re.IGNORECASE)
            ),
            "NONE",
        )
    )

    console.print(
        Panel(
            Text(f"{recommended_action}"),
            title="🌹 [bold magenta]RECOMMENDED ACTION[/bold magenta]",
            style="magenta",
        )
    )

    if not silent:
        send_notification(
            subject, sender, f"Summary: {summary_content}\nAction: {recommended_action}"
        )

        if recommended_action == "ARCHIVE":
            move_email_with_category(email_file, ARCHIVE_DIR)
        elif recommended_action == "REVIEW":
            move_email_with_category(email_file, FOLLOWUP_DIR)
        elif recommended_action == "DELETE":
            move_to_trash_via_maildir(email_file)
        elif recommended_action == "REPLY":
            if (
                Prompt.ask("Send generated reply? (yes/no)", default="no").lower()
                == "yes"
            ):
                generate_draft_reply(
                    email_file=email_file,
                    view_original=True,
                    view_reply=True,
                    send=True,
                )

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
        "action_text": action_text,
        "model": used_model,
    }


def bulk_summarize_and_process_silent(num_emails=None, confirm_all=False):
    stylize_console("Applying filter rules...", "blue")
    apply_filter_rules(MAIN_INBOX)
    emails = [
        f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if num_emails:
        emails = emails[:num_emails]
    if not emails:
        stylize_console("No emails to process.", "yellow")
        return

    stats = json.load(open(STATS_FILE)) if os.path.exists(STATS_FILE) else {}
    total_time = 0
    batches = [emails[i : i + 10] for i in range(0, len(emails), 10)]
    for batch_idx, batch in enumerate(batches, 1):
        stylize_console(f"\nBatch {batch_idx}/{len(batches)} processing…", "bold")
        batch_results = []
        for email_file in batch:
            result = summarize_specific_email(email_file, silent=True)
            total_time += result["time"]
            batch_results.append(result)

        table = Table(title=f"Batch {batch_idx} Recommendations", show_lines=True)
        table.add_column("No.", style="bold")
        table.add_column("From", style="cyan")
        table.add_column("Subject", style="magenta")
        table.add_column("Date", style="green")
        table.add_column("Action", style="yellow")
        for i, r in enumerate(batch_results, 1):
            disp = (
                r["recommended_action"]
                if r["recommended_action"] != "REVIEW"
                else "REVIEW (manual)"
            )
            table.add_row(str(i), r["sender"], r["subject"], r["clean_date"], disp)
        console.print(table)

        if confirm_all or Confirm.ask("Execute ALL recommended actions?", default=True):
            for r in batch_results:
                dest = {
                    "ARCHIVE": ARCHIVE_DIR,
                    "DELETE": TRASH_DIR,
                    "REVIEW": FOLLOWUP_DIR,
                }.get(r["recommended_action"])
                if dest:
                    move_email_with_category(r["email_file"], dest)
                else:
                    stylize_console(
                        f"Unknown action '{r['recommended_action']}' — skipped.", "red"
                    )

        model = batch_results[0].get("model", "unknown") if batch_results else "unknown"
        stats.setdefault(model, []).append(
            {"duration": total_time, "count": len(batch)}
        )
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as sf:
            json.dump(stats, sf, indent=2)

        stylize_console(
            f"⏱ Total time for batch {batch_idx}: {total_time:.2f}s", "bold cyan"
        )
        avg = sum(e["duration"] for e in stats[model]) / len(stats[model])
        stylize_console(
            f"Avg for {model} over {len(stats[model])} runs: {avg:.2f}s", "bold cyan"
        )

        if batch_idx < len(batches):
            stylize_console("Pausing 20–30 seconds before next batch…", "blue")
            time.sleep(random.uniform(20, 30))

    stylize_console(
        f"\nProcessed {len(emails)} emails in {len(batches)} batches. Total time: {total_time:.2f}s",
        "bold green",
    )


def move_to_trash_via_maildir(email_file):
    src = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src):
        stylize_console(f"Source not found: {src}", "red")
        return
    if not move_message_to_trash_via_imap(src):
        stylize_console(
            f"IMAP deletion failed for {email_file}; skipping local move.", "red"
        )
        return
    os.makedirs(os.path.join(TRASH_DIR, "cur"), exist_ok=True)
    try:
        shutil.move(src, os.path.join(TRASH_DIR, "cur", email_file))
        stylize_console(f"Email moved to trash: {email_file}", "red")
    except Exception as e:
        stylize_console(f"Error moving to trash {email_file}: {e}", "bold red")


def move_email_with_category(email_file, target_dir):
    src_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src_path):
        stylize_console(
            f"Warning: source file vanished before move: {email_file}", "yellow"
        )
        return
    if target_dir == TRASH_DIR:
        move_to_trash_via_maildir(email_file)
    else:
        os.makedirs(target_dir, exist_ok=True)
        try:
            shutil.move(src_path, os.path.join(target_dir, email_file))
            stylize_console(f"Moved to {target_dir}: {email_file}", "blue")
        except FileNotFoundError as e:
            stylize_console(f"Move failed: {e}", "red")


def list_emails_for_summary(inbox_path=MAIN_INBOX):
    email_files = [
        f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))
    ]
    if not email_files:
        stylize_console("No new emails found.", "yellow")
        return None
    table = Table(
        title="Available Emails", show_header=True, header_style="bold magenta"
    )
    table.add_column("No.", style="bold")
    table.add_column("From", style="cyan")
    table.add_column("Subject", style="green")
    table.add_column("Date", style="yellow")
    email_info = []
    for i, email_file in enumerate(email_files):
        subject, sender, _, date_str, _ = parse_email(
            os.path.join(inbox_path, email_file)
        )
        email_info.append([i + 1, sender, subject, email_file, date_str])
        table.add_row(str(i + 1), sender, subject, date_str)
    console.print(table)
    return email_info


def stylized_search_output(query, matches):
    if matches:
        stylize_console(f"Search results for '{query}':", "bold")
        for match in matches:
            stylize_console(f" • {match}", "white")
    else:
        stylize_console(f"No emails found matching '{query}'.", "yellow")


def search_emails(query, inbox_path=MAIN_INBOX):
    query_lower = query.lower()
    matches = []
    for f in os.listdir(inbox_path):
        if os.path.isfile(os.path.join(inbox_path, f)):
            subject, sender, *_ = parse_email(os.path.join(inbox_path, f))
            if query_lower in subject.lower() or query_lower in sender.lower():
                matches.append(f)
    stylized_search_output(query, matches)
    return matches if matches else None


def bulk_summarize_and_process_silent(num_emails=None, confirm_all=False):
    stylize_console("Applying filter rules...", "blue")
    apply_filter_rules(MAIN_INBOX)
    emails = [
        f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))
    ]
    if num_emails:
        emails = emails[:num_emails]
    if not emails:
        stylize_console("No emails to process.", "yellow")
        return
    stats = json.load(open(STATS_FILE)) if os.path.exists(STATS_FILE) else {}
    batches = [emails[i : i + 10] for i in range(0, len(emails), 10)]
    for batch_idx, batch in enumerate(batches, 1):
        stylize_console(f"\nBatch {batch_idx}/{len(batches)} processing…", "bold")

        model = get_active_model()
        start_ts = time.time()
        results = [
            summarize_specific_email(email_file, silent=True) for email_file in batch
        ]
        end_ts = time.time()
        table = Table(title=f"Batch {batch_idx} Recommendations", show_lines=True)
        table.add_column("No.", style="bold")
        table.add_column("From", style="cyan")
        table.add_column("Subject", style="magenta")
        table.add_column("Date", style="green")
        table.add_column("Action", style="yellow")
        for i, r in enumerate(results, 1):
            disp = (
                r["recommended_action"]
                if r["recommended_action"] != "REVIEW"
                else "REVIEW (manual)"
            )
            table.add_row(str(i), r["sender"], r["subject"], r["clean_date"], disp)
        console.print(table)
        if confirm_all or Confirm.ask("Execute ALL recommended actions?", default=True):
            for r in results:
                dest = {
                    "ARCHIVE": ARCHIVE_DIR,
                    "DELETE": TRASH_DIR,
                    "REVIEW": FOLLOWUP_DIR,
                }.get(r["recommended_action"])
                if dest:
                    move_email_with_category(r["email_file"], dest)
                else:
                    stylize_console(
                        f"Unknown action '{r['recommended_action']}' — skipped.", "red"
                    )
        duration = end_ts - start_ts
        count = len(batch)
        model = results[0].get("model", "unknown") if results else "unknown"
        stats.setdefault(model, []).append({"duration": duration, "count": count})
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as sf:
            json.dump(stats, sf, indent=2)
        entries = stats[model]
        avg = sum(e["duration"] for e in entries) / len(entries)
        stylize_console(
            f"Batch #{batch_idx} took {duration:.1f}s for {count} emails using model {model}",
            "bold cyan",
        )
        stylize_console(
            f"Avg for {model} over {len(entries)} runs: {avg:.1f}s", "bold cyan"
        )
        if batch_idx < len(batches):
            stylize_console("Pausing 20–30 seconds before next batch…", "blue")
            time.sleep(random.uniform(20, 30))
    stylize_console(
        f"\nProcessed {len(emails)} emails in {len(batches)} batches.", "bold green"
    )


def apply_filter_rules(inbox_path=MAIN_INBOX):
    rules = load_filter_rules()
    email_files = [
        f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))
    ]
    for email_file in email_files:
        file_path = os.path.join(inbox_path, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        email_text = f"From: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
        for rule in rules:
            action = matches_filter_rule(email_text, rule)
            if action == "DELETE":
                move_email_with_category(email_file, TRASH_DIR)
                stylize_console(f"Filtered to DELETE (trash): {email_file}", "red")
                break
            elif action == "ARCHIVE":
                move_email_with_category(email_file, ARCHIVE_DIR)
                stylize_console(f"Filtered to ARCHIVE: {email_file}", "green")
                break
            elif action == "REVIEW":
                move_email_with_category(email_file, FOLLOWUP_DIR)
                stylize_console(
                    f"Filtered to REVIEW (follow-up): {email_file}", "yellow"
                )
                break


def reply_to_email(email_file=None):
    if not email_file:
        email_info = list_emails_for_summary()
        if not email_info:
            return
        user_input = Prompt.ask(
            "\nEnter the number of the email to reply to (or press Enter to search)",
            default="",
        )
        if user_input == "":
            selected = fuzzy_select_email(email_info)
            if not selected:
                stylize_console("No email selected via fuzzy search.", "yellow")
                return
            email_file = selected
        else:
            try:
                idx = int(user_input) - 1
                if 0 <= idx < len(email_info):
                    email_file = email_info[idx][3]
                else:
                    stylize_console("Invalid number.", "red")
                    return
            except ValueError:
                stylize_console("Invalid input.", "red")
                return
    file_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(file_path):
        stylize_console(f"Error: File '{email_file}' not found in {MAIN_INBOX}.", "red")
        return
    subject, sender, body, date_str, _ = parse_email(file_path)
    prompt = (
        f"Compose a brief, polite email reply with a greeting and relevant details.\n\n"
        f"Original Email:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}\n"
    )
    draft = ask_gpt(prompt)
    if draft:
        stylize_console("\nDraft Reply:", "bold underline")
        console.print(draft.get("text", draft))
        stylize_console(
            "Please copy/paste this into your email client or adjust as needed.",
            "italic",
        )
    else:
        stylize_console("Failed to generate a draft reply.", "red")
