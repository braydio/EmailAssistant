
import argparse
from summarize import summarize_all_unread_emails, summarize_specific_email
from manual_review import review_suggestions
from draft_reply import generate_draft_reply

def main():
    print("Welcome to the Email Assistant!")
    while True:
        print("\nOptions:")
        print("1. Summarize all unread emails")
        print("2. Summarize a specific email")
        print("3. Review email suggestions manually")
        print("4. Generate and send a draft reply")
        print("5. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            summarize_all_unread_emails()  # Summarizes all unread emails
        elif choice == "2":
            file_name = input("Enter the email file name: ").strip()
            summarize_specific_email(file_name)  # Summarizes a specific email
        elif choice == "3":
            review_suggestions()  # Opens manual review mode
        elif choice == "4":
            print("\nGenerating and sending draft reply...")
            generate_draft_reply(send=True)  # Ensures the reply is sent
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
