"""Session cart. The session only stores product ids and choices. Every price is
looked up from the database each time, so a customer can never change a price."""
import uuid
from decimal import Decimal
from flask import session
from app.extensions import db
from app.models import Product

MAX_PER_LINE = 10


def _raw():
    return session.get("cart", [])


def _save(items):
    session["cart"] = items
    session.modified = True


def max_qty(product):
    if product.availability_type == "ready_made" and product.stock_quantity is not None:
        return max(0, min(MAX_PER_LINE, product.stock_quantity))
    return MAX_PER_LINE


def validate_choice(product, size, colour, making, qty):
    """Return (clean_choice, error). Never trust what the browser sent."""
    if product is None or not product.is_active:
        return None, "That product is not available."
    if not product.can_order:
        return None, f"{product.name} is {product.availability_label.lower()}."
    sizes, colours = product.size_list, product.colour_list
    if sizes and size not in sizes:
        return None, "Please choose a size."
    if colours and colour not in colours:
        return None, "Please choose a colour."
    if product.availability_type == "ready_made":
        making = "ready"
    elif making == "express" and product.express_available:
        making = "express"
    else:
        making = "standard"
    cap = max_qty(product)
    if cap < 1:
        return None, f"{product.name} is out of stock."
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        qty = 1
    qty = max(1, min(qty, cap))
    return {"size": size if sizes else "", "colour": colour if colours else "",
            "making": making, "qty": qty}, None


def add_item(product, choice):
    items = _raw()
    for line in items:
        if (line["product_id"] == product.id and line["size"] == choice["size"]
                and line["colour"] == choice["colour"] and line["making"] == choice["making"]):
            line["qty"] = min(line["qty"] + choice["qty"], max_qty(product))
            _save(items)
            return
    items.append({"id": uuid.uuid4().hex[:8], "product_id": product.id, **choice})
    _save(items)


def set_qty(line_id, qty):
    items = _raw()
    for line in items:
        if line["id"] == line_id:
            line["qty"] = max(1, min(int(qty), MAX_PER_LINE))
    _save(items)


def remove_item(line_id):
    _save([l for l in _raw() if l["id"] != line_id])


def clear():
    session.pop("cart", None)


def count():
    return sum(l.get("qty", 0) for l in _raw())


def build():
    """Return a dict: lines, subtotal, express_total, total, ok.
    Each line has .problem set if it can no longer be ordered."""
    raw = _raw()
    ids = [l["product_id"] for l in raw]
    products = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()} if ids else {}
    lines, subtotal, express_total = [], Decimal(0), Decimal(0)
    for l in raw:
        p = products.get(l["product_id"])
        problem = None
        if p is None or not p.is_active:
            problem = "No longer available."
        elif not p.can_order:
            problem = f"Now {p.availability_label.lower()}."
        elif l["qty"] > max_qty(p):
            problem = f"Only {max_qty(p)} left in stock."
        fee = Decimal(p.express_fee or 0) if (p and l["making"] == "express") else Decimal(0)
        price = Decimal(p.price) if p else Decimal(0)
        line_total = (price + fee) * l["qty"]
        if not problem:
            subtotal += price * l["qty"]
            express_total += fee * l["qty"]
        lines.append({**l, "product": p, "unit_price": price, "express_fee": fee,
                      "line_total": line_total, "problem": problem})
    return {"lines": lines, "subtotal": subtotal, "express_total": express_total,
            "total": subtotal + express_total,
            "ok": bool(lines) and not any(x["problem"] for x in lines)}
