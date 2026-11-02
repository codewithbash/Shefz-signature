import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL is missing. Create a .env file (copy .env.example).")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "234XXXXXXXXXX")
    # Email (leave MAIL_SERVER empty while testing: emails are printed in the terminal instead)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_FROM = os.environ.get("MAIL_FROM", "") or os.environ.get("MAIL_USERNAME", "")
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15 MB per request (several photos)
