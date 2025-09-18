import os
import smtplib
import ssl
import json
from email.message import EmailMessage

async def send_email(receiver_email, code, discord_name, discord_id):
    """Sends the verification code to the user's email."""
    email_sender = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASS')
    email_receiver = receiver_email

    subject = "Your Discord Verification Code"
    body = f"""
    Hello {discord_name} (ID: {discord_id}),

    Your verification code for the Discord server is: {code}

    Please use the !verify command in the verification channel to complete the process.
    Example: !verify {code}
    """

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls(context=context)
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def load_config(filename='serverlink.json'):
    """Loads the configuration from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The configuration file '{filename}' was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The configuration file '{filename}' is not valid JSON.")
        return []

# Load the configuration data once when the script starts
server_configs = load_config()

def get_control_server_id(server_id_to_find: str) -> str | None:
    """Finds a server's control server channel ID from the config."""
    for config in server_configs:
        if config.get("serverID") == server_id_to_find:
            return config.get("controlServerID")
    return None

def is_verification_channel(channel_id_to_check: str) -> bool:
    """Checks if the given channel ID is a designated verification channel."""
    for config in server_configs:
        if config.get("verificationChannelID") == channel_id_to_check:
            return True
    return False