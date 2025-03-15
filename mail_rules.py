
# mail_rules.py
import os
import shutil
from datetime import datetime
from config import MAIN_INBOX, IMPORTANT_DIR, FOLLOWUP_DIR, SENT_DIR, FROMGPT_DIR
from draft_reply import generate_draft_reply
from utils import parse_email

def apply_rule_to_email(email_file, rule):
    file_path = os.path.join(MAIN_INBOX, email_file)
    if not os.path.exists(file_path):
        print(f"Email file {file_path} does not exist.")
        return

    action = rule.get("action", "").lower()
    if action == "delete":
        try:
            os.remove(file_path)
            print(f"Email {email_file} deleted.")
        except Exception as e:
            print(f"Error deleting {email_file}: {e}")
    elif action == "skip":
        print(f"Skipping email {email_file}.")
    elif action == "move":
        target = rule.get("target", "").lower()
        target_dir = None
        if target == "important":
            target_dir = IMPORTANT_DIR
        elif target == "followup":
            target_dir = FOLLOWUP_DIR
        elif target == "sent":
            target_dir = SENT_DIR
        elif target == "fromgpt":
            target_dir = FROMGPT_DIR
        else:
            print(f"Unknown move target: {target}. Skipping email {email_file}.")
            return
        try:
            os.makedirs(target_dir, exist_ok=True)
            dest_path = os.path.join(target_dir, os.path.basename(email_file))
            shutil.move(file_path, dest_path)
            print(f"Email {email_file} moved to {target} folder.")
        except Exception as e:
            print(f"Error moving {email_file} to {target}: {e}")
    elif action == "reply":
        send_flag = rule.get("send", False)
        generate_draft_reply(email_file=email_file, view_original=True, view_reply=True, send=send_flag)
    else:
        print(f"Unknown action: {action} for email {email_file}.")

def run_rule_on_mailbox(rule):
    email_files = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    if not email_files:
        print("No emails found in the main inbox.")
        return
    for email_file in email_files:
        apply_rule_to_email(email_file, rule)

def filter_emails(criteria):
    filtered = []
    email_files = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
    for email_file in email_files:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, _, date_str, date_obj = parse_email(file_path)
        match = True
        if criteria.get('sender'):
            if criteria['sender'].lower() not in sender.lower():
                match = False
        if criteria.get('subject'):
            if criteria['subject'].lower() not in subject.lower():
                match = False
        if criteria.get('start_date') or criteria.get('end_date'):
            if date_obj is None:
                match = False
            else:
                email_date = date_obj.date()
                if criteria.get('start_date'):
                    try:
                        start_date = datetime.strptime(criteria['start_date'], "%Y-%m-%d").date()
                    except Exception:
                        start_date = None
                    if start_date and email_date < start_date:
                        match = False
                if criteria.get('end_date'):
                    try:
                        end_date = datetime.strptime(criteria['end_date'], "%Y-%m-%d").date()
                    except Exception:
                        end_date = None
                    if end_date and email_date > end_date:
                        match = False
        if match:
            filtered.append({
                'file': email_file,
                'sender': sender,
                'subject': subject,
                'date_str': date_str
            })
    return filtered

def interactive_rule_application():
    print("Interactive Mail Rule Application")
    print("Available actions: delete, skip, move, reply")
    action = input("Enter the action to apply: ").strip().lower()
    rule = {"action": action}
    if action == "move":
        print("Available targets: important, followup, sent, fromgpt")
        target = input("Enter the target folder: ").strip().lower()
        rule["target"] = target
    elif action == "reply":
        send_input = input("Do you want to automatically send the reply? (yes/no): ").strip().lower()
        rule["send"] = send_input == "yes"
    
    print("Set filtering criteria (leave blank to skip):")
    sender_filter = input("Filter by sender (email address substring): ").strip()
    subject_filter = input("Filter by subject (substring): ").strip()
    date_filter = input("Filter by date range (format: YYYY-MM-DD to YYYY-MM-DD): ").strip()
    criteria = {}
    if sender_filter:
        criteria['sender'] = sender_filter
    if subject_filter:
        criteria['subject'] = subject_filter
    if date_filter:
        parts = date_filter.split("to")
        if len(parts) == 2:
            criteria['start_date'] = parts[0].strip()
            criteria['end_date'] = parts[1].strip()
    
    if criteria:
        filtered_emails = filter_emails(criteria)
    else:
        filtered_emails = []
        email_files = [f for f in os.listdir(MAIN_INBOX) if os.path.isfile(os.path.join(MAIN_INBOX, f))]
        for email_file in email_files:
            file_path = os.path.join(MAIN_INBOX, email_file)
            subject, sender, _, date_str, _ = parse_email(file_path)
            filtered_emails.append({
                'file': email_file,
                'sender': sender,
                'subject': subject,
                'date_str': date_str
            })
    
    if not filtered_emails:
        print("No emails match the specified criteria.")
        return
    
    print("\nMatching Emails:")
    for idx, email_info in enumerate(filtered_emails):
        print(f"{idx+1}. From: {email_info['sender']} | Subject: {email_info['subject']} | Date: {email_info['date_str']}")
    
    confirm_all = input("Apply rule to all these emails? (yes/no): ").strip().lower()
    if confirm_all == "yes":
        selected_emails = [e['file'] for e in filtered_emails]
    else:
        selection = input("Enter the numbers of emails to apply the rule (comma separated): ")
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",") if x.strip().isdigit()]
            selected_emails = []
            for i in indices:
                if 0 <= i < len(filtered_emails):
                    selected_emails.append(filtered_emails[i]['file'])
                else:
                    print(f"Invalid selection index: {i+1}")
            if not selected_emails:
                print("No valid emails selected.")
                return
        except Exception as e:
            print(f"Error during selection: {e}")
            return

    print("\nThe following emails will have the rule applied:")
    for email_file in selected_emails:
        file_path = os.path.join(MAIN_INBOX, email_file)
        subject, sender, _, date_str, _ = parse_email(file_path)
        print(f"From: {sender} | Subject: {subject} | Date: {date_str}")
    final_confirm = input("Are you sure you want to apply the rule? (yes/no): ").strip().lower()
    if final_confirm != "yes":
        print("Rule application cancelled.")
        return
    
    for email_file in selected_emails:
        apply_rule_to_email(email_file, rule)

