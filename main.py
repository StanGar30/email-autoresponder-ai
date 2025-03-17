import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import json
import os
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from collections import deque

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='autoresponder.log'
)

# Define the GuffAutoResponder class to handle the autoresponder logic and email processing
class GuffAutoResponder:
    def __init__(self, address, password, imap_server, imap_port, smtp_server, smtp_port, interval, prompt_template, dont_answer, max_length, days):
        """Initializes the autoresponder with the specified settings"""

        # Email настройки
        self.email_address = address
        self.email_password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

        self.check_interval = interval

        self.prompt_template = prompt_template
        self.dont_answer = deque(dont_answer, maxlen=max_length)

        self.response_history = {}
        self.history_file = 'response_history.json'
        self.load_response_history()
        self.clean_old_history(days)

    # Load the response history from the JSON file
    def load_response_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.response_history = json.load(f)
            except Exception as e:
                logging.error(f"Error loading response history: {e}")
                self.response_history = {}

    # Save the response history to the JSON file
    def save_response_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.response_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving response history: {e}")

    # Clean up the old history entries
    def clean_old_history(self, days):
        """Cleans up old history entries"""
        now = datetime.now()
        cutoff = (now - timedelta(days=days)).timestamp()

        cleaned_history = {k: v for k, v in self.response_history.items()
                           if v.get('timestamp', 0) > cutoff}

        if len(cleaned_history) != len(self.response_history):
            self.response_history = cleaned_history
            self.save_response_history()
            logging.info(f"Historical data cleaned up, {len(self.response_history)} entries remaining")

    # Check the email for spam(You need better AI model for this and you can use the OpenAI API)
    def spam_check(self, email_data):
        """Checks the email for spam"""
        # Construct the email prompt
        prompt_template = "From: {sender}\nSubject: {subject}\n\n{body}"

        # Format the prompt with the email data
        prompt = prompt_template.format(
            sender=email_data['sender'],
            subject=email_data['subject'],
            body=email_data['body']
        )

        logging.info(f"Checking for spam: {email_data['sender']}")
        try:
            client = OpenAI(
                api_key="your-api-key",
                base_url="https://api.example.com"  # Specify the base URL for your model
            )
            full_response = ""
            # Create a request with streaming output and you need to specify prompts
            response = client.chat.completions.create(
                model="your-model-name",  # Specify your model name
                messages=[
                    {"role": "system",
                     "content": "Analyze the email and respond with only one word: 'SPAM' if it is spam/advertisement, or 'NORMAL' if it is a regular email"},
                    {"role": "user", "content": prompt}
                ],
                stream=True  # Set to True for streaming output
            )

            # Process the chunks as they come in
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content

            # Check the full response for the spam label
            full_response = full_response.strip().upper()
            print(f"Result: {full_response}")

            # Add the sender to the ignore list if the email is marked as spam
            if email_data['sender'].lower() not in self.dont_answer and full_response == "SPAM":
                self.dont_answer.append(email_data['sender'].lower())  # Add the sender to the ignore list

            return full_response == "SPAM"
        except Exception as e:
            logging.error(f"Error checking for spam: {e}")
            return None

    # Generate a response to the email
    def generate_response(self, email_data):
        """Generates a response to the email"""
        # Construct the email prompt
        prompt_template = "From: {sender}\nSubject: {subject}\n\n{body}"

        # Format the prompt with the email data
        prompt = prompt_template.format(
            sender=email_data['sender'],
            subject=email_data['subject'],
            body=email_data['body']
        )

        logging.info(f"Running response generation for {email_data['sender']}")
        try:
            client = OpenAI(
                api_key="your-api-key", # Specify your API key
                base_url="https://api.example.com"  # Specify the base URL for your model
            )
            # Create a request with streaming output
            response = client.chat.completions.create(
                model="your-model-name",  # Specify your model name
                messages=[
                    {"role": "system", "content": self.prompt_template},
                    {"role": "user", "content": prompt}
                ],
                stream=True  # Set to True for streaming output
            )

            full_response = ""
            # Process the chunks as they come in
            for chunk in response:
                if chunk.choices[0].delta.content:  # Проверяем, есть ли данные в чанке
                    full_response += chunk.choices[0].delta.content
                    print(chunk.choices[0].delta.content, end="", flush=True)

            print("\nFull response:", full_response)

            # Check the full response for the spam label
            if "SPAM" in full_response and email_data['sender'].lower() not in self.dont_answer:
                self.dont_answer.append(email_data['sender'].lower())  # Add the sender to the ignore list

            return full_response
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return None

    # Connect to the email server
    def connect_to_email(self):
        """Connects to the email server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')
            logging.info("Connected to email server")
            return mail
        except Exception as e:
            logging.error(f"Error connecting to email server: {e}")
            return None

    # Get the unread emails
    def get_unread_emails(self):
        """Checks for unread emails"""
        mail = self.connect_to_email()
        if not mail:
            return []

        try:
            # Check for unread emails and get the email IDs
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()

            email_ids.reverse()  # Latest emails first
            email_ids = email_ids[:100]  # Limit the number of emails to process
            processed_ids = set()  # Create a set to store processed email IDs

            # Check if the current email position is set
            if not hasattr(self, 'current_email_position'):
                self.current_email_position = 0

            # Get the start and end index for the email IDs and update the position(8 emails at a time)
            start_index = self.current_email_position
            end_index = min(start_index + 8, len(email_ids))

            # Update the current email position
            self.current_email_position = end_index

            # If the start index exceeds the email count, reset the position
            if start_index >= len(email_ids):
                self.current_email_position = 0
                start_index = 0
                end_index = min(8, len(email_ids))

            email_data = []
            logging.info(f"Emails to process: {start_index}-{end_index}")

            # Process the emails in batches of 8 and add them to the email data list
            for e_id in email_ids[start_index:end_index]:
                e_id_str = e_id.decode()
                if e_id_str in processed_ids:
                    continue
                processed_ids.add(e_id_str)

                print(f'Processing email {e_id}')
                # Fetch the email data
                status, msg_data = mail.fetch(e_id, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract the sender, subject, message ID, and body
                sender = email.utils.parseaddr(msg['From'])[1]
                subject = msg['Subject']
                message_id = msg['Message-ID'] or f"{sender}_{subject}_{e_id.decode()}"

                # Create an empty body string
                body = ""
                if msg.is_multipart():                                                      # If the message is multipart
                    for part in msg.walk():                                                 # Iterate over the parts
                        content_type = part.get_content_type()                              # Content type of the part
                        if content_type == "text/plain":                                    # If the content type is text/plain
                            body = part.get_payload(decode=True).decode(errors='ignore')    # Get the payload
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')

                # Body length limit
                body = body[:4000]

                # Add the email data to the list
                email_data.append({
                    'id': e_id,
                    'message_id': message_id,
                    'sender': sender,
                    'subject': subject,
                    'body': body
                })
            mail.logout()
            return email_data

        except Exception as e:
            logging.error(f"Error processing emails: {e}")
            try:
                mail.logout()
            except:
                pass
            return []

    # Check if a response is needed
    def should_respond(self, email_data):
        """Checks if a response is needed"""

        # Don`t answer if the sender is in the ignore list or the email is from a no-reply address
        if "noreply" in email_data['sender'].lower() or \
                "donotreply" in email_data['sender'].lower() or \
                "mailer-daemon" in email_data['sender'].lower() or \
                any([x in email_data['sender'].lower() for x in self.dont_answer]) or \
                email_data['sender'].lower() == self.email_address.lower():
            print("Ответ не требуется")
            return False

        # Check if the email has already been responded to
        if email_data['message_id'] in self.response_history and self.response_history[
            email_data['message_id']].get('responded'):
            print("Ответ уже отправлен")
            return False

        # Check for spam
        if self.spam_check(email_data):
            print("Письмо определено как спам")
            return False

        return True

    # Send an automatic response
    def send_response(self, email_data, response_text):
        """Send an automatic response to the email"""
        try:
            msg = MIMEMultipart()                           # Create a MIME multipart message
            msg['From'] = self.email_address                # Set the sender
            msg['To'] = email_data['sender']                # Set the recipient
            msg['Subject'] = f"Re: {email_data['subject']}" # Set the subject
            msg['In-Reply-To'] = email_data['message_id']   # Set the in-reply-to header
            msg['References'] = email_data['message_id']    # Set the references header

            msg.attach(MIMEText(response_text, 'plain', 'utf-8'))   # Attach the response text
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:      # Connect to the SMTP server
                server.login(self.email_address, self.email_password)               # Login to the server
                server.send_message(msg)                                            # Send the message

            # Save the response history
            self.response_history[email_data['message_id']] = {
                'sender': email_data['sender'],
                'subject': email_data['subject'],
                'timestamp': datetime.now().timestamp(),
                'responded': True
            }
            self.save_response_history()

            logging.info(f"Answer sent to {email_data['sender']}, subject: {email_data['subject']}")
            return True

        except Exception as e:
            logging.error(f"E-mail sending error: {e}")
            return False

    # Run the autoresponder
    def run(self):
        """General autoresponder loop"""
        logging.info(f"Autoresponder started, for email: {self.email_address}")

        while True:
            try:
                logging.info("Checking for new emails...")
                unread_emails = self.get_unread_emails()    # Get the unread emails

                # Process the unread emails
                for email_data in unread_emails:
                    # Check if a response is needed
                    if self.should_respond(email_data):
                        logging.info(f"E-mail from {email_data['sender']}, subject: {email_data['subject']}")
                        # Generate a response
                        response = self.generate_response(email_data)
                        # Send the response
                        if response:
                            self.send_response(email_data, response)
                    else:
                        logging.info(f"Passthrough email from {email_data['sender']}, subject: {email_data['subject']}")

                # Interval cleanup of the response history
                self.clean_old_history(days)

            except Exception as e:
                logging.error(f"Error in the main loop: {e}")

            # Await the next check interval
            time.sleep(self.check_interval)


if __name__ == "__main__":
    address = ""                        # You email address
    password = ""                       # Passwort for the email account
    imap_server = "imap.example.com"    # IMAP server
    imap_port = 993                     # Port for SSL
    smtp_server = "smtp.example.com"    # SMTP server
    smtp_port = 465                     # Port for SSL
    interval = 10                       # Emails check interval in seconds
    max_length = 50                     # Max length of the dont_answer list
    days = 30                           # Days to keep the response history

    # Example prompt template
    prompt_template = """Below is an email to which you need to compose a polite professional response.
                        Focus on the content of the email and provide specific information if possible.
                        Check for spam and advertisements and respond with only one word: 'SPAM' if it is spam/advertisement.
                        Check again for advertisements and spam, no mistakes are allowed."""

    # List of emails to ignore("noreply", "donotreply", "mailer-daemon")
    dont_answer = [
        "noreply", "donotreply", "mailer-daemon"
    ]

    # Email autoresponder instance
    autoresponder = GuffAutoResponder(address, password, imap_server, imap_port, smtp_server, smtp_port, interval, prompt_template, dont_answer, max_length, days)
    autoresponder.run()