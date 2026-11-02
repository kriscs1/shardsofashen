"""Email from the central server (a new account's welcome, a forgotten password's code), through any mail service's
SMTP (the standard library's smtplib): DS_SMTP_HOST, DS_SMTP_PORT (587), DS_SMTP_USER, DS_SMTP_PASSWORD, DS_SMTP_FROM,
and DS_SMTP_TLS (starttls, the default; ssl for port 465; none). Without DS_SMTP_HOST there's no email, and the recovery
code is the only way back in.

  python -m central.mail you@example.com      (a test email, or why it didn't go)"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

SENT = []                       # (tests: what would have gone, when DS_SMTP_HOST is "test")


def ready():
    return bool(os.environ.get("DS_SMTP_HOST", "").strip())


def message(to, subject, text):
    """One plain-text email, with the Date and Message-ID that mail services want (smtplib adds neither)."""
    sender = os.environ.get("DS_SMTP_FROM", "") or os.environ.get("DS_SMTP_USER", "")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(usegmt=True)
    msg["Message-ID"] = make_msgid(domain=parseaddr(sender)[1].rpartition("@")[2] or None)
    msg.set_content(text)
    return msg


def send(to, subject, text):
    """Sends one plain-text email (blocking: call it from a thread). Raises if the mail service says no."""
    host = os.environ.get("DS_SMTP_HOST", "").strip()
    if host == "test":
        SENT.append((to, subject, text))
        return
    msg = message(to, subject, text)
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


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("Which address? python -m central.mail you@example.com")
    if not ready():
        sys.exit("No email: DS_SMTP_HOST isn't set.")
    try:
        send(sys.argv[1], "Shards of Ashen: a test email", "The central server can send email.\n")
    except Exception as e:
        sys.exit("It didn't go: %s: %s" % (type(e).__name__, e))
    print("Sent to %s. Look in its spam folder too." % sys.argv[1])
