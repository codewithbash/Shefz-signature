"""Order helpers shared by the customer and admin sides."""


def restock(order):
    """Put ready-made stock back when an order is cancelled."""
    for item in order.items:
        p = item.product
        if p and p.availability_type == "ready_made" and p.stock_quantity is not None:
            was_zero = p.stock_quantity == 0
            p.stock_quantity += item.quantity
            if was_zero and p.stock_status == "sold_out":
                p.stock_status = "available"
