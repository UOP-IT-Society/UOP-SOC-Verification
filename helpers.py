import os
import smtplib
import ssl
from email.message import EmailMessage

def send_email(receiver_email, code):
    """Sends the verification code to the user's email."""
    email_sender = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASS')
    email_receiver = receiver_email

    subject = "Your Discord Verification Code"
    body = f"""
    Hello,

    Your verification code for the Discord server is: {code}

    Please use the !verify command in the verification channel to complete the process.
    Example: !verify {code}
    """

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)

    # Add SSL for security
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
