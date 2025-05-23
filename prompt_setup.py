
def get_summary_prompt(sender, date_str, subject, body):
    SUMMARY_PROMPT = (
            "You are Brayden's email assistant. You summarize emails and decide how they are handled.\n"
            "In your summary include any requests, deadlines, or important context.\n"
            "Your number one priority is to minimize the number of emails that Brayden sees.\n"
            "BUT if Brayden misses even ONE important email then you will be immediately FIRED and Brayden will lose his home.\n"

            "Also, Brayden is severely allergic to emails and, even seeing 5 emails in one day could kill him.\n\n"
            "At the end of every summary write a single line with one of the below\n ACTION:INDICATOR\n"
            "ACTION:ARCHIVE,\n ACTION:REVIEW,\n ACTION:DELETE,\n ACTION:REPLY\n"
            f"EMAIL DETAILS:\nFrom: {sender}\nSubject: {subject}\nDate: {date_str}\n\n"
            f"{body}\n\n"
            "If there are any actions, tasks, or urgent items mentioned, please highlight them."
            "\n\nRemember to ACTION:DELETE as many emails as you can so that Brayden doesn't die."
        )
    if SUMMARY_PROMPT:
        print("Succesfully built summary prompt.")
        return SUMMARY_PROMPT

def get_action_prompt(summary_content):
    ACTION_PROMPT = (
            "Read the below email summary and decide whether the email should be DELETE, ARCHIVE, REVIEW, or requires a REPLY.\n"
            "Respond with ONLY TWO WORDS from the ACTION:INDICATOR table:\n"
            "ACTION:INDICATOR\n"
            "ACTION:DELETE — if this email is of little importance, is spam, or can be ignored.\n"
            "ACTION:REPLY — if this email directly requires an email response.\n"
            "ACTION:REVIEW — if it needs review but no reply.\n"
            "ACTION:ARCHIVE — if it's informational OR if you do not know.\n\n"
            f"Summary:\n{summary_content}\n\n"
            "In 2 words tell me what is the ACTION:INDICATOR?"
        )
    if ACTION_PROMPT:
        print("Succesfully built action prompt.")
        return ACTION_PROMPT
