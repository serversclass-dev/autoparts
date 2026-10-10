import sys
import os
import sqlite3

HERE     = os.path.abspath(os.path.dirname(__file__))
INSTANCE = os.path.join(HERE, "instance")
DB_PATH  = os.path.join(INSTANCE, "autoparts.db")

# إنشاء المجلدات
os.makedirs(INSTANCE,                                     exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "uploads"),            exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "uploads", "avatars"), exist_ok=True)
os.makedirs(os.path.join(INSTANCE, "backups"),            exist_ok=True)

# إنشاء ملف DB فارغ مباشرة
conn = sqlite3.connect(DB_PATH)
conn.close()

# المسار يحتوي مسافات — نستخدم مسار قصير بـ os.chdir
# SQLAlchemy يقبل المسار النسبي بدون مسافات
os.chdir(INSTANCE)
_rel_uri = "sqlite:///autoparts.db"
os.environ["DATABASE_URL"] = _rel_uri
os.chdir(HERE)

print(f"✅ DB Path : {DB_PATH}")
print(f"✅ DB URI  : {_rel_uri}")
print(f"✅ DB Size : {os.path.getsize(DB_PATH)} bytes")

sys.path.insert(0, HERE)
from app import create_app

app = create_app("development")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)