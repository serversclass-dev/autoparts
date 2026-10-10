from datetime import datetime
from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(100), unique=True, nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Pricing
    purchase_price = db.Column(db.Float, nullable=False, default=0.0)
    sale_price = db.Column(db.Float, nullable=False, default=0.0)

    # Stock
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    # opening_qty: الكمية الافتتاحية عند إنشاء المنتج — تدخل في معادلة المخزون
    opening_qty = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False, default="قطعة")
    low_stock_alert = db.Column(db.Integer, nullable=False, default=5)

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sale_items = db.relationship("SaleItem", backref="product", lazy="dynamic")
    purchase_items = db.relationship("PurchaseItem", backref="product", lazy="dynamic")

    @property
    def profit_margin(self):
        if self.purchase_price and self.purchase_price > 0:
            return round(self.sale_price - self.purchase_price, 2)
        return 0.0

    @property
    def profit_percent(self):
        if self.purchase_price and self.purchase_price > 0:
            return round((self.profit_margin / self.purchase_price) * 100, 1)
        return 0.0

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_alert

    @property
    def stock_value(self):
        return round(self.quantity * self.purchase_price, 2)

    def __repr__(self):
        return f"<Product {self.name}>"