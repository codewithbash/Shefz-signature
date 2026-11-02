import os

from flask import Flask, render_template

from config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (so migrations see the tables)
    from app.commands import register_commands
    register_commands(app)

    @app.context_processor
    def inject_css():
        # Use the Tailwind build if it exists, otherwise the plain CSS fallback
        built = os.path.exists(os.path.join(app.root_path, "static", "css", "output.css"))
        return {"css_file": "css/output.css" if built else "css/style.css"}

    @app.context_processor
    def inject_shop():
        from app.settings_service import load_settings
        from app.cart import service as cart_service
        return {"shop": load_settings(), "wa_number": load_settings()["whatsapp_number"],
                "cart_count": cart_service.count()}

    @app.template_filter("naira")
    def naira(value):
        return "\u20a6{:,.0f}".format(value or 0)

    from app.main import bp as main_bp
    from app.auth import bp as auth_bp
    from app.shop import bp as shop_bp
    from app.cart import bp as cart_bp
    from app.orders import bp as orders_bp
    from app.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(shop_bp, url_prefix="/shop")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    return app
