
# draft_reply.py
import os
import subprocess
from utils import parse_email, fuzzy_select_email
from gpt_api import ask_gpt
from config import MAIN_INBOX, SENT_EMAIL
from display import console

def list_emails(inbox_path=MAIN_INBOX):
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    if not email_files:
        console.print("No new emails found.")
        return None

    email_info = []
    for i, email_file in enumerate(email_files):
        subject, sender, _, date_str, _ = parse_email(os.path.join(inbox_path, email_file))
        email_info.append([i + 1, sender, subject, email_file, date_str])

    console.print("\nAvailable Emails:")
    for idx, sender, subject, _, date_str in email_info:
        console.print(f"{idx}. From: {sender} | Subject: {subject} | Date: {date_str}")
    return email_info

def generate_draft_reply(email_file=None, view_original=True, view_reply=True, send=False):
    inbox_path = MAIN_INBOX
    
    if email_file is None:
        email_list = list_emails(inbox_path)
        if not email_list:
            return
        
        user_input = input("\nEnter the number of the email to reply to (or press Enter to search): ").strip()
        if user_input == "":
            email_file = fuzzy_select_email(email_list)
            if not email_file:
                console.print("No email selected via fuzzy search.")
                return
        else:
            try:
                selection = int(user_input) - 1
                if 0 <= selection < len(email_list):
                    email_file = email_list[selection][3]
                else:
                    console.print("Invalid number. Please choose a valid email number.")
                    return
            except ValueError:
                console.print("Invalid input. Please enter a number or press Enter for fuzzy search.")
                return

    file_path = os.path.join(inbox_path, email_file)
    if not os.path.exists(file_path):
        console.print(f"Error: File '{email_file}' not found.")
        return

    subject, sender, body, date_str, _ = parse_email(file_path)

    if view_original:
        console.print(f"\n--- Original Message ---\nFrom: {sender} | Date: {date_str}\nSubject: {subject}\n\n{body}\n")

    prompt = (
        f"Compose a draft response to the following email:\n\n"
        f"From: {sender}\nSubject: {subject}\n\n{body}\n\n"
        f"Please provide a clear and professional response."
    )
    draft_reply_text = ask_gpt(prompt)
    
    if draft_reply_text:
        if view_reply:
            console.print(f"\n--- Drafted Reply ---\n{draft_reply_text}\n")

        if send:
            console.print(f"Sending email to: {sender}...")
            send_email_with_msmtp(sender, subject, draft_reply_text)
        else:
            replies_dir = os.path.join(os.path.dirname(__file__), "replies")
            os.makedirs(replies_dir, exist_ok=True)
            draft_file = os.path.join(replies_dir, f"reply_{os.path.basename(email_file)}.txt")
            with open(draft_file, "w") as f:
                f.write(draft_reply_text)
            console.print(f"Draft reply saved as: {draft_file}")
    else:
        console.print("Failed to generate a draft reply.")

def send_email_with_msmtp(to_email, subject, body):
    email_content = f"From: {SENT_EMAIL}\nTo: {to_email}\nSubject: Re: {subject}\n\n{body}"
    try:
        subprocess.run(
            ["msmtp", "-a", "gmail", to_email],
            input=email_content.encode("utf-8"),
            check=True
        )
        console.print(f"Email sent successfully to {to_email}!")
    except subprocess.CalledProcessError as e:
        console.print(f"Error sending email: {e}")

