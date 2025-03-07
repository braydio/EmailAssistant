import os
import shutil
from utils import parse_email
from config import MAIN_INBOX, ARCHIVE_DIR

def review_suggestions():
    inbox_path = MAIN_INBOX
    email_files = [os.path.join(inbox_path, f) for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No new emails found.")
        return

    for email_file in email_files:
        subject, sender, _, date_str, _ = parse_email(email_file)
        print(f"\nFrom: {sender} | Date: {date_str}\nSubject: {subject}")
        action = input("Action (archive/delete/skip): ").strip().lower()
        
        if action == "archive":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            archive_path = os.path.join(ARCHIVE_DIR, os.path.basename(email_file))
            shutil.move(email_file, archive_path)
            print(f"Email archived: {archive_path}")
        elif action == "delete":
            os.remove(email_file)
            print(f"Email deleted: {email_file}")
        else:
            print("Skipped.")

