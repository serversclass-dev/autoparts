from datetime import datetime
from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(128), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    purchases = db.relationship("Purchase", backref="supplier", lazy="dynamic")
    # payments backref added by SupplierPayment model

    @property
    def total_invoiced(self):
        """إجمالي فواتير الشراء الآجلة غير الملغاة."""
        return sum(
            p.total for p in self.purchases
            if p.payment_method == "credit" and p.status == "received"
        )

    @property
    def total_paid(self):
        """إجمالي الدفعات المسددة للمورد."""
        return sum(p.amount for p in self.payments)

    @property
    def balance(self):
        """المستحق للمورد = فواتير الآجل - المدفوع. محسوب دائماً من الحركات."""
        return round(self.total_invoiced - self.total_paid, 2)

    @property
    def has_debt(self):
        return self.balance > 0

    @property
    def balance_label(self):
        b = self.balance
        if b > 0:
            return f"مستحق له {b:.2f} ر.س"
        elif b < 0:
            return f"دائن {abs(b):.2f} ر.س"
        return "لا يوجد رصيد"

    @property
    def has_purchases(self):
        return self.purchases.count() > 0

    def get_ledger(self):
        """كشف حساب مرتب بالتاريخ مع الرصيد التراكمي."""
        entries = []

        # Credit purchases
        for p in self.purchases.filter_by(status="received").all():
            if p.payment_method == "credit":
                entries.append({
                    "date": p.purchase_date,
                    "type": "invoice",
                    "ref": p.invoice_number,
                    "description": "فاتورة شراء آجل",
                    "debit": p.total,
                    "credit": 0,
                    "obj": p,
                })

        # Payments to supplier
        for p in self.payments:
            entries.append({
                "date": p.payment_date,
                "type": "payment",
                "ref": f"دفعة #{p.id}",
                "description": f"دفعة للمورد — {p.payment_method_label}",
                "debit": 0,
                "credit": p.amount,
                "obj": p,
            })

        entries.sort(key=lambda x: x["date"])

        running = 0.0
        for e in entries:
            running += e["debit"] - e["credit"]
            e["running_balance"] = round(running, 2)

        return entries

    def __repr__(self):
        return f"<Supplier {self.name}>"