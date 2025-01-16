
import os
import subprocess
from utils import parse_email
from gpt_api import ask_gpt

def list_emails(inbox_path):
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No new emails found.")
        return None

    email_info = []
    for i, email_file in enumerate(email_files):
        subject, sender, _ = parse_email(os.path.join(inbox_path, email_file))
        email_info.append([i + 1, sender, subject, email_file])

    print("\nAvailable Emails:")
    for idx, sender, subject, filename in email_info:
        print(f"{idx}. From: {sender}, Subject: {subject}")
    return email_info

def send_email_with_msmtp(to_email, subject, body):
    email_content = f"From: chaffee.brayden@gmail.com\nTo: {to_email}\nSubject: Re: {subject}\n\n{body}"
    
    try:
        subprocess.run(
            ["msmtp", "-a", "gmail", to_email],
            input=email_content.encode("utf-8"),
            check=True
        )
        print(f"Email sent successfully to {to_email}!")
    except subprocess.CalledProcessError as e:
        print(f"Error sending email: {e}")

def generate_draft_reply(email_file=None, view_original=True, view_reply=True, send=False):
    inbox_path = os.path.expanduser("~/.mail/Gmail/RecentInbox/new")
    
    if email_file is None:
        email_list = list_emails(inbox_path)
        if not email_list:
            return
        
        while True:
            try:
                selection = int(input("\nEnter the number of the email to reply to: ").strip()) - 1
                if 0 <= selection < len(email_list):
                    email_file = email_list[selection][3]
                    break
                else:
                    print("Invalid number. Please choose a valid email number.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    file_path = os.path.join(inbox_path, email_file)
    
    if not os.path.exists(file_path):
        print(f"Error: File '{email_file}' not found.")
        return

    subject, sender, body = parse_email(file_path)

    if view_original:
        print(f"\n--- Original Message ---\nFrom: {sender}\nSubject: {subject}\n\n{body}\n")

    prompt = f"Compose a draft response to the following email:\n\nFrom: {sender}\nSubject: {subject}\n\n{body}"
    draft_reply = ask_gpt(prompt)
    
    if draft_reply:
        if view_reply:
            print(f"\n--- Drafted Reply ---\n{draft_reply}\n")

        if send:
            print(f"Sending email to: {sender}...")
            send_email_with_msmtp(sender, subject, draft_reply)
        else:
            replies_dir = os.path.join(os.path.dirname(__file__), "replies")
            os.makedirs(replies_dir, exist_ok=True)
            draft_file = os.path.join(replies_dir, f"reply_{os.path.basename(email_file)}.txt")
            with open(draft_file, "w") as f:
                f.write(draft_reply)
            print(f"Draft reply saved as: {draft_file}")
    else:
        print("Failed to generate a draft reply.")
