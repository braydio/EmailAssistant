#!/usr/bin/env python3
"""Mail processing pipeline for classification and reply drafting.

This script embeds incoming emails, classifies them, and optionally drafts
responses. It can operate against a local OpenAI-compatible API when
``LOCAL_AI_BASE_URL`` is configured.
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
from openai import OpenAI
from dotenv import load_dotenv
from config import LOCAL_AI_BASE_URL

# ─── load config ───────────────────────────────────────────────────────────────
load_dotenv()
MAILDIR = os.getenv("MAILDIR_ROOT", os.path.expanduser("~/.mail/Gmail"))
REPORT_PATH = os.getenv("REPORT_PATH", "/reports/email_report.md")
EMB_FILE = os.getenv("EMB_FILE", "/data/embeddings.jsonl")
API_KEY = os.getenv("OPENAI_API_KEY", "")
THRESH_SIM = float(os.getenv("KNN_THRESHOLD", "0.80"))

openai.api_key = API_KEY
if LOCAL_AI_BASE_URL:
    openai.api_base = LOCAL_AI_BASE_URL

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


# ─── embedding utils ──────────────────────────────────────────────────────────
def embed_text(text: str) -> list:
    """Return an embedding vector for the given text."""

    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def load_embeddings():
    embs = []
    if os.path.exists(EMB_FILE):
        for line in open(EMB_FILE):
            embs.append(json.loads(line))
    return embs


def save_embedding(subject, body, label):
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


def classify_email(subject: str, body: str) -> str:
    """Classify an email as JUNK, REVIEW, or REPLY."""

    # 1) try k-NN
    label = knn_label(subject, body, embs_db)
    if label:
        return label
    # 2) fallback to LLM
    resp = client.chat.completions.create(
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


def draft_reply(subject: str, body: str) -> str:
    """Draft a short reply using the chat completion model."""

    resp = client.chat.completions.create(
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
    for sub in ("new", "cur"):
        for path in glob(os.path.join(src, sub, "*")):
            # parse email
            try:
                msg = BytesParser(policy=default).parse(open(path, "rb"))
                subj = msg.get("subject", "")
                part = msg.get_body(preferencelist=("plain",))
                body = part.get_content() if part else ""
            except:
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
