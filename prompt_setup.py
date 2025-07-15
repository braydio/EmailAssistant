def get_summary_prompt(sender, date_str, subject, body):
    SUMMARY_PROMPT = (
        "Review this email, give a brief summary, identify any requests, deadlines, or important context.\n"
        "You DO NOT want Brayden to review an email UNLESS it is *very* important.\n"
        "This is because Brayden has a dangerous allergy to emails.\n"
        "If he reviews more than 5 emails in one day, he will DIE!\n\n"
        "END your response with one of the following actions: \n\n"
        "\nACTION:ARCHIVE,\nACTION:REVIEW,\nACTION:DELETE,\nACTION:REPLY\n\n"
        f"EMAIL DETAILS:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n"
        f"{body}\n\n"
        "\nWhat do you recommend?"
        "\n\n!WARNING! BRAYDEN HAS REVIEWED 5 EMAILS TODAY"
        "\nTHE NEXT EMAIL REVIEW WILL KILL HIM"
        "\n\nIS THIS EMAIL WORTH HIS LIFE??\n"
    )
    if SUMMARY_PROMPT:
        print("Succesfully built summary prompt.")
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
        print("Succesfully built action prompt.")
        return ACTION_PROMPT
