

# manual_review.py
import os
import shutil
import json
from datetime import datetime
from utils import parse_email
from config import MAIN_INBOX, ARCHIVE_DIR, TRASH_DIR, FOLLOWUP_DIR
from embedding import send_embedding

def review_suggestions():
    """
    Legacy manual review process (unchanged).
    """
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

def manual_review_process(num_emails):
    """
    Performs manual review for a specified number of emails from MAIN_INBOX.
    For each email, displays details and prompts the reviewer to select one of:
      ACTION: REPLY, ACTION: DELETE, ACTION: REVIEW, ACTION: ARCHIVE.
    The review decision is logged in a structured JSON format and then sent to the embedding endpoint.
    """
    inbox_files = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    if not inbox_files:
        print("No emails found in inbox for manual review.")
        return

    review_log = []  # Collect log entries

    emails_to_review = inbox_files[:num_emails]
    for email_file in emails_to_review:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, body, date_str, _ = parse_email(file_path)
        print("\n-------------------------")
        print(f"Email File: {email_file}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Date: {date_str}")
        print("-------------------------")
        print("Select an action for this email:")
        print("1. ACTION: REPLY   - Email requires a reply.")
        print("2. ACTION: DELETE  - Email should be deleted.")
        print("3. ACTION: REVIEW  - Email should be manually reviewed (flagged).")
        print("4. ACTION: ARCHIVE - Email should be archived (no further action).")
        action_choice = input("Enter your choice (1-4): ").strip()
        if action_choice == "1":
            chosen_action = "ACTION: REPLY"
        elif action_choice == "2":
            chosen_action = "ACTION: DELETE"
        elif action_choice == "3":
            chosen_action = "ACTION: REVIEW"
        elif action_choice == "4":
            chosen_action = "ACTION: ARCHIVE"
        else:
            print("Invalid choice, defaulting to ACTION: REVIEW.")
            chosen_action = "ACTION: REVIEW"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "email_file": email_file,
            "sender": sender,
            "subject": subject,
            "date": date_str,
            "chosen_action": chosen_action,
            "timestamp": timestamp
        }
        review_log.append(log_entry)

        # Execute the chosen action
        if chosen_action == "ACTION: DELETE":
            try:
                os.remove(file_path)
                print("Email deleted.")
            except Exception as e:
                print(f"Error deleting email: {e}")
        elif chosen_action == "ACTION: ARCHIVE":
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            dest_path = os.path.join(ARCHIVE_DIR, email_file)
            shutil.move(file_path, dest_path)
            print("Email archived.")
        elif chosen_action == "ACTION: REVIEW":
            os.makedirs(FOLLOWUP_DIR, exist_ok=True)
            dest_path = os.path.join(FOLLOWUP_DIR, email_file)
            shutil.move(file_path, dest_path)
            print("Email moved to review (follow-up).")
        elif chosen_action == "ACTION: REPLY":
            print("Action set to reply; no automatic reply generated in manual review.")
        else:
            print("No action taken.")

    # Save the review log to a file
    log_file = os.path.join("manual_review_log.json")
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(review_log, f, indent=2)
        print(f"Manual review log saved to {log_file}")
    except Exception as e:
        print(f"Error saving manual review log: {e}")

    # Send the log to the embedding endpoint
    embedding_response = send_embedding(review_log)
    if embedding_response:
        print("Manual review log successfully sent to embedding endpoint.")
    else:
        print("Failed to send manual review log to embedding endpoint.")

if __name__ == "__main__":
    try:
        num = int(input("Enter number of emails to review manually: ").strip())
    except ValueError:
        print("Invalid number.")
        num = 0
    if num > 0:
        manual_review_process(num)

