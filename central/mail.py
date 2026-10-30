"""Email from the central server (a forgotten password's code), through any mail service's SMTP (the standard
library's smtplib): DS_SMTP_HOST, DS_SMTP_PORT (587), DS_SMTP_USER, DS_SMTP_PASSWORD, DS_SMTP_FROM, and DS_SMTP_TLS
(starttls, the default; ssl for port 465; none). Without DS_SMTP_HOST there's no email, and the recovery code is the
only way back in."""
import os
import smtplib
import ssl
from email.message import EmailMessage

SENT = []                       # (tests: what would have gone, when DS_SMTP_HOST is "test")


def ready():
    return bool(os.environ.get("DS_SMTP_HOST", "").strip())


def send(to, subject, text):
    """Sends one plain-text email (blocking: call it from a thread). Raises if the mail service says no."""
    host = os.environ.get("DS_SMTP_HOST", "").strip()
    if host == "test":
        SENT.append((to, subject, text))
        return
    msg = EmailMessage()
    msg["From"] = os.environ.get("DS_SMTP_FROM", "") or os.environ.get("DS_SMTP_USER", "")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    port = int(os.environ.get("DS_SMTP_PORT", "587"))
    tls = os.environ.get("DS_SMTP_TLS", "starttls").lower()
    if tls == "ssl":
        server = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        if tls == "starttls":
            server.starttls(context=ssl.create_default_context())
    with server:
        if os.environ.get("DS_SMTP_USER"):
            server.login(os.environ["DS_SMTP_USER"], os.environ.get("DS_SMTP_PASSWORD", ""))
        server.send_message(msg)
