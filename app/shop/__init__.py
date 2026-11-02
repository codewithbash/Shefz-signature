from flask import Blueprint

bp = Blueprint("shop", __name__)

from app.shop import routes  # noqa: E402,F401
