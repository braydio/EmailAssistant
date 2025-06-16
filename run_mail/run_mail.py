# usr/bin/env python3
import datetime
import os
import shutil
import sys
from email.parser import BytesParser
from email.policy import default
from glob import glob

import openai
from dotenv import load_dotenv

# ─── load config ───────────────────────────────────────────────────────────────
load_dotenv()
MAILDIR = os.getenv("MAILDIR_ROOT", os.path.expanduser("~/.mail/Gmail"))
API_KEY = os.getenv("OPENAI_API_KEY", "")
API_BASE = os.getenv("LOCAL_API_URL", "")  # e.g. http://192.168.1.238:5000/v1
REPORT_PATH = os.getenv("REPORT_PATH", "/reports/email_report.md")

openai.api_key = API_KEY
if API_BASE:
    openai.api_base = API_BASE

# ─── maildirs ────────────────────────────────────────────────────────────────
DIRS = {
    "INBOX": os.path.join(MAILDIR, "Inbox"),
    "IMPORTANT": os.path.join(MAILDIR, "Important"),
    "SPAM": os.path.join(MAILDIR, "Spam"),
    "TRASH": os.path.join(MAILDIR, "Trash"),
    "OUTBOX": os.path.join(MAILDIR, "Outbox"),
}
for d in DIRS.values():
    os.makedirs(os.path.join(d, "new"), exist_ok=True)
    os.makedirs(os.path.join(d, "cur"), exist_ok=True)

# ─── classification & reply ──────────────────────────────────────────────────
counts = {"JUNK": 0, "REVIEW": 0, "REPLY": 0}


def classify_email(subject: str, body: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an email triage assistant.  "
                + "Given Subject and Body, reply with exactly one of: JUNK, REVIEW, or REPLY.",
            },
            {"role": "user", "content": f"Subject: {subject}\n\n{body}"},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip().upper()


def draft_reply(subject: str, body: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an email assistant.  Draft a concise reply to the email below.",
            },
            {"role": "user", "content": f"Subject: {subject}\n\n{body}"},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ─── process inbox ───────────────────────────────────────────────────────────
def process_folder(src_dir):
    for sub in ("new", "cur"):
        pattern = os.path.join(src_dir, sub, "*")
        for path in glob(pattern):
            try:
                with open(path, "rb") as f:
                    msg = BytesParser(policy=default).parse(f)
            except Exception:
                # If even parsing fails, treat as junk
                label = "JUNK"
                subject = ""
                body = ""
            else:
                subject = msg.get("subject", "")
                textpart = msg.get_body(preferencelist=("plain",))
                body = textpart.get_content() if textpart else ""
                label = classify_email(subject, body)
            counts[label] += 1

            # decide dest folder
            if label == "JUNK":
                dest = DIRS["TRASH"]
            elif label == "REVIEW":
                dest = DIRS["IMPORTANT"]
            else:  # REPLY
                dest = DIRS["OUTBOX"]

            # move file
            dst_sub = "cur"  # keep everything in cur so you can open it easily
            os.makedirs(os.path.join(dest, dst_sub), exist_ok=True)
            shutil.move(path, os.path.join(dest, dst_sub, os.path.basename(path)))

            # if reply, generate draft
            if label == "REPLY":
                draft = draft_reply(subject, body)
                draft_fn = os.path.join(
                    dest, dst_sub, f"reply_{os.path.basename(path)}.txt"
                )
                with open(draft_fn, "w") as dr:
                    dr.write(
                        f"To: {msg.get('from', '')}\nSubject: Re: {subject}\n\n{draft}"
                    )


# ─── run & write report ───────────────────────────────────────────────────────
if __name__ == "__main__":
    process_folder(DIRS["INBOX"])
    # optional: also scan AllMail instead of Inbox
    # process_folder(os.path.join(MAILDIR,"AllMail"))

    # write summary
    today = datetime.date.today().isoformat()
    with open(REPORT_PATH, "w") as r:
        r.write(f"# Email Summary – {today}\n\n")
        for label in ("JUNK", "REVIEW", "REPLY"):
            r.write(f"- **{label}**: {counts[label]}\n")
    sys.exit(0)
