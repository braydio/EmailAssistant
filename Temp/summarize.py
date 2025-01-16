import os
import shutil
from utils import parse_email, send_notification
from gpt_api import ask_gpt

def summarize_all_unread_emails():
    inbox_path = os.path.expanduser("~/.mail/Gmail/RecentInbox/new")
    email_files = [os.path.join(inbox_path, f) for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No new emails found.")
        return

    for email_file in email_files:
        summarize_specific_email(email_file)

def summarize_specific_email(email_file):
    inbox_path = os.path.expanduser("~/.mail/Gmail/RecentInbox/new")
    file_path = os.path.join(inbox_path, email_file)
    
    if not os.path.exists(file_path):
        print(f"Error: File '{email_file}' not found in {inbox_path}.")
        return

    subject, sender, body = parse_email(file_path)
    prompt = f"Summarize this email:\nFrom: {sender}\nSubject: {subject}\n\n{body}\n\nPlease include one of the following phrases in your response: 'ACTION: ARCHIVE' if no response is needed, or 'ACTION: KEEP' if a response is required."
    recommendation = ask_gpt(prompt)
    
    if recommendation:
        print(f"\n--- Email Summary ---\nFrom: {sender}\nSubject: {subject}\nRecommendation: {recommendation}\n")
        send_notification(subject, sender, recommendation)

        # Auto-archive or keep the email based on the GPT recommendation
        if "ACTION: ARCHIVE" in recommendation:
            archive_dir = os.path.expanduser("~/.mail/Gmail/Archive")
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, os.path.basename(email_file))
            shutil.move(file_path, archive_path)
            print(f"Email archived: {archive_path}")
        elif "ACTION: KEEP" in recommendation:
            print("This email requires action. Leaving in the inbox.")
        else:
            print("No clear recommendation. Email remains in inbox.")
    else:
        print(f"Failed to summarize or recommend an action for: {email_file}")
