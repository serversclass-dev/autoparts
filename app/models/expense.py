from datetime import datetime
from app.extensions import db


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="other")
    # categories: rent | salary | electricity | water | maintenance | other
    amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(20), nullable=False, default="cash")
    # payment_method: cash | transfer | credit
    notes = db.Column(db.Text, nullable=True)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Relationship
    user = db.relationship("User", backref="expenses")

    CATEGORIES = {
        "rent": "إيجار",
        "salary": "رواتب",
        "electricity": "كهرباء",
        "water": "ماء",
        "maintenance": "صيانة",
        "transport": "نقل وشحن",
        "tax": "ضرائب ورسوم",
        "other": "أخرى",
    }

    PAYMENT_METHODS = {
        "cash": "نقدي",
        "transfer": "تحويل بنكي",
        "credit": "آجل",
    }

    @property
    def category_label(self):
        return self.CATEGORIES.get(self.category, self.category)

    @property
    def payment_method_label(self):
        return self.PAYMENT_METHODS.get(self.payment_method, self.payment_method)

    def __repr__(self):
        return f"<Expense {self.title} {self.amount}>"