#!/usr/bin/env python3
"""Utility script for classifying and replying to emails.

This module embeds message content, labels incoming mail, and drafts
responses using either OpenAI or a local LLM based on configuration.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from email.parser import BytesParser
from email.policy import default
from glob import glob

import numpy as np
import openai
from dotenv import load_dotenv
from embedding_engine import embed_text

# ─── load config ───────────────────────────────────────────────────────────────
load_dotenv()
MAILDIR = os.getenv("MAILDIR_ROOT", os.path.expanduser("~/.mail/Gmail"))
REPORT_PATH = os.getenv("REPORT_PATH", "/reports/email_report.md")
EMB_FILE = os.getenv("EMB_FILE", "/data/embeddings.jsonl")
API_KEY = os.getenv("OPENAI_API_KEY", "")
API_BASE = os.getenv("LOCAL_API_URL", "")
THRESH_SIM = float(os.getenv("KNN_THRESHOLD", "0.80"))

openai.api_key = API_KEY
if API_BASE:
    openai.api_base = API_BASE

# ─── maildirs ────────────────────────────────────────────────────────────────
dirs = dict(
    INBOX=os.path.join(MAILDIR, "Inbox"),
    IMPORTANT=os.path.join(MAILDIR, "Important"),
    SPAM=os.path.join(MAILDIR, "Spam"),
    TRASH=os.path.join(MAILDIR, "Trash"),
    OUTBOX=os.path.join(MAILDIR, "Outbox"),
)
for d in dirs.values():
    os.makedirs(os.path.join(d, "new"), exist_ok=True)
    os.makedirs(os.path.join(d, "cur"), exist_ok=True)


def load_embeddings():
    """Return existing embeddings from ``EMB_FILE`` if it exists."""

    embs = []
    if os.path.exists(EMB_FILE):
        for line in open(EMB_FILE):
            embs.append(json.loads(line))
    return embs


def save_embedding(subject, body, label):
    """Persist an embedding and metadata for a processed email."""

    record = dict(
        subject=subject,
        body=body,
        label=label,
        emb=embed_text(subject + "\n\n" + body),
        ts=datetime.datetime.utcnow().isoformat(),
    )
    with open(EMB_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def knn_label(subject, body, embs):
    """Return the nearest-neighbor label if similarity exceeds ``THRESH_SIM``."""

    if not embs:
        return None
    query = np.array(embed_text(subject + "\n\n" + body))
    sims = [
        (
            e["label"],
            float(
                np.dot(query, e["emb"])
                / (np.linalg.norm(query) * np.linalg.norm(e["emb"]))
            ),
        )
        for e in embs
    ]
    best_label, best_sim = max(sims, key=lambda x: x[1])
    return best_label if best_sim >= THRESH_SIM else None


# ─── classification & reply ──────────────────────────────────────────────────
counts = {"JUNK": 0, "REVIEW": 0, "REPLY": 0}
embs_db = load_embeddings()


def classify_email(subject, body):
    # 1) try k-NN
    label = knn_label(subject, body, embs_db)
    if label:
        return label
    # 2) fallback to LLM
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "Triage this email into exactly one of: JUNK, REVIEW, REPLY.",
            },
            {"role": "user", "content": f"Subject: {subject}\n\n{body}"},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip().upper()


def draft_reply(subject, body):
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Draft a concise reply to this email."},
            {"role": "user", "content": f"Subject: {subject}\n\n{body}"},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ─── processing loop ─────────────────────────────────────────────────────────
def process_folder(src):
    """Process emails in ``src`` and triage them into target folders."""

    for sub in ("new", "cur"):
        for path in glob(os.path.join(src, sub, "*")):
            # parse email
            try:
                msg = BytesParser(policy=default).parse(open(path, "rb"))
                subj = msg.get("subject", "")
                part = msg.get_body(preferencelist=("plain",))
                body = part.get_content() if part else ""
            except Exception:
                subj, body = "", ""
            label = classify_email(subj, body)
            counts[label] += 1

            # record embedding
            save_embedding(subj, body, label)

            # move
            dest = {"JUNK": "TRASH", "REVIEW": "IMPORTANT", "REPLY": "OUTBOX"}[label]
            dst = os.path.join(dirs[dest], "cur", os.path.basename(path))
            shutil.move(path, dst)

            # generate reply
            if label == "REPLY":
                dr = draft_reply(subj, body)
                with open(dst.replace(".eml", ".reply.txt"), "w") as f:
                    f.write(f"To: {msg.get('from')}\nSubject: Re: {subj}\n\n{dr}")


# ─── interactive training mode ───────────────────────────────────────────────
def train_mode():
    # pick unembedded emails in Inbox/cur:
    for path in glob(os.path.join(dirs["INBOX"], "cur", "*")):
        msg = BytesParser(policy=default).parse(open(path, "rb"))
        subj = msg.get("subject", "")
        body = (msg.get_body(("plain",)) or "").get_content()
        # ask via Zenity
        choice = (
            subprocess.run(
                [
                    "zenity",
                    "--list",
                    "--title=Label this email",
                    f"--text=Subject: {subj}",
                    "--column=Label",
                    "JUNK",
                    "REVIEW",
                    "REPLY",
                ],
                capture_output=True,
            )
            .stdout.decode()
            .strip()
        )
        if choice in ("JUNK", "REVIEW", "REPLY"):
            save_embedding(subj, body, choice)
            os.remove(path)


# ─── main & report ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "train":
        train_mode()
        sys.exit(0)
    process_folder(dirs["INBOX"])
    today = datetime.date.today().isoformat()
    with open(REPORT_PATH, "w") as r:
        r.write(f"# Email Summary – {today}\n\n")
        for k in counts:
            r.write(f"- **{k}**: {counts[k]}\n")
    sys.exit(0)
