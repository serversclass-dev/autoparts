from app.extensions import db


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    # Default settings
    DEFAULTS = {
        "shop_name": "زيوت وكماليات السيارات",
        "shop_name_en": "AutoParts Store",
        "shop_address": "",
        "shop_phone": "",
        "shop_email": "",
        "currency": "د.ل",
        "invoice_footer": "شكراً لتعاملكم معنا",
        "shop_logo": "",
        "vat_number": "",
        "vat_rate": "0",
        "low_stock_default": "5",
        "backup_keep_days": "30",
        "force_password_change": "1",
        "login_max_attempts": "5",
        "login_lockout_minutes": "15",
    }

    @classmethod
    def get(cls, key, default=None):
        """الحصول على قيمة إعداد بالمفتاح."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            return setting.value
        return cls.DEFAULTS.get(key, default)

    @classmethod
    def set(cls, key, value):
        """تعيين قيمة إعداد."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

    @classmethod
    def get_all(cls):
        """جميع الإعدادات كقاموس."""
        settings = {s.key: s.value for s in cls.query.all()}
        result = dict(cls.DEFAULTS)
        result.update(settings)
        return result

    @classmethod
    def init_defaults(cls):
        """تهيئة الإعدادات الافتراضية إن لم تكن موجودة."""
        for key, value in cls.DEFAULTS.items():
            if not cls.query.filter_by(key=key).first():
                db.session.add(cls(key=key, value=value))
        db.session.commit()

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"