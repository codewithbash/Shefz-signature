import re
from flask import render_template, redirect, url_for, flash, request, abort
from app.admin import bp
from datetime import datetime
from app.admin.forms import ProductForm, SettingsForm
from app.admin.uploads import save_product_image, delete_image_file
from app.decorators import admin_required
from app.extensions import db
from app.models import (Product, ProductImage, Category, User, Order,
                        ORDER_STATUSES, PAYMENT_STATUSES, ORDER_STATUS_LABELS)
from app.orders.service import restock
from app.settings_service import load_settings, save_settings, normalise_whatsapp, normalise_url

STATUSES = ("available", "sold_out", "unavailable")


def make_slug(name, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "product"
    slug, n = base, 2
    while True:
        found = Product.query.filter_by(slug=slug).first()
        if not found or found.id == ignore_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


def apply_form(product, form):
    product.name = form.name.data.strip()
    product.category_id = form.category_id.data
    product.description = form.description.data
    product.price = form.price.data
    product.availability_type = form.availability_type.data
    product.stock_status = form.stock_status.data
    product.stock_quantity = form.stock_quantity.data
    product.sizes = (form.sizes.data or "").strip()
    product.colours = (form.colours.data or "").strip()
    product.is_featured = form.is_featured.data
    product.is_active = form.is_active.data
    if product.availability_type == "made_to_order":
        product.production_days = form.production_days.data
        product.express_available = form.express_available.data
        product.express_days = form.express_days.data if form.express_available.data else None
        product.express_fee = form.express_fee.data if form.express_available.data else None
    else:  # ready-made: no waiting time, no express
        product.production_days = None
        product.express_available = False
        product.express_days = None
        product.express_fee = None
        if product.stock_quantity == 0 and product.stock_status == "available":
            product.stock_status = "sold_out"


def save_uploads(product):
    files = [f for f in request.files.getlist("images") if f and f.filename]
    saved = 0
    for f in files:
        try:
            path = save_product_image(f)
        except ValueError as e:
            flash(str(e), "error")
            continue
        first = not product.images
        db.session.add(ProductImage(product_id=product.id, image_path=path,
                                    alt_text=product.name, is_primary=first,
                                    sort_order=len(product.images) + saved))
        saved += 1
    if saved:
        db.session.commit()
        flash(f"{saved} photo(s) uploaded.", "success")


@bp.route("/")
@admin_required
def dashboard():
    recent = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html",
                           product_count=Product.query.count(),
                           customer_count=User.query.filter_by(role="customer").count(),
                           new_orders=Order.query.filter_by(status="pending").count(),
                           unpaid_orders=Order.query.filter(Order.payment_status == "unpaid",
                                                            Order.status != "cancelled").count(),
                           in_production=Order.query.filter_by(status="in_production").count(),
                           recent=recent)


@bp.route("/products")
@admin_required
def products():
    items = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items)


def product_page(product=None):
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if request.method == "GET" and product is None:
        form.is_active.data = True
    if form.validate_on_submit():
        creating = product is None
        if creating:
            product = Product(slug=make_slug(form.name.data))
            db.session.add(product)
        apply_form(product, form)
        db.session.commit()
        save_uploads(product)
        flash("Product created." if creating else "Product saved.", "success")
        return redirect(url_for("admin.edit_product", product_id=product.id))
    return render_template("admin/product_form.html", form=form, product=product)


@bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def new_product():
    return product_page()


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    return product_page(product)


@bp.route("/products/<int:product_id>/status", methods=["POST"])
@admin_required
def set_status(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    value = request.form.get("stock_status")
    if value not in STATUSES:
        abort(400)
    product.stock_status = value
    db.session.commit()
    flash(f"{product.name} is now {value.replace('_', ' ')}.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/products/<int:product_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_active(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    product.is_active = not product.is_active
    db.session.commit()
    flash(f"{product.name} is {'visible' if product.is_active else 'hidden'} in the shop.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/images/<int:image_id>/delete", methods=["POST"])
@admin_required
def delete_image(image_id):
    img = db.session.get(ProductImage, image_id) or abort(404)
    product_id, was_primary = img.product_id, img.is_primary
    delete_image_file(img.image_path)
    db.session.delete(img)
    db.session.commit()
    if was_primary:
        nxt = ProductImage.query.filter_by(product_id=product_id).order_by(ProductImage.sort_order).first()
        if nxt:
            nxt.is_primary = True
            db.session.commit()
    flash("Photo deleted.", "success")
    return redirect(url_for("admin.edit_product", product_id=product_id))


@bp.route("/images/<int:image_id>/primary", methods=["POST"])
@admin_required
def make_primary(image_id):
    img = db.session.get(ProductImage, image_id) or abort(404)
    for other in ProductImage.query.filter_by(product_id=img.product_id).all():
        other.is_primary = (other.id == img.id)
    db.session.commit()
    flash("Main photo updated.", "success")
    return redirect(url_for("admin.edit_product", product_id=img.product_id))


# ------------------------------------------------------------------ Orders
@bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status", "")
    payment = request.args.get("payment", "")
    q = Order.query
    if status in ORDER_STATUS_LABELS:
        q = q.filter_by(status=status)
    if payment in dict(PAYMENT_STATUSES):
        q = q.filter_by(payment_status=payment)
    items = q.order_by(Order.created_at.desc()).limit(300).all()
    return render_template("admin/orders.html", orders=items, status=status, payment=payment,
                           statuses=ORDER_STATUSES, payments=PAYMENT_STATUSES)


@bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    return render_template("admin/order_detail.html", order=order,
                           statuses=ORDER_STATUSES, payments=PAYMENT_STATUSES)


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def set_order_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    value = request.form.get("status")
    if value not in ORDER_STATUS_LABELS:
        abort(400)
    if order.status == "cancelled" and value != "cancelled":
        flash("A cancelled order cannot be reopened. Ask the customer to place a new order.", "error")
    elif value != order.status:
        if value == "cancelled":
            restock(order)
        order.status = value
        db.session.commit()
        flash(f"Order {order.order_number} is now: {ORDER_STATUS_LABELS[value]}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@bp.route("/orders/<int:order_id>/payment", methods=["POST"])
@admin_required
def set_payment_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    value = request.form.get("payment_status")
    if value not in dict(PAYMENT_STATUSES):
        abort(400)
    if order.status == "cancelled":
        flash("This order is cancelled.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    order.payment_status = value
    if value == "paid":
        order.paid_at = datetime.utcnow()
        if order.status == "pending":
            order.status = "confirmed"
    else:
        order.paid_at = None
    db.session.commit()
    flash(f"Order {order.order_number} marked {value}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


# ---------------------------------------------------------------- Settings
@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    form = SettingsForm()
    if request.method == "GET":
        for key, value in load_settings().items():
            if hasattr(form, key):
                getattr(form, key).data = value
    if form.validate_on_submit():
        save_settings({
            "bank_name": (form.bank_name.data or "").strip(),
            "account_number": (form.account_number.data or "").strip(),
            "account_name": (form.account_name.data or "").strip(),
            "whatsapp_number": normalise_whatsapp(form.whatsapp_number.data),
            "payment_note": (form.payment_note.data or "").strip(),
            "notification_email": (form.notification_email.data or "").strip().lower(),
            "instagram_url": normalise_url(form.instagram_url.data),
            "tiktok_url": normalise_url(form.tiktok_url.data),
            "facebook_url": normalise_url(form.facebook_url.data),
            "x_url": normalise_url(form.x_url.data),
        })
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", form=form)
