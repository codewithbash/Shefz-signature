from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):  # used by Flask-Login
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    products = db.relationship("Product", backref="category", lazy=True)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    # made_to_order or ready_made
    availability_type = db.Column(db.String(20), nullable=False, default="made_to_order")
    production_days = db.Column(db.Integer)           # standard making time
    express_available = db.Column(db.Boolean, default=False)
    express_days = db.Column(db.Integer)
    express_fee = db.Column(db.Numeric(12, 2))
    # available, sold_out or unavailable
    stock_status = db.Column(db.String(20), nullable=False, default="available")
    stock_quantity = db.Column(db.Integer)            # ready_made only (optional)
    sizes = db.Column(db.String(200), default="")     # comma separated, for now
    colours = db.Column(db.String(200), default="")
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    images = db.relationship("ProductImage", backref="product", lazy=True,
                             order_by="ProductImage.sort_order")

    @property
    def size_list(self):
        return [s.strip() for s in (self.sizes or "").split(",") if s.strip()]

    @property
    def colour_list(self):
        return [c.strip() for c in (self.colours or "").split(",") if c.strip()]

    @property
    def can_order(self):
        return self.stock_status == "available"

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img.image_path
        return self.images[0].image_path if self.images else None

    @property
    def availability_label(self):
        if self.stock_status == "sold_out":
            return "Sold out"
        if self.stock_status == "unavailable":
            return "Currently unavailable"
        if self.availability_type == "ready_made":
            return "Ready now"
        return f"Made for you in {self.production_days} days after payment"


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)  # path under static/
    alt_text = db.Column(db.String(150))
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)


# ---------------------------------------------------------------- Settings
class Setting(db.Model):
    """Simple key/value store the admin can edit (bank details, WhatsApp number)."""
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


# ------------------------------------------------------------------ Orders
ORDER_STATUSES = [
    ("pending", "New order"),
    ("confirmed", "Confirmed"),
    ("in_production", "In production"),
    ("ready", "Ready for delivery"),
    ("delivered", "Delivered"),
    ("cancelled", "Cancelled"),
]
PAYMENT_STATUSES = [("unpaid", "Unpaid"), ("paid", "Paid"), ("refunded", "Refunded")]
ORDER_STATUS_LABELS = dict(ORDER_STATUSES)
PAYMENT_STATUS_LABELS = dict(PAYMENT_STATUSES)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    payment_status = db.Column(db.String(20), nullable=False, default="unpaid", index=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    express_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))
    items = db.relationship("OrderItem", backref="order", lazy=True,
                            cascade="all, delete-orphan", order_by="OrderItem.id")

    @property
    def status_label(self):
        return ORDER_STATUS_LABELS.get(self.status, self.status)

    @property
    def payment_label(self):
        return PAYMENT_STATUS_LABELS.get(self.payment_status, self.payment_status)

    @property
    def longest_lead_days(self):
        days = [i.lead_days for i in self.items if i.lead_days]
        return max(days) if days else None


class OrderItem(db.Model):
    """A snapshot of what was bought. Prices and names are copied so later
    product edits never change old orders."""
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(150), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    size = db.Column(db.String(40))
    colour = db.Column(db.String(40))
    # standard, express or ready (ready-made item)
    making_option = db.Column(db.String(20), nullable=False, default="standard")
    express_fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    lead_days = db.Column(db.Integer)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")

    @property
    def line_total(self):
        return (self.unit_price + (self.express_fee or 0)) * self.quantity

    @property
    def making_label(self):
        if self.making_option == "ready":
            return "Ready now"
        kind = "Express" if self.making_option == "express" else "Standard"
        return f"{kind} making, ready in {self.lead_days} days after payment"


class UserAddress(db.Model):
    """One saved delivery address per customer (used to prefill checkout)."""
    __tablename__ = "user_addresses"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    address = db.Column(db.Text, nullable=False, default="")
    city = db.Column(db.String(80), nullable=False, default="")
    user = db.relationship("User", backref=db.backref("saved_address", uselist=False))
