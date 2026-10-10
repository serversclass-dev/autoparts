import sys
import os
import sqlite3

HERE     = os.path.abspath(os.path.dirname(__file__))
INSTANCE = os.path.join(HERE, "instance")
DB_PATH  = os.path.join(INSTANCE, "autoparts.db")

# إنشاء المجلدات والـ DB
os.makedirs(INSTANCE, exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "uploads"), exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "uploads", "avatars"), exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "backups"), exist_ok=True)
conn = sqlite3.connect(DB_PATH); conn.close()

# تعيين URI
os.chdir(INSTANCE)
os.environ["DATABASE_URL"] = "sqlite:///autoparts.db"
os.chdir(HERE)

sys.path.insert(0, HERE)

from app import create_app

app = create_app("development")

def seed():
    with app.app_context():
        from seeds.seeder import seed_all
        seed_all()

def create_admin():
    with app.app_context():
        from app.extensions import db
        from app.models.user import User
        if User.query.filter_by(username="admin").first():
            print("✅ المستخدم admin موجود مسبقاً")
            return
        u = User(username="admin", full_name="المدير العام",
                 role="admin", is_active=True, force_password_change=False)
        u.set_password("admin123")
        db.session.add(u)
        db.session.commit()
        print("✅ تم إنشاء المستخدم: admin / admin123")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "seed":
        seed()
    elif cmd == "create-admin":
        create_admin()
    elif cmd == "check-users":
        with app.app_context():
            from app.models.user import User
            users = User.query.all()
            if not users:
                print("❌ لا يوجد مستخدمون في قاعدة البيانات!")
                print("   شغّل: python cli.py seed")
            else:
                for u in users:
                    print(f"  ✅ {u.username} | {u.role} | نشط: {u.is_active}")
    else:
        print("الأوامر المتاحة:")
        print("  python cli.py seed          — إضافة البيانات الأولية")
        print("  python cli.py create-admin  — إنشاء مستخدم admin فوراً")
        print("  python cli.py check-users   — عرض المستخدمين الموجودين")