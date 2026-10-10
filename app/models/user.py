from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cashier")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)

    # Login security
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    sales = db.relationship("Sale", backref="cashier", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    @property
    def role_label(self):
        labels = {"admin": "مدير", "cashier": "كاشير"}
        return labels.get(self.role, self.role)

    def record_failed_login(self, max_attempts=5, lockout_minutes=15):
        from datetime import timedelta
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            self.failed_attempts = 0

    def record_success_login(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()

    def __repr__(self):
        return f"<User {self.username}>"