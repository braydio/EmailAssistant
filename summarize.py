
# summarize.py
import os
import shutil
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

def list_emails_for_summary(inbox_path=MAIN_INBOX):
    """
    Lists emails in the specified inbox directory (default: MAIN_INBOX).
    Returns a list of [index, sender, subject, filename, date_str].
    """
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    if not email_files:
        print("No new emails found.")
        return None
    email_info = []
    for i, email_file in enumerate(email_files):
        subject, sender, _, date_str, _ = parse_email(os.path.join(inbox_path, email_file))
        email_info.append([i + 1, sender, subject, email_file, date_str])
    return email_info

def summarize_all_unread_emails():
    """
    Summarizes all unread emails in the MAIN_INBOX by calling summarize_specific_email on each one.
    """
    inbox_path = MAIN_INBOX
    email_files = [os.path.join(inbox_path, f) for f in os.listdir(inbox_path)
                   if os.path.isfile(os.path.join(inbox_path, f))]
    if not email_files:
        print("No new emails found.")
        return
    for email_file in email_files:
        summarize_specific_email(os.path.basename(email_file))

def summarize_specific_email(email_file=None, silent=False):
    """
    Summarizes a specific email.
    After summarizing, it inspects the GPT response for:
      - ACTION: REPLY   => Generate and send a response email.
      - ACTION: DELETE  => Delete the email (move to trash).
      - ACTION: REVIEW  => Flag the email for manual review (move to follow-up).
      - ACTION: ARCHIVE => Archive the email.
    In silent mode, returns a dictionary with the summary and recommended action.
    """
    inbox_path = MAIN_INBOX
    if not email_file:
        if silent:
            print("Silent mode requires an email_file to be specified.")
            return None
        else:
            email_info = list_emails_for_summary(inbox_path)
            if not email_info:
                return
            print("\nAvailable Emails:")
            for idx, sender, subject, file, date_str in email_info:
                print(f"{idx}. From: {sender} | Subject: {subject} | Date: {date_str}")
            user_input = input("\nEnter the number of the email to summarize (or press Enter to search): ").strip()
            if user_input == "":
                email_file = fuzzy_select_email(email_info)
                if not email_file:
                    print("No email selected via fuzzy search.")
                    return
            else:
                try:
                    selection = int(user_input) - 1
                    if 0 <= selection < len(email_info):
                        email_file = email_info[selection][3]
                    else:
                        print("Invalid number. Please choose a valid email number.")
                        return
                except ValueError:
                    print("Invalid input. Please enter a number or press Enter for fuzzy search.")
                    return

    file_path = os.path.join(inbox_path, email_file)
    if not os.path.exists(file_path):
        print(f"Error: File '{email_file}' not found in {inbox_path}.")
        return None

    subject, sender, body, date_str, _ = parse_email(file_path)
    prompt = (
        f"You are an email assistant. Please summarize the following email briefly and clearly.\n"
        f"Then, select exactly one of the following actions based on the email's content and include it as the final line:\n\n"
        f"1. ACTION: REPLY - Email requires a reply.\n"
        f"2. ACTION: DELETE - Email should be deleted.\n"
        f"3. ACTION: REVIEW - Email should be manually reviewed.\n"
        f"4. ACTION: ARCHIVE - Email does not require further action and should be archived.\n\n"
        f"DO NOT draft a reply or any follow-up text.\n\n"
        f"Email details:\n"
        f"From: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}\n"
    )
    recommendation_obj = ask_gpt(prompt)
    if recommendation_obj:
        # If the response is a dict (EverythingLLM), extract the text
        if isinstance(recommendation_obj, dict):
            recommendation = recommendation_obj.get("text", "")
        else:
            recommendation = recommendation_obj
        if not silent:
            print(f"\n--- Email Summary ---\nFrom: {sender} | Date: {date_str}\nSubject: {subject}\n")
            print(f"Recommendation/Analysis:\n{recommendation}\n")
            send_notification(subject, sender, recommendation)
        # Process any RULE lines in the recommendation
        for line in recommendation.splitlines():
            if line.strip().startswith("RULE:"):
                record_filter_rule(line.strip())
                break
        category_name = None
        for line in recommendation.splitlines():
            if line.strip().startswith("CATEGORY:"):
                parts = line.split("CATEGORY:", 1)
                if len(parts) == 2:
                    category_name = parts[1].strip()
                break

        if "ACTION: ARCHIVE" in recommendation:
            recommended_action = "ARCHIVE"
        elif "ACTION: REVIEW" in recommendation:
            recommended_action = "REVIEW"
        elif "ACTION: DELETE" in recommendation:
            recommended_action = "DELETE"
        elif "ACTION: REPLY" in recommendation:
            recommended_action = "REPLY"
        else:
            recommended_action = "NONE"

        if not silent:
            if recommended_action == "ARCHIVE":
                move_email_with_category(email_file, ARCHIVE_DIR, category_name)
                print(f"Email archived.\n")
            elif recommended_action == "REVIEW":
                move_email_with_category(email_file, FOLLOWUP_DIR, category_name)
                print("Email moved to review (follow-up folder).\n")
            elif recommended_action == "DELETE":
                move_email_with_category(email_file, TRASH_DIR, category_name)
                print("Email moved to trash.\n")
            elif recommended_action == "REPLY":
                send_input = input("Send generated reply? (yes/no): ").strip().lower()
                if send_input == "yes":
                    generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
                    print("Reply sent.\n")
                else:
                    print("Reply generation skipped.\n")
            else:
                print("No clear recommendation. Email remains in inbox.\n")
            return
        else:
            result = {
                "email_file": email_file,
                "sender": sender,
                "subject": subject,
                "date_str": date_str,
                "recommended_action": recommended_action,
                "category": category_name,
                "recommendation": recommendation
            }
            return result
    else:
        if not silent:
            print(f"Failed to summarize or recommend an action for: {email_file}")
        return None

def move_email_with_category(email_file, base_dir, category=None):
    """
    Moves the given email_file from MAIN_INBOX into the specified base_dir.
    If a category name is provided, it creates a subdirectory under base_dir.
    """
    from config import MAIN_INBOX
    src_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(src_path):
        print(f"Cannot move '{email_file}': source does not exist.")
        return
    if category:
        target_dir = os.path.join(base_dir, category)
    else:
        target_dir = base_dir
    os.makedirs(target_dir, exist_ok=True)
    dst_path = os.path.join(target_dir, email_file)
    shutil.move(src_path, dst_path)

def apply_filter_rules(inbox_path=MAIN_INBOX):
    """
    Applies pre-defined filter rules to each email in the inbox.
    If an email matches a rule that marks it for deletion, it's moved to TRASH_DIR.
    If a rule marks it as archive, it's moved to ARCHIVE_DIR, etc.
    """
    rules = load_filter_rules()
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    for email_file in email_files:
        file_path = os.path.join(inbox_path, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        email_text = f"From: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
        for rule in rules:
            action = matches_filter_rule(email_text, rule)
            if action == "DELETE":
                move_email_with_category(email_file, TRASH_DIR)
                print(f"Filtered to DELETE (trash): {email_file}")
                break
            elif action == "ARCHIVE":
                move_email_with_category(email_file, ARCHIVE_DIR)
                print(f"Filtered to ARCHIVE: {email_file}")
                break
            elif action == "REVIEW":
                move_email_with_category(email_file, FOLLOWUP_DIR)
                print(f"Filtered to REVIEW (moved to follow-up): {email_file}")
                break

def search_emails(query, inbox_path=MAIN_INBOX):
    """
    Allows a basic text-based search of emails in the MAIN_INBOX (subject and sender).
    Returns a list of matching email filenames or None if no matches.
    """
    matches = []
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    query_lower = query.lower()
    for email_file in email_files:
        subject, sender, body, date_str, _ = parse_email(os.path.join(inbox_path, email_file))
        if (query_lower in subject.lower()) or (query_lower in sender.lower()):
            matches.append(email_file)
    if matches:
        print(f"Search results for '{query}':")
        for m in matches:
            print(f"  - {m}")
        return matches
    else:
        print(f"No emails found matching '{query}'.")
        return None

def reply_to_email(email_file=None):
    """
    Uses ChatGPT to generate a draft reply for the specified email.
    The user can then copy/paste or manually finalize the draft in their mail client.
    If no email_file is provided, the function will allow the user to pick from the inbox.
    """
    inbox_path = MAIN_INBOX
    if not email_file:
        email_info = list_emails_for_summary(inbox_path)
        if not email_info:
            return
        print("\nAvailable Emails to Reply To:")
        for idx, sender, subject, file, date_str in email_info:
            print(f"{idx}. From: {sender} | Subject: {subject} | Date: {date_str}")
        user_input = input("\nEnter the number of the email to reply to (or press Enter to search): ").strip()
        if user_input == "":
            email_file = fuzzy_select_email(email_info)
            if not email_file:
                print("No email selected via fuzzy search.")
                return
        else:
            try:
                selection = int(user_input) - 1
                if 0 <= selection < len(email_info):
                    email_file = email_info[selection][3]
                else:
                    print("Invalid number. Please choose a valid email number.")
                    return
            except ValueError:
                print("Invalid input. Please enter a number or press Enter for fuzzy search.")
                return

    file_path = os.path.join(inbox_path, email_file)
    if not os.path.exists(file_path):
        print(f"Error: File '{email_file}' not found in {inbox_path}.")
        return

    subject, sender, body, date_str, _ = parse_email(file_path)
    prompt = (
        f"Compose a brief, polite email reply. Include a greeting, and any relevant details.\n\n"
        f"Original Email:\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Date: {date_str}\n\n"
        f"{body}\n"
    )
    draft = ask_gpt(prompt)
    if draft:
        print(f"\n--- Draft Reply ---\n{draft}\n")
        print("Please copy/paste this into your email client or adjust as needed.\n")
    else:
        print("Failed to generate a draft reply.")

def bulk_summarize_and_process(limit=None):
    """
    Processes every email in MAIN_INBOX in a single pass:
      1. Applies any existing filter rules first.
      2. Summarizes and recommends an action for each email not yet moved.
      Optionally processes only a limited number of emails if 'limit' is provided.
      In interactive mode, prompts for a limit if not provided.
    """
    print("Applying filter rules first...")
    apply_filter_rules(MAIN_INBOX)
    remaining_emails = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    if not remaining_emails:
        print("No emails left in inbox after filter rules.")
        return
    if limit is None:
        user_limit = input("Enter number of emails to process (or press Enter for all): ").strip()
        if user_limit.isdigit():
            limit = int(user_limit)
    if limit is not None:
        remaining_emails = remaining_emails[:limit]
    print("\nSummarizing all remaining emails...")
    for email_file in remaining_emails:
        summarize_specific_email(email_file)

def bulk_summarize_and_process_silent(num_emails=None):
    """
    Processes emails in MAIN_INBOX in silent mode (no user prompts during processing).
    It collects all GPT responses and recommended actions without executing them immediately.
    Optionally processes only a limited number of emails if num_emails is provided.
    After processing, it provides a summary overview and prompts the user to execute all recommended actions.
    """
    print("Applying filter rules first...")
    apply_filter_rules(MAIN_INBOX)
    remaining_emails = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    if not remaining_emails:
        print("No emails left in inbox after filter rules.")
        return
    if num_emails is not None:
        remaining_emails = remaining_emails[:num_emails]
    results = []
    print("\nProcessing emails silently...")
    for email_file in remaining_emails:
        result = summarize_specific_email(email_file, silent=True)
        if result:
            results.append(result)
    if not results:
        print("No emails processed.")
        return
    print("\n--- Summary Overview ---")
    for res in results:
        action_to_execute = res["recommended_action"]
        display_action = action_to_execute if action_to_execute != "REVIEW" else "REVIEW (flagged for manual review)"
        print(f"Email: {res['email_file']} | From: {res['sender']} | Subject: {res['subject']} | Recommended Action: {res['recommended_action']} (to be executed as {display_action})")
    
    confirm = input("\nExecute all recommended actions? (yes/no): ").strip().lower()
    if confirm == "yes":
        for res in results:
            action = res["recommended_action"]
            if action == "ARCHIVE":
                move_email_with_category(res["email_file"], ARCHIVE_DIR, res["category"])
                print(f"Email {res['email_file']} archived.")
            elif action == "DELETE":
                move_email_with_category(res["email_file"], TRASH_DIR, res["category"])
                print(f"Email {res['email_file']} moved to trash.")
            elif action == "REPLY":
                generate_draft_reply(email_file=res["email_file"], view_original=False, view_reply=False, send=True)
                print(f"Reply sent for {res['email_file']}.")
            elif action == "REVIEW":
                move_email_with_category(res["email_file"], FOLLOWUP_DIR, res["category"])
                print(f"Email {res['email_file']} moved to review folder.")
            else:
                print(f"No action taken for {res['email_file']}.")
    else:
        print("No actions executed.")

