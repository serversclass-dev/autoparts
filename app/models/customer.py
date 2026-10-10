from datetime import datetime
from app.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    car_plate = db.Column(db.String(20), nullable=True)
    car_model = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales = db.relationship("Sale", backref="customer", lazy="dynamic")
    # payments backref added by CustomerPayment model

    @property
    def total_invoiced(self):
        """إجمالي فواتير الآجل غير الملغاة."""
        from app.models.sale import Sale
        return sum(
            s.total for s in self.sales
            if s.status == "on_credit"
        )

    @property
    def total_paid(self):
        """إجمالي الدفعات المسددة."""
        return sum(p.amount for p in self.payments)

    @property
    def balance(self):
        """الرصيد المستحق = فواتير الآجل - المدفوع. محسوب دائماً من الحركات."""
        return round(self.total_invoiced - self.total_paid, 2)

    @property
    def has_debt(self):
        return self.balance > 0

    @property
    def balance_label(self):
        b = self.balance
        if b > 0:
            return f"مدين {b:.2f} ر.س"
        elif b < 0:
            return f"دائن {abs(b):.2f} ر.س"
        return "لا يوجد رصيد"

    @property
    def has_sales(self):
        return self.sales.count() > 0

    def get_ledger(self):
        """كشف حساب مرتب بالتاريخ مع الرصيد التراكمي."""
        from app.models.sale import Sale
        from app.models.customer_payment import CustomerPayment

        entries = []
        # Credit sales
        for s in self.sales.filter(Sale.status == "on_credit").all():
            entries.append({
                "date": s.created_at,
                "type": "invoice",
                "ref": s.invoice_number,
                "description": f"فاتورة بيع آجل",
                "debit": s.total,
                "credit": 0,
                "obj": s,
            })
        # Payments
        for p in self.payments:
            entries.append({
                "date": p.payment_date,
                "type": "payment",
                "ref": f"دفعة #{p.id}",
                "description": f"دفعة نقدية — {p.payment_method_label}",
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
        return f"<Customer {self.name}>"