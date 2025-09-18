import os
import smtplib
import ssl
from email.message import EmailMessage

async def send_email(receiver_email, code, discord_name, discord_id):
    """Sends the verification code to the user's email."""
    email_sender = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASS')
    email_receiver = receiver_email

    subject = "Your Discord Verification Code"
    body = f"""
    Hello {discord_name}, ID: {discord_id},

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
        # Use the standard SMTP class for port 587
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            # Upgrade the plain text connection to a secure one
            smtp.starttls(context=context)
            
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

import json

def load_config(filename='serverlink.json'):
    """Loads the configuration from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return [] # Return an empty list on error

# Load the configuration data once when the script starts
server_configs = load_config()

def get_control_server_id(server_id_to_find: str) -> str | None:
    """
    Finds a server object by its ID and returns the control server ID.

    Args:
        server_id_to_find: The serverID to search for.

    Returns:
        The controlServerID as a string if a match is found, otherwise None.
    """
    # Loop through each server configuration in the list
    for config in server_configs:
        # Check if the 'serverID' in the current config matches the one we're looking for
        if config.get("serverID") == server_id_to_find:
            # If it matches, return the corresponding 'controlServerID'
            return config.get("controlServerID")
    
    # If the loop finishes without finding a match, return None
    return None

def is_verification_channel(channel_id_to_check: str) -> bool:
    """
    Checks if the given channel ID is the verification channel for the specified server ID.

    Args:
        channel_id_to_check: The channel ID to check.
    Returns:
        True if the channel ID matches the verification channel for the server, otherwise False.
    """

    for config in server_configs:
        try:
            if config.get("verificationChannelID") == channel_id_to_check:
                return True
        except KeyError:
            continue
    return False
