from flask import render_template, redirect, url_for, flash, request
from app.cart import bp
from app.cart import service
from app.extensions import db
from app.models import Product


@bp.route("/")
def view():
    return render_template("cart/cart.html", cart=service.build())


@bp.route("/add", methods=["POST"])
def add():
    product = db.session.get(Product, request.form.get("product_id", type=int) or 0)
    choice, error = service.validate_choice(
        product, request.form.get("size", ""), request.form.get("colour", ""),
        request.form.get("making", "standard"), request.form.get("qty", 1))
    if error:
        flash(error, "error")
        return redirect(request.referrer or url_for("shop.index"))
    service.add_item(product, choice)
    flash(f"{product.name} added to your cart.", "success")
    return redirect(url_for("cart.view"))


@bp.route("/update/<line_id>", methods=["POST"])
def update(line_id):
    service.set_qty(line_id, request.form.get("qty", 1, type=int) or 1)
    return redirect(url_for("cart.view"))


@bp.route("/remove/<line_id>", methods=["POST"])
def remove(line_id):
    service.remove_item(line_id)
    flash("Item removed.", "success")
    return redirect(url_for("cart.view"))
