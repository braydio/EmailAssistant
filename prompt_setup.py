from display import console


def get_summary_prompt(sender, date_str, subject, body):
    SUMMARY_PROMPT = (
        "Assess this email and summarize briefly. Highlight any critical requests, deadlines, or key context.\n"
        "Please note that the other assistants have been marking too many ACTION:REVIEW and Brayden is being inundated with emails.\n"
        "ENSURE that ONLY IMPORTANT emails are marked for REVIEW. Please note that Brayden is on top of his accounts and DOES NOT need ANY account status updates of ANY kind..\n\n"
        "Choose one final action: \n\n"
        "ACTION:ARCHIVE (If you cannot decide, DEFAULT is ACTION:ARCHIVE),\nACTION:REVIEW (Is this email really that important?),\nACTION:DELETE (delete marketing, frequent announcement's of little import etc.),\nACTION:REPLY\n\n"
        f"EMAIL DETAILS:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n"
        f"{body}\n\n"
        "\nWhat do you recommend? "
    )
    if SUMMARY_PROMPT:
        console.print("Succesfully built summary prompt.")
        return SUMMARY_PROMPT


def get_action_prompt(summary_content):
    ACTION_PROMPT = (
        "Read the below email summary and decide whether the email should be DELETE, ARCHIVE, REVIEW, or requires a REPLY.\n"
        "Respond with ONLY TWO WORDS from the ACTION:INDICATOR table:\n\n"
        "ACTION:DELETE — ALWAYS default to the SAFEST ACTION:DELETE\n"
        "ACTION:REPLY — if this email directly requires an email response.\n"
        "ACTION:REVIEW — if it needs review but no reply (CRITICALLY DANGEROUS - LAST RESORT!)\n"
        "ACTION:ARCHIVE — if it's informational OR if you do not know.\n\n"
        f"Summary:\n{summary_content}\n\n"
        "In 2 words tell me what is the ACTION:INDICATOR?\n"
    )
    if ACTION_PROMPT:
        console.print("Succesfully built action prompt.")
        return ACTION_PROMPT
