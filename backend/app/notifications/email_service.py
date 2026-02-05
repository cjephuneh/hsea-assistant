"""Send emails via SMTP. Configure MAIL_* in .env. Supports Gmail, SendGrid, etc."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.config import Config


def send_email(to_email: str, subject: str, body: str, attachments=None):
    """
    Send an email. attachments: list of (filename, bytes, content_type).
    Returns (True, None) on success, (False, error_message) on failure.
    """
    if Config.MAIL_SUPPRESS_SEND:
        if Config.MAIL_DEBUG:
            print(f"[MAIL_SUPPRESS_SEND] Would send to {to_email}: {subject}")
        return True, None
    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        return False, "Email is not configured. Set MAIL_USERNAME and MAIL_PASSWORD in .env"
    attachments = attachments or []
    try:
        msg = MIMEMultipart()
        msg["From"] = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        for filename, data, ctype in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)
        if Config.MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=Config.MAIL_TIMEOUT)
        else:
            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=Config.MAIL_TIMEOUT)
        try:
            if Config.MAIL_USE_TLS and not Config.MAIL_USE_SSL:
                server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
        finally:
            server.quit()
        return True, None
    except Exception as e:
        return False, str(e)
