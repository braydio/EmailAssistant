

import os
import shutil
from utils import parse_email, send_notification, fuzzy_select_email, record_filter_rule
from gpt_api import ask_gpt
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, SPAM_DIR

def list_emails_for_summary(inbox_path=MAIN_INBOX):
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
    inbox_path = MAIN_INBOX
    email_files = [os.path.join(inbox_path, f) for f in os.listdir(inbox_path)
                   if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No new emails found.")
        return

    for email_file in email_files:
        summarize_specific_email(os.path.basename(email_file))

def summarize_specific_email(email_file=None):
    inbox_path = MAIN_INBOX

    if not email_file:
        email_info = list_emails_for_summary(inbox_path)
        if not email_info:
            return
        print("\nAvailable Emails:")
        for idx, sender, subject, email_file, date_str in email_info:
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
        return

    subject, sender, body, date_str, _ = parse_email(file_path)
    prompt = (
        f"Please summarize the following email and provide a clear recommendation for sorting. "
        f"Consider that emails can be sorted into the following boxes: Inbox (if a response is required), "
        f"Archive (if no response is needed), or Spam (if the email appears to be unsolicited or malicious). "
        f"Include exactly one of the following phrases as the final line of your summary: "
        f"'ACTION: ARCHIVE', 'ACTION: KEEP', or 'ACTION: SPAM'. "
        f"Plese note that trade confirmations or financial statement availabilities, or one-time passcodes, should be archived."
        f"If you select 'ACTION: SPAM', please also include a suggested rule to automatically flag similar emails as spam. "
        f"For example: 'RULE: If sender contains \"example-spam.com\" or subject contains \"free money\", then flag as spam.'\n\n"
        f"Email Details:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n{body}"
    )
    recommendation = ask_gpt(prompt)
    
    if recommendation:
        print(f"\n--- Email Summary ---\nFrom: {sender} | Date: {date_str}\nSubject: {subject}\nRecommendation: {recommendation}\n")
        send_notification(subject, sender, recommendation)

        if "ACTION: ARCHIVE" in recommendation:
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            archive_path = os.path.join(ARCHIVE_DIR, os.path.basename(email_file))
            shutil.move(file_path, archive_path)
            print(f"Email archived: {archive_path}")
        elif "ACTION: KEEP" in recommendation:
            follow_up = input("Would you like to mark this email for follow-up? (yes/no): ").strip().lower()
            if follow_up == "yes":
                os.makedirs(FOLLOWUP_DIR, exist_ok=True)
                followup_path = os.path.join(FOLLOWUP_DIR, os.path.basename(email_file))
                shutil.move(file_path, followup_path)
                print(f"Email moved to follow-up folder: {followup_path}")
            elif follow_up == "no":
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                archive_path = os.path.join(ARCHIVE_DIR, os.path.basename(email_file))
                shutil.move(file_path, archive_path)
                print(f"Email archived: {archive_path}")
            else:
                print("Email remains in the inbox for further action.")
        elif "ACTION: SPAM" in recommendation:
            # Check for a suggested filter rule
            rule_line = None
            for line in recommendation.splitlines():
                if line.strip().startswith("RULE:"):
                    rule_line = line.strip()
                    break
            if rule_line:
                record_filter_rule(rule_line)
            os.makedirs(SPAM_DIR, exist_ok=True)
            spam_path = os.path.join(SPAM_DIR, os.path.basename(email_file))
            shutil.move(file_path, spam_path)
            print(f"Email moved to spam folder: {spam_path}")
        else:
            print("No clear recommendation. Email remains in inbox.")
    else:
        print(f"Failed to summarize or recommend an action for: {email_file}")

