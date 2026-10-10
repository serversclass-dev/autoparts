from datetime import datetime
from app.extensions import db


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Totals
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    paid = db.Column(db.Float, nullable=False, default=0.0)

    # Payment
    payment_method = db.Column(db.String(20), nullable=False, default="cash")
    # payment_method: cash | credit | transfer

    # Status
    status = db.Column(db.String(20), nullable=False, default="received")
    # status: received | pending | cancelled

    notes = db.Column(db.Text, nullable=True)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship(
        "PurchaseItem", backref="purchase", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def remaining(self):
        return round(self.total - self.paid, 2)

    @property
    def is_paid(self):
        return self.paid >= self.total

    @staticmethod
    def generate_invoice_number():
        prefix = datetime.utcnow().strftime("%Y%m%d")
        last = (
            Purchase.query.filter(Purchase.invoice_number.like(f"PUR-{prefix}-%"))
            .order_by(Purchase.id.desc())
            .first()
        )
        if last:
            try:
                seq = int(last.invoice_number.split("-")[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"PUR-{prefix}-{seq:04d}"

    def __repr__(self):
        return f"<Purchase {self.invoice_number}>"


class PurchaseItem(db.Model):
    __tablename__ = "purchase_items"

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<PurchaseItem purchase={self.purchase_id} product={self.product_id}>"