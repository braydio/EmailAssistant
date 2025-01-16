import os
import shutil
from utils import parse_email

def review_suggestions():
    inbox_path = os.path.expanduser("~/.mail/Gmail/RecentInbox/new")
    email_files = [os.path.join(inbox_path, f) for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No new emails found.")
        return

    for email_file in email_files:
        subject, sender, _ = parse_email(email_file)
        print(f"\nFrom: {sender}\nSubject: {subject}")
        action = input("Action (archive/delete/skip): ").strip().lower()
        
        if action == "archive":
            archive_dir = os.path.expanduser("~/.mail/Gmail/Archive")
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, os.path.basename(email_file))
            shutil.move(email_file, archive_path)
            print(f"Email archived: {archive_path}")
        elif action == "delete":
            os.remove(email_file)
            print(f"Email deleted: {email_file}")
        else:
            print("Skipped.")
