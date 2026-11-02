from flask import render_template
from app.extensions import db
from app.main import bp
from app.models import Product


@bp.route("/")
def home():
    try:
        featured = (Product.query.filter_by(is_active=True, is_featured=True)
                    .order_by(Product.created_at.desc()).limit(4).all())
    except Exception:  # tables not created yet: still show the page
        db.session.rollback()
        featured = []
    return render_template("main/home.html", featured=featured)


@bp.route("/delivery")
def delivery():
    return render_template("main/delivery.html")
