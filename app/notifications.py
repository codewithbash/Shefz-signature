"""Emails about orders. Failures are logged, never shown to the customer."""
import logging
from flask import url_for
from app.mailer import send_email
from app.settings_service import load_settings

log = logging.getLogger("shefz.mail")


def _items_text(order):
    lines = []
    for i in order.items:
        detail = ", ".join(x for x in (f"size {i.size}" if i.size else "", i.colour or "") if x)
        lines.append(f"- {i.quantity} x {i.product_name}" + (f" ({detail})" if detail else "")
                     + f" - \u20a6{i.line_total:,.0f}\n    {i.making_label}")
    return "\n".join(lines)


def notify_new_order(order):
    try:
        s = load_settings()
        customer_link = url_for("orders.detail", order_number=order.order_number, _external=True)
        pay = ""
        if s["bank_name"] and s["account_number"]:
            pay = (f"\nPay by bank transfer:\n  Bank: {s['bank_name']}\n  Account number: {s['account_number']}\n"
                   f"  Account name: {s['account_name']}\n  Reference: {order.order_number}\n")
        send_email(order.user.email, f"Your SHEFz Signature order {order.order_number}",
                   f"Hello {order.customer_name},\n\nThank you for your order {order.order_number}.\n\n"
                   f"{_items_text(order)}\n\nTotal: \u20a6{order.total:,.0f}\n{pay}\n"
                   f"Making starts after your payment is confirmed.\nView your order: {customer_link}\n\nSHEFz Signature")
        if s["notification_email"]:
            admin_link = url_for("admin.order_detail", order_id=order.id, _external=True)
            send_email(s["notification_email"], f"New order {order.order_number} - \u20a6{order.total:,.0f}",
                       f"New order {order.order_number}\n\nCustomer: {order.customer_name}\nPhone: {order.phone}\n"
                       f"Address: {order.delivery_address}, {order.city}\n\n{_items_text(order)}\n\n"
                       f"Total: \u20a6{order.total:,.0f}\n\nOpen in admin: {admin_link}")
    except Exception:
        log.exception("Order email failed for %s", getattr(order, "order_number", "?"))


def notify_order_cancelled(order):
    try:
        to = load_settings()["notification_email"]
        if to:
            send_email(to, f"Order {order.order_number} cancelled by the customer",
                       f"{order.customer_name} ({order.phone}) cancelled order {order.order_number} "
                       f"(\u20a6{order.total:,.0f}) before payment.\nReady-made stock has been put back.")
    except Exception:
        log.exception("Cancel email failed")
