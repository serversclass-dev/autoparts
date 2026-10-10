from datetime import datetime, timedelta
from app.extensions import db


class OilService(db.Model):
    __tablename__ = "oil_services"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Service details
    service_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    odometer = db.Column(db.Float, nullable=False)          # عداد وقت التغيير (كم)
    labor_cost = db.Column(db.Float, default=0.0)           # أجرة العمالة
    discount = db.Column(db.Float, default=0.0)             # خصم
    discount_type = db.Column(db.String(10), default="amount")  # amount | percent
    payment_method = db.Column(db.String(20), default="cash")   # cash | credit | transfer
    notes = db.Column(db.Text, nullable=True)

    # Next service
    next_km_interval = db.Column(db.Float, default=5000.0)  # مسافة التغيير القادم (كم)
    next_odometer = db.Column(db.Float, nullable=True)       # عداد التغيير القادم
    next_months = db.Column(db.Integer, nullable=True)       # مدة التغيير القادم (شهور)
    next_date = db.Column(db.DateTime, nullable=True)        # تاريخ التغيير القادم

    # Status
    status = db.Column(db.String(20), default="completed")  # completed | cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship("Customer", backref="oil_services")
    technician = db.relationship("User", backref="oil_services")
    sale = db.relationship("Sale", backref="oil_service", uselist=False)
    items = db.relationship(
        "OilServiceItem", backref="service", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    PAYMENT_METHODS = {
        "cash": "نقدي",
        "credit": "آجل",
        "transfer": "تحويل بنكي",
    }

    @property
    def payment_method_label(self):
        return self.PAYMENT_METHODS.get(self.payment_method, self.payment_method)

    @property
    def parts_total(self):
        return sum(i.total for i in self.items)

    @property
    def subtotal(self):
        return self.parts_total + self.labor_cost

    @property
    def discount_amount(self):
        if self.discount_type == "percent":
            return round(self.subtotal * self.discount / 100, 2)
        return round(self.discount, 2)

    @property
    def total(self):
        return max(self.subtotal - self.discount_amount, 0)

    @property
    def is_overdue(self):
        """هل فات موعد التغيير؟"""
        if self.next_date and self.next_date < datetime.utcnow():
            return True
        return False

    @property
    def days_until_next(self):
        if self.next_date:
            delta = self.next_date - datetime.utcnow()
            return delta.days
        return None

    @property
    def oil_type(self):
        """أول منتج زيت في العملية"""
        first = self.items.first()
        return first.product.name if first else "—"

    def compute_next(self):
        """حساب موعد التغيير القادم"""
        self.next_odometer = self.odometer + (self.next_km_interval or 5000)
        if self.next_months:
            self.next_date = self.service_date + timedelta(days=self.next_months * 30)

    def __repr__(self):
        return f"<OilService {self.id} vehicle={self.vehicle_id}>"


class OilServiceItem(db.Model):
    __tablename__ = "oil_service_items"

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("oil_services.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    purchase_price = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)

    product = db.relationship("Product", backref="oil_service_items")

    @property
    def profit(self):
        return round((self.unit_price - self.purchase_price) * self.quantity, 2)

    def __repr__(self):
        return f"<OilServiceItem service={self.service_id} product={self.product_id}>"