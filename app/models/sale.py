from datetime import datetime
from app.extensions import db


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Totals
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    discount_type = db.Column(db.String(10), nullable=False, default="amount")
    # discount_type: 'amount' | 'percent'
    total = db.Column(db.Float, nullable=False, default=0.0)
    paid = db.Column(db.Float, nullable=False, default=0.0)
    change = db.Column(db.Float, nullable=False, default=0.0)

    # Payment
    payment_method = db.Column(db.String(20), nullable=False, default="cash")
    # payment_method: cash | credit | transfer

    # Status
    status = db.Column(db.String(20), nullable=False, default="completed")
    # status: completed | cancelled | on_credit

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship(
        "SaleItem", backref="sale", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def discount_amount(self):
        if self.discount_type == "percent":
            return round(self.subtotal * self.discount / 100, 2)
        return self.discount

    @property
    def profit(self):
        return sum(item.profit for item in self.items)

    @staticmethod
    def generate_invoice_number():
        from datetime import datetime
        prefix = datetime.utcnow().strftime("%Y%m%d")
        last = (
            Sale.query.filter(Sale.invoice_number.like(f"INV-{prefix}-%"))
            .order_by(Sale.id.desc())
            .first()
        )
        if last:
            try:
                seq = int(last.invoice_number.split("-")[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"INV-{prefix}-{seq:04d}"

    def __repr__(self):
        return f"<Sale {self.invoice_number}>"


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    purchase_price = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)

    @property
    def profit(self):
        return round((self.unit_price - self.purchase_price) * self.quantity, 2)

    def __repr__(self):
        return f"<SaleItem sale={self.sale_id} product={self.product_id}>"