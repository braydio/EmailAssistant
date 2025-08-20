# EmailAssistant

Email with ChatGPT you lazy rube

## Quickstart and Setup

### 1. Clone the Repository
```bash
git clone https://github.com/braydio/EmailAssistant.git
cd EmailAssistant
```

### 2. Install Dependencies
Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root with the following:
```env
OPENAI_API_KEY=<your_openai_api_key>
EMAIL_ADDRESS=<your_email_address>
EMAIL_SMTP_PROFILE=gmail  # msmtp profile name
LOCAL_AI_IP=127.0.0.1       # Ollama host
OLLAMA_PORT=11434           # Ollama API port
```

The application defaults to using a local [Ollama](https://ollama.com) server
for language model interactions via its OpenAI-compatible `/v1` API.
Set `LOCAL_AI_IP` and `OLLAMA_PORT` to match
your environment if the defaults differ.

### 4. Configure msmtp
Ensure msmtp is configured correctly for sending emails. Example configuration in `~/.msmtprc`:
```plaintext
account gmail
host smtp.gmail.com
port 587
from <your_email_address>
auth on
user <your_email_address>
password <your_email_password>
```

### 5. Run the Application
```bash
python main.py
```

## Features
- **Email Summarization:** Summarizes unread emails and provides actionable recommendations (e.g., archive or respond).
- **Draft Replies:** Automatically generates draft replies to emails using ChatGPT.
- **Manual Review:** Allows users to review and take manual actions on emails.
- **Logging:** Tracks GPT requests and email summaries for debugging and review purposes.
- **Email Automation:** Supports automated archiving or deletion based on recommendations.

## File Structure
- `main.py`: Entry point for the application. Provides a menu-driven interface.
- `draft_reply.py`: Handles drafting and sending email replies.
- `manual_review.py`: Enables manual review and actions on emails.
- `summarize.py`: Summarizes emails and recommends actions.
- `utils.py`: Utility functions for email parsing, formatting, and notifications.
- `gpt_api.py`: Handles interactions with the ChatGPT API, including logging requests.
- `email_summaries.log`: Logs email summarization recommendations.
- `gpt_requests.log`: Logs prompts and token usage for GPT API requests.

## Usage
### Menu Options
1. **Summarize all unread emails:** Analyzes all emails in the inbox and generates summaries with recommended actions.
2. **Summarize a specific email:** Summarizes a single email file by name.
3. **Review email suggestions manually:** Lets you manually review, archive, or delete emails.
4. **Generate and send a draft reply:** Automatically drafts a reply to a selected email and optionally sends it.
5. **Exit:** Exits the application.

### Draft Reply Example
Run the following command to draft and send an email reply:
```bash
python main.py
```
Select option 4 and follow the prompts to generate and send a reply.

## Logs
- **Email Summaries:** Check `email_summaries.log` for a record of summarized emails and recommendations.
- **GPT Requests:** Check `gpt_requests.log` for a record of GPT API prompts and token counts.

## Future Enhancements
- Automatic ball-fondler module

## License
give me money license
