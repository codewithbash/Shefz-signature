import uuid
from urllib.parse import quote
from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from app.orders import bp
from app.orders.forms import CheckoutForm
from app.cart import service
from app.extensions import db
from app.models import Order, OrderItem, Product, UserAddress
from app.notifications import notify_new_order, notify_order_cancelled
from app.orders.service import restock
from app.settings_service import load_settings


class StockError(Exception):
    pass


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = service.build()
    if not cart["lines"]:
        flash("Your cart is empty.", "error")
        return redirect(url_for("shop.index"))
    if not cart["ok"]:
        flash("Some items in your cart need attention before you can order.", "error")
        return redirect(url_for("cart.view"))

    form = CheckoutForm()
    if not form.is_submitted():
        form.customer_name.data = current_user.full_name
        form.phone.data = current_user.phone
        saved = current_user.saved_address
        if saved:
            form.delivery_address.data = saved.address
            form.city.data = saved.city

    if form.validate_on_submit():
        try:
            order = place_order(form, cart)
        except StockError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(url_for("cart.view"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Sorry, we could not save your order. Nothing was charged. Please try again.", "error")
            return redirect(url_for("cart.view"))
        service.clear()
        remember_details(form)
        notify_new_order(order)
        flash("Order placed. Please complete your payment below.", "success")
        return redirect(url_for("orders.detail", order_number=order.order_number))
    return render_template("orders/checkout.html", form=form, cart=cart)


def remember_details(form):
    """Save the delivery details for next time. A failure here must never affect the order."""
    if not form.save_details.data:
        return
    try:
        saved = current_user.saved_address
        if saved is None:
            saved = UserAddress(user_id=current_user.id)
            db.session.add(saved)
        saved.address = form.delivery_address.data.strip()
        saved.city = form.city.data.strip()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def place_order(form, cart):
    """Save the order, its items and the stock change in ONE transaction.
    Prices come from the database (cart.build), never from the browser."""
    order = Order(order_number="TMP-" + uuid.uuid4().hex[:20], user_id=current_user.id,
                  customer_name=form.customer_name.data.strip(),
                  phone=form.phone.data.strip(),
                  delivery_address=form.delivery_address.data.strip(),
                  city=form.city.data.strip(),
                  notes=(form.notes.data or "").strip() or None,
                  subtotal=cart["subtotal"], express_total=cart["express_total"],
                  total=cart["total"])
    db.session.add(order)
    db.session.flush()  # gives the order its id
    order.order_number = f"SHZ-{order.id:05d}"

    for line in cart["lines"]:
        # Lock the product row so two customers cannot buy the last item together
        product = (Product.query.filter_by(id=line["product_id"])
                   .with_for_update().first())
        if product is None or not product.can_order or not product.is_active:
            raise StockError(f"{line['product'].name if line['product'] else 'An item'} is no longer available.")
        if product.availability_type == "ready_made" and product.stock_quantity is not None:
            if line["qty"] > product.stock_quantity:
                raise StockError(f"Sorry, only {product.stock_quantity} of {product.name} left.")
            product.stock_quantity -= line["qty"]
            if product.stock_quantity == 0:
                product.stock_status = "sold_out"
        making = line["making"]
        if product.availability_type == "ready_made":
            lead = None
        elif making == "express":
            lead = product.express_days
        else:
            lead = product.production_days
        db.session.add(OrderItem(
            order_id=order.id, product_id=product.id, product_name=product.name,
            unit_price=product.price, size=line["size"] or None, colour=line["colour"] or None,
            making_option=making, lead_days=lead, quantity=line["qty"],
            express_fee=(product.express_fee or 0) if making == "express" else 0))
    db.session.commit()
    return order


def _own_order_or_404(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first()
    return order or abort(404)


@bp.route("/")
@login_required
def history():
    orders = (Order.query.filter_by(user_id=current_user.id)
              .order_by(Order.created_at.desc()).all())
    return render_template("orders/list.html", orders=orders)


@bp.route("/<order_number>")
@login_required
def detail(order_number):
    order = _own_order_or_404(order_number)
    s = load_settings()
    msg = (f"Hello SHEFz Signature, I am sending payment for order {order.order_number}. "
           f"Name: {order.customer_name}. Amount: \u20a6{order.total:,.0f}.")
    wa_link = f"https://wa.me/{s['whatsapp_number']}?text={quote(msg)}"
    return render_template("orders/detail.html", order=order, wa_link=wa_link)


@bp.route("/<order_number>/cancel", methods=["POST"])
@login_required
def cancel(order_number):
    order = _own_order_or_404(order_number)
    if order.status != "pending" or order.payment_status != "unpaid":
        flash("This order can no longer be cancelled here. Please message us on WhatsApp.", "error")
        return redirect(url_for("orders.detail", order_number=order.order_number))
    restock(order)
    order.status = "cancelled"
    db.session.commit()
    notify_order_cancelled(order)
    flash("Your order has been cancelled.", "success")
    return redirect(url_for("orders.detail", order_number=order.order_number))
