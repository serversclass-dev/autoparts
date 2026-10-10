import os
from datetime import timedelta

BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# إنشاء المجلدات فوراً
os.makedirs(INSTANCE_DIR,                                      exist_ok=True)
os.makedirs(os.path.join(INSTANCE_DIR, "uploads"),             exist_ok=True)
os.makedirs(os.path.join(INSTANCE_DIR, "uploads", "avatars"),  exist_ok=True)
os.makedirs(os.path.join(INSTANCE_DIR, "backups"),             exist_ok=True)

DB_PATH = os.path.join(INSTANCE_DIR, "autoparts.db")

# على Windows مع مسافات في المسار نستخدم URI مع 4 شرطات مائلة
# sqlite:////C:/path with spaces/file.db
if os.name == "nt":
    # Windows: نستخدم المسار المطلق مع forward slashes و4 شرطات
    _db_uri = "sqlite:///" + DB_PATH.replace("\\", "/")
else:
    _db_uri = f"sqlite:///{DB_PATH}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "autoparts-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _db_uri)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    LOW_STOCK_DEFAULT = 5
    APP_NAME    = "زيوت وكماليات السيارات"
    APP_NAME_EN = "AutoParts Manager"
    APP_VERSION = "1.0.0"


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}