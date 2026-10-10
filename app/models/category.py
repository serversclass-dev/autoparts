from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship("Product", backref="category", lazy="dynamic")

    @property
    def product_count(self):
        return self.products.count()

    def __repr__(self):
        return f"<Category {self.name}>"