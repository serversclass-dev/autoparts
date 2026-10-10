from datetime import datetime
from app.extensions import db


class CustomerPayment(db.Model):
    __tablename__ = "customer_payments"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default="cash")
    notes = db.Column(db.Text, nullable=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    PAYMENT_METHODS = {
        "cash": "نقدي",
        "transfer": "تحويل بنكي",
        "check": "شيك",
    }

    # Relationships
    customer = db.relationship("Customer", backref="payments")
    user = db.relationship("User", backref="customer_payments")

    @property
    def payment_method_label(self):
        return self.PAYMENT_METHODS.get(self.payment_method, self.payment_method)

    def __repr__(self):
        return f"<CustomerPayment {self.customer_id} {self.amount}>"