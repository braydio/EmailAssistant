
# review_marked.py v1.0.0
import os
import shutil
from utils import parse_email
from config import FOLLOWUP_DIR, ARCHIVE_DIR
from draft_reply import generate_draft_reply

def review_marked_emails():
    """
    Reviews emails that have been marked for review by ChatGPT.
    Each email (with HTML/CSS stripped) is displayed, and the user is prompted to:
      1. Reply (calls the draft reply generator with sending enabled)
      2. Delete the email
      3. Archive the email (move to ARCHIVE_DIR)
      4. Skip (take no action)
    """
    email_files = [f for f in os.listdir(FOLLOWUP_DIR) if os.path.isfile(os.path.join(FOLLOWUP_DIR, f))]
    if not email_files:
        print("No emails found in the review folder.")
        return

    for email_file in email_files:
        file_path = os.path.join(FOLLOWUP_DIR, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        print("\n-------------------------")
        print(f"Email File: {email_file}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Date: {date_str}")
        print("-------------------------")
        print(f"Email Body:\n{body}\n")
        print("Select an action for this email:")
        print("1. Reply")
        print("2. Delete")
        print("3. Archive")
        print("4. Skip")
        action_choice = input("Enter your choice (1-4): ").strip()
        if action_choice == "1":
            # Generate a draft reply and send it
            generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=True)
        elif action_choice == "2":
            try:
                os.remove(file_path)
                print(f"Email {email_file} deleted.")
            except Exception as e:
                print(f"Error deleting email {email_file}: {e}")
        elif action_choice == "3":
            try:
                os.makedirs(ARCHIVE_DIR, exist_ok=True)
                dest_path = os.path.join(ARCHIVE_DIR, email_file)
                shutil.move(file_path, dest_path)
                print(f"Email {email_file} archived.")
            except Exception as e:
                print(f"Error archiving email {email_file}: {e}")
        else:
            print("Skipping email.")
