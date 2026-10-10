import os
from flask import Flask, render_template
from config import config
from app.extensions import db, login_manager, csrf


def create_app(config_name="default"):
    app = Flask(__name__)

    # ── إنشاء instance قبل تحميل الـ config (SQLAlchemy يحتاج المجلد أثناء from_object)
    _instance = os.path.abspath(os.path.join(app.root_path, "..", "instance"))
    os.makedirs(_instance,                                      exist_ok=True)
    os.makedirs(os.path.join(_instance, "uploads"),             exist_ok=True)
    os.makedirs(os.path.join(_instance, "uploads", "avatars"),  exist_ok=True)
    os.makedirs(os.path.join(_instance, "backups"),             exist_ok=True)

    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Login manager config
    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
    login_manager.login_message_category = "warning"

    # User loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.modules.auth import auth_bp
    from app.modules.dashboard import dashboard_bp
    from app.modules.products import products_bp
    from app.modules.categories import categories_bp
    from app.modules.sales import sales_bp
    from app.modules.customers import customers_bp
    from app.modules.suppliers import suppliers_bp
    from app.modules.purchases import purchases_bp
    from app.modules.expenses import expenses_bp
    from app.modules.reports import reports_bp
    from app.modules.settings import settings_bp
    from app.modules.backup import backup_bp
    from app.modules.inventory import inventory_bp
    from app.modules.audit import audit_bp
    from app.modules.oil_service import oil_service_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(oil_service_bp)

    # CSRF exempt for AJAX endpoints
    csrf.exempt(sales_bp)
    csrf.exempt(purchases_bp)
    csrf.exempt(oil_service_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # Jinja2 globals
    app.jinja_env.globals["APP_NAME"] = app.config["APP_NAME"]
    app.jinja_env.globals["APP_VERSION"] = app.config["APP_VERSION"]

    # تمرير العملة لكل الصفحات
    @app.context_processor
    def inject_currency():
        from app.models.setting import Setting
        try:
            currency = Setting.get("currency", "د.ل")
        except Exception:
            currency = "د.ل"
        return {"CURRENCY": currency}

    # Init DB & defaults
    with app.app_context():
        from app.core.audit import AuditLog
        from app.models.setting import Setting
        from app.models.vehicle import Vehicle
        from app.models.oil_service import OilService, OilServiceItem
        db.create_all()
        Setting.init_defaults()

    return app