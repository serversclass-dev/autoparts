from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.modules.customers import customers_bp
from app.models.customer import Customer
from app.models.customer_payment import CustomerPayment
from app.extensions import db


# ── List ──────────────────────────────────────────────────────────────────────
@customers_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    debt_only = request.args.get("debt_only", "")
    page = request.args.get("page", 1, type=int)

    query = Customer.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Customer.car_plate.ilike(f"%{search}%"),
            )
        )

    customers = query.order_by(Customer.name).paginate(page=page, per_page=20)

    # Filter debt_only after pagination (small dataset)
    if debt_only:
        debt_customers = [c for c in customers.items if c.balance > 0]
    else:
        debt_customers = customers.items

    total_debt = sum(c.balance for c in Customer.query.filter_by(is_active=True).all() if c.balance > 0)

    return render_template(
        "customers/list.html",
        customers=customers,
        debt_customers=debt_customers,
        debt_only=debt_only,
        search=search,
        total_debt=total_debt,
    )


# ── Create ────────────────────────────────────────────────────────────────────
@customers_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip() or None
        car_plate = request.form.get("car_plate", "").strip() or None
        car_model = request.form.get("car_model", "").strip() or None
        address = request.form.get("address", "").strip() or None
        notes = request.form.get("notes", "").strip() or None

        if not name:
            flash("اسم العميل مطلوب.", "danger")
            return render_template("customers/form.html", customer=None)

        customer = Customer(
            name=name, phone=phone, car_plate=car_plate,
            car_model=car_model, address=address, notes=notes,
        )
        db.session.add(customer)
        db.session.commit()
        flash(f"تم إضافة العميل '{name}' بنجاح.", "success")
        return redirect(url_for("customers.detail", customer_id=customer.id))

    return render_template("customers/form.html", customer=None)


# ── Edit ──────────────────────────────────────────────────────────────────────
@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("اسم العميل مطلوب.", "danger")
            return render_template("customers/form.html", customer=customer)

        customer.name = name
        customer.phone = request.form.get("phone", "").strip() or None
        customer.car_plate = request.form.get("car_plate", "").strip() or None
        customer.car_model = request.form.get("car_model", "").strip() or None
        customer.address = request.form.get("address", "").strip() or None
        customer.notes = request.form.get("notes", "").strip() or None
        db.session.commit()
        flash(f"تم تعديل بيانات العميل '{name}' بنجاح.", "success")
        return redirect(url_for("customers.detail", customer_id=customer.id))

    return render_template("customers/form.html", customer=customer)


# ── Detail / Ledger ───────────────────────────────────────────────────────────
@customers_bp.route("/<int:customer_id>")
@login_required
def detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    ledger = customer.get_ledger()
    recent_sales = customer.sales.order_by(db.text("created_at desc")).limit(10).all()
    return render_template(
        "customers/detail.html",
        customer=customer,
        ledger=ledger,
        recent_sales=recent_sales,
    )


# ── Delete ────────────────────────────────────────────────────────────────────
@customers_bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete(customer_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("customers.index"))

    customer = Customer.query.get_or_404(customer_id)

    if customer.has_sales:
        flash("لا يمكن حذف عميل له فواتير مسجلة.", "danger")
        return redirect(url_for("customers.index"))

    customer.is_active = False
    db.session.commit()
    flash(f"تم حذف العميل '{customer.name}'.", "success")
    return redirect(url_for("customers.index"))


# ── Add Payment ───────────────────────────────────────────────────────────────
@customers_bp.route("/<int:customer_id>/pay", methods=["POST"])
@login_required
def add_payment(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    amount = float(request.form.get("amount", 0))
    payment_method = request.form.get("payment_method", "cash")
    notes = request.form.get("notes", "").strip() or None
    payment_date_str = request.form.get("payment_date", "")

    if amount <= 0:
        flash("المبلغ يجب أن يكون أكبر من صفر.", "danger")
        return redirect(url_for("customers.detail", customer_id=customer_id))

    try:
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d") if payment_date_str else datetime.utcnow()
    except ValueError:
        payment_date = datetime.utcnow()

    payment = CustomerPayment(
        customer_id=customer_id,
        user_id=current_user.id,
        amount=amount,
        payment_method=payment_method,
        notes=notes,
        payment_date=payment_date,
    )
    db.session.add(payment)
    db.session.commit()
    flash(f"تم تسجيل دفعة بمبلغ {amount:.2f} ر.س من العميل '{customer.name}'.", "success")
    return redirect(url_for("customers.detail", customer_id=customer_id))


# ── Delete Payment ────────────────────────────────────────────────────────────
@customers_bp.route("/payment/<int:payment_id>/delete", methods=["POST"])
@login_required
def delete_payment(payment_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("customers.index"))

    payment = CustomerPayment.query.get_or_404(payment_id)
    customer_id = payment.customer_id
    db.session.delete(payment)
    db.session.commit()
    flash("تم حذف الدفعة بنجاح.", "success")
    return redirect(url_for("customers.detail", customer_id=customer_id))


# ── AJAX search ───────────────────────────────────────────────────────────────
@customers_bp.route("/search-ajax")
@login_required
def search_ajax():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    customers = Customer.query.filter(
        db.or_(
            Customer.name.ilike(f"%{q}%"),
            Customer.phone.ilike(f"%{q}%"),
            Customer.car_plate.ilike(f"%{q}%"),
        ),
        Customer.is_active == True,
    ).limit(10).all()
    return jsonify([
        {"id": c.id, "name": c.name,
         "phone": c.phone or "", "car_plate": c.car_plate or ""}
        for c in customers
    ])