"""Send email without ever breaking the page the customer is on.
If MAIL_SERVER is empty, the email is printed in the terminal (handy for testing)."""
import logging
import smtplib
import threading
from email.message import EmailMessage
from flask import current_app

log = logging.getLogger("shefz.mail")
KEYS = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD",
        "MAIL_USE_TLS", "MAIL_USE_SSL", "MAIL_FROM")


def send_email(to, subject, body):
    if not to:
        return
    cfg = {k: current_app.config.get(k) for k in KEYS}
    if not (cfg["MAIL_SERVER"] and cfg["MAIL_FROM"]):
        print(f"\n----- EMAIL NOT SENT (mail not set up) -----\nTo: {to}\nSubject: {subject}\n\n{body}\n--------------------------------------------\n")
        return
    threading.Thread(target=_send, args=(cfg, to, subject, body), daemon=True).start()


def _send(cfg, to, subject, body):
    try:
        msg = EmailMessage()
        msg["From"] = f"SHEFz Signature <{cfg['MAIL_FROM']}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if cfg["MAIL_USE_SSL"]:
            server = smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=15)
        else:
            server = smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=15)
            if cfg["MAIL_USE_TLS"]:
                server.starttls()
        with server:
            if cfg["MAIL_USERNAME"]:
                server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            server.send_message(msg)
    except Exception:
        log.exception("Could not send email to %s", to)
