
# search_emails.py
import os
import re
from datetime import datetime
import subprocess
from utils import parse_email
from config import MAIN_INBOX

def search_emails(keyword):
    inbox_path = MAIN_INBOX
    email_files = [f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))]
    
    if not email_files:
        print("No emails found in inbox.")
        return
    
    email_list = []
    lines = []
    date_range_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})\s*(to|-)\s*(\d{4}-\d{2}-\d{2})')
    single_date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    filter_by_date = False
    start_date = end_date = None
    if date_range_pattern.search(keyword):
        m = date_range_pattern.search(keyword)
        start_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        end_date = datetime.strptime(m.group(3), "%Y-%m-%d")
        filter_by_date = True
    elif single_date_pattern.match(keyword):
        start_date = datetime.strptime(keyword, "%Y-%m-%d")
        end_date = start_date
        filter_by_date = True

    for email_file in email_files:
        file_path = os.path.join(inbox_path, email_file)
        subject, sender, _, date_str, date_obj = parse_email(file_path)
        if filter_by_date:
            if date_obj is None:
                continue
            email_date = date_obj.date()
            if not (start_date.date() <= email_date <= end_date.date()):
                continue
        line = f"From: {sender} | Subject: {subject} | Date: {date_str} | File: {email_file}"
        lines.append(line)
        email_list.append((email_file, sender, subject, date_str))
    
    if not lines:
        print(f"No emails found matching the criteria '{keyword}'.")
        return

    try:
        process = subprocess.Popen(
            ["fzf", "--query", keyword],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        input_data = "\n".join(lines)
        output, _ = process.communicate(input=input_data)
        if output:
            parts = output.strip().split(" | ")
            selected_file = None
            for part in parts:
                if part.startswith("File: "):
                    selected_file = part.replace("File: ", "").strip()
                    break
            if selected_file:
                print(f"Selected email: {selected_file}")
            else:
                print("No email selected.")
        else:
            print("No email selected.")
    except Exception as e:
        print(f"Fuzzy search failed: {e}")

