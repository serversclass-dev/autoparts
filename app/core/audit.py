from datetime import datetime
from flask_login import current_user
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", backref="audit_logs", foreign_keys=[user_id])

    # Action constants
    ACTIONS = {
        "login": "تسجيل دخول",
        "logout": "تسجيل خروج",
        "sale_create": "إنشاء فاتورة بيع",
        "sale_cancel": "إلغاء فاتورة بيع",
        "purchase_create": "إنشاء فاتورة شراء",
        "purchase_cancel": "إلغاء فاتورة شراء",
        "product_create": "إضافة منتج",
        "product_edit": "تعديل منتج",
        "product_delete": "حذف منتج",
        "product_price_change": "تغيير سعر منتج",
        "stock_adjust": "تعديل مخزون يدوي",
        "inventory_commit": "اعتماد جرد مخزون",
        "customer_payment": "تسجيل دفعة عميل",
        "supplier_payment": "تسجيل دفعة مورد",
        "expense_create": "إضافة مصروف",
        "expense_delete": "حذف مصروف",
        "user_create": "إنشاء مستخدم",
        "user_edit": "تعديل مستخدم",
        "user_role_change": "تغيير صلاحية مستخدم",
        "password_reset": "إعادة تعيين كلمة مرور",
        "settings_update": "تحديث الإعدادات",
        "backup_create": "إنشاء نسخة احتياطية",
        "backup_restore": "استعادة نسخة احتياطية",
    }

    @property
    def action_label(self):
        return self.ACTIONS.get(self.action, self.action)

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"


def log_action(action, entity=None, entity_id=None, description=None):
    """تسجيل عملية في سجل التدقيق."""
    try:
        from flask import request as flask_request
        try:
            ip = flask_request.remote_addr
        except Exception:
            ip = None

        user_id = None
        if current_user and current_user.is_authenticated:
            user_id = current_user.id

        log = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            description=description,
            ip_address=ip,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        # Never let audit logging crash the app
        db.session.rollback()