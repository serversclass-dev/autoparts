from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.setting import Setting

app = create_app()

with app.app_context():
    # اعدادات اساسية
    defaults = {
        "shop_name": "زيوت وكماليات السيارات",
        "currency": "د.ل",
        "invoice_footer": "شكراً لتعاملكم معنا",
        "vat_rate": "0",
        "low_stock_default": "5",
        "backup_keep_days": "30",
        "force_password_change": "1",
        "login_max_attempts": "5",
        "login_lockout_minutes": "15",
    }
    for key, value in defaults.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value))

    # اضافة الادمن لو ما موجود
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            full_name="المدير العام",
            role="admin",
            is_active=True,
            force_password_change=False,
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("تم انشاء الادمن بنجاح")
        print("اسم المستخدم: admin")
        print("كلمة المرور:  admin123")
    else:
        db.session.commit()
        print("الادمن موجود مسبقاً")