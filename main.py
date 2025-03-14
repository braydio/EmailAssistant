# main.py
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

def main():
    print("Welcome to the Email Assistant!")
    print_email_status()
    while True:
        print("\nOptions:")
        print("1. Summarize all unread emails")
        print("2. Summarize a specific email")
        print("3. Review email suggestions manually")
        print("4. Generate and send a draft reply (legacy)")
        print("5. Bulk Summarize and Process Emails (Interactive)")
        print("6. Apply Filter Rules (Interactive)")
        print("7. Reply to Email (Interactive)")
        print("8. Search emails by keyword/date")
        print("9. Apply mail rule (Interactive)")
        print("10. Batch cleanup analysis (Top 3 Senders)")
        print("11. Silent Bulk Summarize and Process")
        print("12. Manual Review Process (with Embedding)")
        print("0. Exit")
        
        choice = input("Choose an option: ").strip()
        if choice == "1":
            summarize_all_unread_emails()
        elif choice == "2":
            file_name = input("Enter the email file name: ").strip()
            summarize_specific_email(file_name)
        elif choice == "3":
            review_suggestions()
        elif choice == "4":
            print("\nGenerating and sending draft reply (legacy)...")
            generate_draft_reply(send=True)
        elif choice == "5":
            bulk_summarize_and_process()
        elif choice == "6":
            apply_filter_rules()
        elif choice == "7":
            reply_to_email()
        elif choice == "8":
            keyword = input("Enter keyword or date (YYYY-MM-DD) / range (YYYY-MM-DD to YYYY-MM-DD): ").strip()
            search_emails(keyword)
        elif choice == "9":
            from mail_rules import interactive_rule_application
            interactive_rule_application()
        elif choice == "10":
            from batch_cleanup import batch_cleanup_analysis
            batch_cleanup_analysis()
        elif choice == "11":
            num = input("Enter number of emails to process silently (or press Enter for all): ").strip()
            num_emails = int(num) if num.isdigit() else None
            bulk_summarize_and_process_silent(num_emails)
        elif choice == "12":
            try:
                num = int(input("Enter number of emails to manually review: ").strip())
            except ValueError:
                print("Invalid number.")
                num = 0
            if num > 0:
                manual_review_process(num)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        print_email_status()

if __name__ == "__main__":
    main()

