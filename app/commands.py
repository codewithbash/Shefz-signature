import click
from app.extensions import db
from app.models import User, Category, Product


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create any missing tables (safe to run again; it never deletes data)."""
        db.create_all()
        click.echo("Database tables are up to date.")

    @app.cli.command("seed")
    def seed():
        """Add demo categories and products."""
        if Category.query.first():
            click.echo("Already seeded.")
            return
        cats = {}
        for name, slug in [("Footwear", "footwear"), ("Bags", "bags"), ("Belts", "belts")]:
            cats[slug] = Category(name=name, slug=slug)
            db.session.add(cats[slug])
        db.session.flush()

        def p(cat, name, price, **kw):
            base = dict(category_id=cats[cat].id, name=name,
                        slug=name.lower().replace(" ", "-"), price=price,
                        description="Handmade in Lagos from premium leather, made to your size.",
                        colours="Black,Brown,Tan", is_featured=False)
            base.update(kw)
            db.session.add(Product(**base))

        mto = dict(availability_type="made_to_order", express_available=True)
        p("footwear", "Lagos Loafer", 85000, production_days=7, express_days=3, express_fee=10000, sizes="40,41,42,43,44,45", is_featured=True, **mto)
        p("footwear", "Abuja Sandal", 55000, production_days=5, express_days=2, express_fee=7000, sizes="38,39,40,41,42,43", **mto)
        p("footwear", "Ikoyi Oxford", 98000, production_days=10, express_days=5, express_fee=12000, sizes="40,41,42,43,44,45", **mto)
        p("bags", "Signature Tote", 120000, production_days=10, express_days=5, express_fee=15000, sizes="Medium,Large", is_featured=True, **mto)
        p("bags", "Evening Clutch", 68000, production_days=7, express_days=3, express_fee=8000, sizes="One size", colours="Black,Gold,Cream", is_featured=True, **mto)
        p("bags", "Travel Duffel", 150000, availability_type="ready_made", stock_quantity=3, sizes="One size", colours="Black")
        p("belts", "Classic Belt", 35000, production_days=5, express_days=2, express_fee=5000, sizes="S,M,L,XL", colours="Black,Brown", is_featured=True, **mto)
        p("belts", "Gold Buckle Belt", 42000, availability_type="ready_made", stock_status="sold_out", stock_quantity=0, sizes="M,L", colours="Black")
        db.session.commit()
        click.echo("Demo data added.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin(name, email, password):
        """Create the first admin account."""
        if User.query.filter_by(email=email.lower()).first():
            click.echo("That email already exists.")
            return
        u = User(full_name=name, email=email.lower(), role="admin")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo("Admin created.")
