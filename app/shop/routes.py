from flask import render_template, request, abort
from app.shop import bp
from app.models import Product, Category


@bp.route("/")
def index():
    categories = Category.query.filter_by(is_active=True).all()
    current = request.args.get("category", "")
    sort = request.args.get("sort", "newest")

    q = Product.query.filter_by(is_active=True)
    if current:
        q = q.join(Category).filter(Category.slug == current)
    if sort == "price_low":
        q = q.order_by(Product.price.asc())
    elif sort == "price_high":
        q = q.order_by(Product.price.desc())
    else:
        q = q.order_by(Product.created_at.desc())
    return render_template("shop/collection.html", products=q.all(),
                           categories=categories, current=current, sort=sort)


@bp.route("/<slug>")
def detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first()
    if product is None:
        abort(404)
    return render_template("shop/product_detail.html", p=product)
