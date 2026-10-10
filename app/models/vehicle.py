from datetime import datetime
from app.extensions import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    plate = db.Column(db.String(30), nullable=False, index=True)
    car_type = db.Column(db.String(100), nullable=True)   # نوع السيارة
    car_model = db.Column(db.String(100), nullable=True)  # موديل السيارة
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship("Customer", backref="vehicles")
    oil_services = db.relationship("OilService", backref="vehicle", lazy="dynamic")

    @property
    def last_service(self):
        return self.oil_services.filter_by(status="completed")\
            .order_by(OilService.service_date.desc()).first()

    @property
    def last_odometer(self):
        svc = self.last_service
        return svc.odometer if svc else None

    @property
    def display_name(self):
        parts = [self.plate]
        if self.car_type:
            parts.append(self.car_type)
        if self.car_model:
            parts.append(self.car_model)
        return " — ".join(parts)

    def __repr__(self):
        return f"<Vehicle {self.plate}>"


# Import here to avoid circular import
from app.models.oil_service import OilService  # noqa: E402