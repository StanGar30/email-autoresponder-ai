# Guff AutoResponder

This project is an automated email responder written in Python. It connects to an **IMAP server** to fetch incoming mail and uses an **SMTP server** to send replies. A detailed log of activities is saved in `autoresponder.log`.


## 📥 Getting Started  
1. **Clone this repository:**  
   ```bash
   git clone https://github.com/StanGar30/Guff-AutoResponder.git
   cd Guff-AutoResponder

## Features

### Authorization
- Connects to the IMAP server using login and password specified in `main.py`.
- Uses the same credentials for the SMTP server to send replies.

### Checking Emails
- Processes unread emails in batches, limiting the total number checked (up to 100).
- Each iteration reads up to 8 new emails.
- Analyzes the body of each email for spam and additional information.

### Ignoring Emails
- Includes a list of senders that should never receive an automatic reply.
- Skips replying to system-related addresses and adds any spam sender to the ignore list.

### Spam Handling
- Supports calling an OpenAI model to detect unwanted mail.
- **Important:** For reliable spam detection, a specialized, trained model is strongly recommended.

### Generating Replies
- Optionally composes a response for each email, based on its content.
- Sends messages via SMTP, then stores details in the local history (`response_history.json`).

### History and Cleanup
- Avoids duplicate replies by checking the local history.
- Automatically cleans old entries exceeding a set threshold (30 days by default).

## Installation and Execution

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

## 📂 Project Structure  
```bash
├── 📄 main.py              # Main script for the autoresponder
├── 📄 requirements.txt     # Dependencies
├── 📄 .gitignore           # Ignored files list
├── 📄 autoresponder.log    # Log file (auto-generated)
├── 📄 response_history.json # Stores processed emails(auto-generated)
├── 📄 LICENSE              # License file
├── 📄 README.md            # This file
```

## Contact
- **Name:** Stanislav Garipov
- **Email:** stanislavgaripov93@gmail.com
- [GitHub Profile](https://github.com/StanGar30)

## License
This project is licensed under the [MIT License](LICENSE).


