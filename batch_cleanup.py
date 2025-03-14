
import os
from collections import Counter, defaultdict
from config import MAIN_INBOX
from utils import parse_email
from gpt_api import ask_gpt

def batch_cleanup_analysis():
    """
    Batch together the three most frequent email senders and the associated emails
    (filenames, date, subject) and send them to ChatGPT with a request to determine
    which emails can be deleted.
    """
    # List all email files in the main inbox.
    email_files = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    if not email_files:
        print("No emails found in the main inbox.")
        return

    # Build frequency counts and group emails by sender.
    sender_counts = Counter()
    sender_emails = defaultdict(list)

    for email_file in email_files:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, _, date_str, _ = parse_email(file_path)
        sender_counts[sender] += 1
        sender_emails[sender].append({
            'filename': email_file,
            'subject': subject,
            'date': date_str
        })

    # Get the top three most frequent senders.
    top_senders = sender_counts.most_common(3)
    if not top_senders:
        print("No sender information found.")
        return

    # Construct the details message.
    message_details = "Top 3 Most Frequent Email Senders and Their Emails:\n\n"
    for sender, count in top_senders:
        message_details += f"Sender: {sender} (Total Emails: {count})\n"
        for email_info in sender_emails[sender]:
            message_details += (
                f"  - Filename: {email_info['filename']}, Date: {email_info['date']}, "
                f"Subject: {email_info['subject']}\n"
            )
        message_details += "\n"

    # Create the prompt for ChatGPT.
    prompt = (
        f"I have a batch of emails from the top 3 most frequent senders:\n\n"
        f"{message_details}\n"
        f"Based on the above information, please determine which of these emails can be deleted. "
        f"Provide a list of filenames for each sender that are candidates for deletion and briefly explain the reasoning."
    )

    print("Sending batch cleanup analysis to ChatGPT...")
    response = ask_gpt(prompt)
    if response:
        print("\nChatGPT Recommendation for Cleanup:")
        print(response)
    else:
        print("Failed to receive a response from ChatGPT.")

if __name__ == "__main__":
    batch_cleanup_analysis()
