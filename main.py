# main.py v. 1.0.0
import os
from config import MAIN_INBOX, ARCHIVE_DIR, FOLLOWUP_DIR, TRASH_DIR
from summarize import (
    summarize_all_unread_emails, 
    summarize_specific_email, 
    bulk_summarize_and_process, 
    bulk_summarize_and_process_silent,
    apply_filter_rules, 
    reply_to_email,
    search_emails
)
from manual_review import review_suggestions, manual_review_process
from draft_reply import generate_draft_reply
from mail_rules import interactive_rule_application
from batch_cleanup import batch_cleanup_analysis
# Import new module for reviewing marked emails
import review_marked

def count_emails(directory):
    return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])

def print_email_status():
    inbox_count = count_emails(MAIN_INBOX)
    archive_count = count_emails(ARCHIVE_DIR)
    review_count = count_emails(FOLLOWUP_DIR)
    trash_count = count_emails(TRASH_DIR)
    print("\n=== Email Status ===")
    print(f"Inbox: {inbox_count}")
    print(f"Archive: {archive_count}")
    print(f"Review: {review_count}")
    print(f"Trash: {trash_count}")
    print("====================\n")

def clear_archive():
    """
    Clears all emails in the archive folder.
    """
    email_files = [f for f in os.listdir(ARCHIVE_DIR) if os.path.isfile(os.path.join(ARCHIVE_DIR, f))]
    if not email_files:
        print("Archive folder is already empty.")
        return
    confirm = input("Are you sure you want to clear the Archive folder? This will delete all archived emails. (yes/no): ").strip().lower()
    if confirm == "yes":
        for email_file in email_files:
            file_path = os.path.join(ARCHIVE_DIR, email_file)
            try:
                os.remove(file_path)
                print(f"Deleted archived email: {email_file}")
            except Exception as e:
                print(f"Error deleting {email_file}: {e}")
        print("Archive folder cleared.")
    else:
        print("Clear archive cancelled.")

def main():
    print("Welcome to the Email Assistant!")
    print_email_status()
    while True:
        print("\nOptions:")
        print("1. Summarize all unread emails")
        print("2. Silent Bulk Summarize and Process a range of emails")
        print("3. Fuzzy Find an email for reply (Interactive)")
        print("4. Generate and send a draft reply (Legacy)")
        print("5. Check Reviewed Emails (Marked for review by ChatGPT)")
        print("6. Search emails by keyword/date")
        print("7. Apply Filter Rules (Interactive)")
        print("8. Apply Mail Rule (Interactive)")
        print("9. Batch Cleanup Analysis (Top 3 Senders)")
        print("10. Manual Review Process (with Embedding)")
        print("11. Clear Archive Box")
        print("0. Exit")
        
        choice = input("Choose an option: ").strip()
        if choice == "1":
            summarize_all_unread_emails()
        elif choice == "2":
            num = input("Enter number of emails to process silently (or press Enter for all): ").strip()
            num_emails = int(num) if num.isdigit() else None
            bulk_summarize_and_process_silent(num_emails)
        elif choice == "3":
            reply_to_email()  # This function already performs fuzzy selection if no email is specified.
        elif choice == "4":
            print("\nGenerating and sending draft reply (legacy)...")
            generate_draft_reply(send=True)
        elif choice == "5":
            review_marked.review_marked_emails()
        elif choice == "6":
            keyword = input("Enter keyword or date (YYYY-MM-DD) / range (YYYY-MM-DD to YYYY-MM-DD): ").strip()
            search_emails(keyword)
        elif choice == "7":
            apply_filter_rules(MAIN_INBOX)
        elif choice == "8":
            interactive_rule_application()
        elif choice == "9":
            batch_cleanup_analysis()
        elif choice == "10":
            try:
                num = int(input("Enter number of emails to review manually: ").strip())
            except ValueError:
                print("Invalid number.")
                num = 0
            if num > 0:
                manual_review_process(num)
        elif choice == "11":
            clear_archive()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        print_email_status()

if __name__ == "__main__":
    main()

