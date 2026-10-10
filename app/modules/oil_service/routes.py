from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.modules.oil_service import oil_service_bp
from app.models.oil_service import OilService, OilServiceItem
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.core.permissions import admin_required
from app.core.audit import log_action
from app.extensions import db


# ── List ──────────────────────────────────────────────────────────────────────
@oil_service_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = request.args.get("page", 1, type=int)

    query = OilService.query

    if search:
        query = query.join(Vehicle).join(Customer).filter(
            db.or_(
                Vehicle.plate.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    if date_from:
        try:
            query = query.filter(OilService.service_date >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(OilService.service_date <= dt)
        except ValueError:
            pass

    services = query.order_by(OilService.service_date.desc()).paginate(page=page, per_page=20)

    # Summary
    total_revenue = sum(s.total for s in query.all() if s.status == "completed")
    total_count = query.filter_by(status="completed").count()

    return render_template(
        "oil_service/list.html",
        services=services,
        search=search,
        date_from=date_from,
        date_to=date_to,
        total_revenue=total_revenue,
        total_count=total_count,
    )


# ── Create ────────────────────────────────────────────────────────────────────
@oil_service_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == "POST":
        customer_id = request.form.get("customer_id") or None
        new_customer_name = request.form.get("new_customer_name", "").strip()
        new_customer_phone = request.form.get("new_customer_phone", "").strip()

        # Quick-add customer
        if not customer_id and new_customer_name:
            new_cust = Customer(name=new_customer_name, phone=new_customer_phone or None)
            db.session.add(new_cust)
            db.session.flush()
            customer_id = new_cust.id

        if not customer_id:
            flash("اختر عميلاً أو أضف عميلاً جديداً.", "danger")
            return render_template("oil_service/form.html", customers=customers, products=products)

        # Vehicle
        vehicle_id = request.form.get("vehicle_id") or None
        plate = request.form.get("plate", "").strip()
        car_type = request.form.get("car_type", "").strip()
        car_model = request.form.get("car_model", "").strip()

        if not vehicle_id:
            # Create new vehicle (plate optional)
            vehicle = Vehicle(
                customer_id=customer_id,
                plate=plate or "—",
                car_type=car_type or None,
                car_model=car_model or None,
            )
            db.session.add(vehicle)
            db.session.flush()
            vehicle_id = vehicle.id
        else:
            # Update vehicle info if changed
            vehicle = Vehicle.query.get(int(vehicle_id))
            if vehicle and car_type:
                vehicle.car_type = car_type
            if vehicle and car_model:
                vehicle.car_model = car_model

        # Service data
        odometer = float(request.form.get("odometer", 0))
        labor_cost = float(request.form.get("labor_cost", 0))
        discount = float(request.form.get("discount", 0))
        discount_type = request.form.get("discount_type", "amount")
        payment_method = request.form.get("payment_method", "cash")
        notes = request.form.get("notes", "").strip() or None
        next_km_interval = float(request.form.get("next_km_interval", 5000))
        next_months = request.form.get("next_months", "").strip()
        next_months = int(next_months) if next_months else None
        service_date_str = request.form.get("service_date", "")
        try:
            service_date = datetime.strptime(service_date_str, "%Y-%m-%d") if service_date_str else datetime.utcnow()
        except ValueError:
            service_date = datetime.utcnow()

        # Validate odometer
        vehicle = Vehicle.query.get(int(vehicle_id))
        if vehicle and vehicle.last_odometer and odometer < vehicle.last_odometer:
            flash(
                f"⚠️ تنبيه: قراءة العداد ({odometer} كم) أقل من آخر قراءة مسجّلة "
                f"({vehicle.last_odometer} كم). تحقق من الرقم.",
                "warning"
            )

        # Items
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")

        if not product_ids and labor_cost <= 0:
            flash("أضف منتجاً واحداً على الأقل أو أجرة عمالة.", "danger")
            db.session.rollback()
            return render_template("oil_service/form.html", customers=customers, products=products)

        try:
            with db.session.begin_nested():
                service = OilService(
                    vehicle_id=int(vehicle_id),
                    customer_id=int(customer_id),
                    user_id=current_user.id,
                    service_date=service_date,
                    odometer=odometer,
                    labor_cost=labor_cost,
                    discount=discount,
                    discount_type=discount_type,
                    payment_method=payment_method,
                    notes=notes,
                    next_km_interval=next_km_interval,
                    next_months=next_months,
                    status="completed",
                )
                service.compute_next()
                db.session.add(service)
                db.session.flush()

                # Process items & deduct stock
                items_data = []
                subtotal = labor_cost
                for pid, qty_str, price_str in zip(product_ids, quantities, unit_prices):
                    product = Product.query.get(int(pid))
                    if not product:
                        continue
                    qty = float(qty_str)
                    price = float(price_str)
                    if qty <= 0:
                        continue
                    if product.quantity < qty:
                        raise ValueError(
                            f"الكمية المطلوبة ({qty}) أكبر من المتوفر ({product.quantity}) للمنتج: {product.name}"
                        )
                    line_total = round(qty * price, 2)
                    subtotal += line_total
                    db.session.add(OilServiceItem(
                        service_id=service.id,
                        product_id=product.id,
                        quantity=qty,
                        unit_price=price,
                        purchase_price=product.purchase_price,
                        total=line_total,
                    ))
                    product.quantity -= qty
                    items_data.append({"product": product, "qty": qty, "price": price, "total": line_total})

                # Create Sale
                disc_amount = round(subtotal * discount / 100, 2) if discount_type == "percent" else discount
                total = max(subtotal - disc_amount, 0)
                status = "on_credit" if payment_method == "credit" else "completed"

                sale = Sale(
                    invoice_number=Sale.generate_invoice_number(),
                    customer_id=int(customer_id),
                    user_id=current_user.id,
                    subtotal=subtotal,
                    discount=discount,
                    discount_type=discount_type,
                    total=total,
                    paid=total if payment_method != "credit" else 0,
                    change=0,
                    payment_method=payment_method,
                    status=status,
                    notes=f"خدمة تغيير زيت — لوحة: {vehicle.plate}",
                )
                db.session.add(sale)
                db.session.flush()

                # Sale items
                for it in items_data:
                    db.session.add(SaleItem(
                        sale_id=sale.id,
                        product_id=it["product"].id,
                        quantity=it["qty"],
                        unit_price=it["price"],
                        purchase_price=it["product"].purchase_price,
                        total=it["total"],
                    ))
                # Labor as sale item if > 0
                if labor_cost > 0:
                    # Add labor as a special note in sale; no product deduction
                    pass

                # Link service to sale
                service.sale_id = sale.id

                # Update customer balance if credit
                if status == "on_credit":
                    customer = Customer.query.get(int(customer_id))
                    if customer:
                        customer.balance += total

            db.session.commit()
            log_action(
                "sale_create",
                entity="OilService",
                entity_id=service.id,
                description=f"تغيير زيت — {vehicle.plate} — {sale.invoice_number}",
            )
            flash(f"تم تسجيل عملية تغيير الزيت وإنشاء الفاتورة {sale.invoice_number}.", "success")
            return redirect(url_for("oil_service.detail", service_id=service.id))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except Exception as e:
            db.session.rollback()
            flash("حدث خطأ أثناء الحفظ. حاول مجدداً.", "danger")

    return render_template("oil_service/form.html", customers=customers, products=products)


# ── Detail ────────────────────────────────────────────────────────────────────
@oil_service_bp.route("/<int:service_id>")
@login_required
def detail(service_id):
    service = OilService.query.get_or_404(service_id)
    return render_template("oil_service/detail.html", service=service)


# ── Cancel ────────────────────────────────────────────────────────────────────
@oil_service_bp.route("/<int:service_id>/cancel", methods=["POST"])
@login_required
@admin_required
def cancel(service_id):
    service = OilService.query.get_or_404(service_id)

    if service.status == "cancelled":
        flash("هذه العملية ملغاة مسبقاً.", "warning")
        return redirect(url_for("oil_service.detail", service_id=service_id))

    try:
        # Return stock
        for item in service.items:
            item.product.quantity += item.quantity

        # Cancel linked sale
        if service.sale:
            service.sale.status = "cancelled"
            if service.sale.status == "on_credit" and service.customer_id:
                service.customer.balance -= service.total
                service.customer.balance = max(service.customer.balance, 0)

        service.status = "cancelled"
        db.session.commit()
        log_action(
            "sale_cancel",
            entity="OilService",
            entity_id=service.id,
            description=f"إلغاء تغيير زيت — {service.vehicle.plate}",
        )
        flash("تم إلغاء العملية وإرجاع المخزون.", "success")
    except Exception:
        db.session.rollback()
        flash("حدث خطأ أثناء الإلغاء.", "danger")

    return redirect(url_for("oil_service.detail", service_id=service_id))


# ── Reminders ─────────────────────────────────────────────────────────────────
@oil_service_bp.route("/reminders")
@login_required
def reminders():
    now = datetime.utcnow()
    soon = now + timedelta(days=14)

    # Overdue or due within 14 days
    due = OilService.query.filter(
        OilService.status == "completed",
        OilService.next_date.isnot(None),
        OilService.next_date <= soon,
    ).order_by(OilService.next_date).all()

    # Deduplicate: keep only latest per vehicle
    seen = {}
    for svc in due:
        vid = svc.vehicle_id
        if vid not in seen:
            seen[vid] = svc

    reminders_list = sorted(seen.values(), key=lambda s: s.next_date)
    overdue = [r for r in reminders_list if r.next_date < now]
    upcoming = [r for r in reminders_list if r.next_date >= now]

    return render_template(
        "oil_service/reminders.html",
        overdue=overdue,
        upcoming=upcoming,
    )


# ── Vehicle History ───────────────────────────────────────────────────────────
@oil_service_bp.route("/vehicle/<int:vehicle_id>")
@login_required
def vehicle_history(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    services = vehicle.oil_services.order_by(OilService.service_date.desc()).all()
    return render_template("oil_service/vehicle.html", vehicle=vehicle, services=services)


# ── AJAX: customer vehicles ───────────────────────────────────────────────────
@oil_service_bp.route("/ajax/vehicles")
@login_required
def ajax_vehicles():
    customer_id = request.args.get("customer_id", type=int)
    if not customer_id:
        return jsonify([])
    vehicles = Vehicle.query.filter_by(customer_id=customer_id, is_active=True).all()
    return jsonify([
        {
            "id": v.id,
            "plate": v.plate,
            "car_type": v.car_type or "",
            "car_model": v.car_model or "",
            "last_odometer": v.last_odometer,
            "display": v.display_name,
        }
        for v in vehicles
    ])


# ── Reports ───────────────────────────────────────────────────────────────────
@oil_service_bp.route("/reports")
@login_required
@admin_required
def reports():
    today = datetime.utcnow().date()
    first_of_month = today.replace(day=1)

    # Monthly count
    month_services = OilService.query.filter(
        OilService.service_date >= first_of_month,
        OilService.status == "completed",
    ).all()

    month_count = len(month_services)
    month_revenue = sum(s.total for s in month_services)
    month_labor = sum(s.labor_cost for s in month_services)
    month_parts = sum(s.parts_total for s in month_services)

    # By technician
    tech_data = db.session.query(
        OilService.user_id,
        func.count(OilService.id).label("count"),
        func.sum(OilService.labor_cost).label("labor"),
    ).filter(
        OilService.status == "completed",
        OilService.service_date >= first_of_month,
    ).group_by(OilService.user_id).all()

    from app.models.user import User
    tech_rows = []
    for row in tech_data:
        u = User.query.get(row.user_id)
        tech_rows.append({
            "name": u.full_name if u else "—",
            "count": row.count,
            "labor": row.labor or 0,
        })

    # Top oil types
    top_oils = db.session.query(
        Product.name,
        func.sum(OilServiceItem.quantity).label("total_qty"),
    ).join(OilServiceItem, OilServiceItem.product_id == Product.id)\
     .join(OilService, OilService.id == OilServiceItem.service_id)\
     .filter(
        OilService.status == "completed",
        OilService.service_date >= first_of_month,
     ).group_by(Product.id)\
      .order_by(func.sum(OilServiceItem.quantity).desc())\
      .limit(10).all()

    return render_template(
        "oil_service/reports.html",
        month_count=month_count,
        month_revenue=month_revenue,
        month_labor=month_labor,
        month_parts=month_parts,
        tech_rows=tech_rows,
        top_oils=top_oils,
        first_of_month=first_of_month,
    )


# ── Reminder count (for dashboard) ───────────────────────────────────────────
def get_reminder_count():
    now = datetime.utcnow()
    soon = now + timedelta(days=14)
    return OilService.query.filter(
        OilService.status == "completed",
        OilService.next_date.isnot(None),
        OilService.next_date <= soon,
    ).count()