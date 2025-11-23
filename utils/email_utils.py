import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(recipient: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email using SMTP settings from app config.
    Returns True on success, False otherwise.
    """
    app = current_app._get_current_object()
    server = app.config.get("MAIL_SERVER")
    username = app.config.get("MAIL_USERNAME")
    password = app.config.get("MAIL_PASSWORD")
    port = app.config.get("MAIL_PORT", 587)
    use_tls = app.config.get("MAIL_USE_TLS", True)
    sender = app.config.get("MAIL_DEFAULT_SENDER") or username

    if not all([server, username, password, sender]):
        app.logger.warning("Email not sent: SMTP settings are incomplete.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(server, port) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # pragma: no cover - best-effort logging
        app.logger.error("Failed to send email to %s: %s", recipient, exc)
        return False

