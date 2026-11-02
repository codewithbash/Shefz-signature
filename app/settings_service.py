"""Read and write the admin-editable settings (bank details, WhatsApp number)."""
import re
from urllib.parse import urlparse
from flask import current_app, g
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import Setting

KEYS = ("bank_name", "account_number", "account_name", "whatsapp_number", "payment_note",
        "notification_email", "instagram_url", "tiktok_url", "facebook_url", "x_url")


def normalise_whatsapp(raw):
    """'0808 723 4718' or '+234 808 723 4718' -> '2348087234718'. Returns '' if not valid."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = "234" + digits[1:]
    return digits if 10 <= len(digits) <= 15 else ""


def normalise_url(raw):
    """'' if empty, a clean https link if valid, None if not a usable web address."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in ("http", "https") or "." not in parsed.netloc or " " in raw:
        return None
    return raw


def load_settings():
    """All settings as a dict. Cached for the request. If the settings table does not
    exist yet (flask init-db not run), the site still works using the .env number."""
    if "shop_settings" in g:
        return g.shop_settings
    data = {k: "" for k in KEYS}
    data["whatsapp_number"] = current_app.config.get("WHATSAPP_NUMBER", "")
    try:
        for row in Setting.query.all():
            if row.key in data and (row.value or row.key != "whatsapp_number"):
                data[row.key] = row.value or ""
    except SQLAlchemyError:
        db.session.rollback()
    g.shop_settings = data
    return data


def save_settings(values):
    for key in KEYS:
        if key not in values:
            continue
        row = db.session.get(Setting, key)
        if row is None:
            row = Setting(key=key, value="")
            db.session.add(row)
        row.value = values[key] or ""
    db.session.commit()
    g.pop("shop_settings", None)
