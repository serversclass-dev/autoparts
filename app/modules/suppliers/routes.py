from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.modules.suppliers import suppliers_bp
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.extensions import db


# ── List ──────────────────────────────────────────────────────────────────────
@suppliers_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    debt_only = request.args.get("debt_only", "")
    page = request.args.get("page", 1, type=int)

    query = Supplier.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Supplier.name.ilike(f"%{search}%"),
                Supplier.phone.ilike(f"%{search}%"),
            )
        )

    suppliers = query.order_by(Supplier.name).paginate(page=page, per_page=20)

    if debt_only:
        filtered = [s for s in suppliers.items if s.balance > 0]
    else:
        filtered = suppliers.items

    total_debt = sum(
        s.balance for s in Supplier.query.filter_by(is_active=True).all()
        if s.balance > 0
    )

    return render_template(
        "suppliers/list.html",
        suppliers=suppliers,
        filtered=filtered,
        debt_only=debt_only,
        search=search,
        total_debt=total_debt,
    )


# ── Create ────────────────────────────────────────────────────────────────────
@suppliers_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("suppliers.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("اسم المورد مطلوب.", "danger")
            return render_template("suppliers/form.html", supplier=None)

        supplier = Supplier(
            name=name,
            phone=request.form.get("phone", "").strip() or None,
            email=request.form.get("email", "").strip() or None,
            address=request.form.get("address", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f"تم إضافة المورد '{name}' بنجاح.", "success")
        return redirect(url_for("suppliers.detail", supplier_id=supplier.id))

    return render_template("suppliers/form.html", supplier=None)


# ── Edit ──────────────────────────────────────────────────────────────────────
@suppliers_bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
@login_required
def edit(supplier_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("suppliers.index"))

    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("اسم المورد مطلوب.", "danger")
            return render_template("suppliers/form.html", supplier=supplier)

        supplier.name = name
        supplier.phone = request.form.get("phone", "").strip() or None
        supplier.email = request.form.get("email", "").strip() or None
        supplier.address = request.form.get("address", "").strip() or None
        supplier.notes = request.form.get("notes", "").strip() or None
        db.session.commit()
        flash(f"تم تعديل بيانات المورد '{name}' بنجاح.", "success")
        return redirect(url_for("suppliers.detail", supplier_id=supplier.id))

    return render_template("suppliers/form.html", supplier=supplier)


# ── Detail / Ledger ───────────────────────────────────────────────────────────
@suppliers_bp.route("/<int:supplier_id>")
@login_required
def detail(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    ledger = supplier.get_ledger()
    recent_purchases = supplier.purchases.order_by(
        db.text("purchase_date desc")
    ).limit(10).all()
    return render_template(
        "suppliers/detail.html",
        supplier=supplier,
        ledger=ledger,
        recent_purchases=recent_purchases,
    )


# ── Delete ────────────────────────────────────────────────────────────────────
@suppliers_bp.route("/<int:supplier_id>/delete", methods=["POST"])
@login_required
def delete(supplier_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("suppliers.index"))

    supplier = Supplier.query.get_or_404(supplier_id)

    if supplier.has_purchases:
        flash("لا يمكن حذف مورد له فواتير مسجلة.", "danger")
        return redirect(url_for("suppliers.index"))

    supplier.is_active = False
    db.session.commit()
    flash(f"تم حذف المورد '{supplier.name}'.", "success")
    return redirect(url_for("suppliers.index"))


# ── Add Payment ───────────────────────────────────────────────────────────────
@suppliers_bp.route("/<int:supplier_id>/pay", methods=["POST"])
@login_required
def add_payment(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    amount = float(request.form.get("amount", 0))
    payment_method = request.form.get("payment_method", "cash")
    notes = request.form.get("notes", "").strip() or None
    payment_date_str = request.form.get("payment_date", "")

    if amount <= 0:
        flash("المبلغ يجب أن يكون أكبر من صفر.", "danger")
        return redirect(url_for("suppliers.detail", supplier_id=supplier_id))

    try:
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d") if payment_date_str else datetime.utcnow()
    except ValueError:
        payment_date = datetime.utcnow()

    payment = SupplierPayment(
        supplier_id=supplier_id,
        user_id=current_user.id,
        amount=amount,
        payment_method=payment_method,
        notes=notes,
        payment_date=payment_date,
    )
    db.session.add(payment)
    db.session.commit()
    flash(f"تم تسجيل دفعة بمبلغ {amount:.2f} ر.س للمورد '{supplier.name}'.", "success")
    return redirect(url_for("suppliers.detail", supplier_id=supplier_id))


# ── Delete Payment ────────────────────────────────────────────────────────────
@suppliers_bp.route("/payment/<int:payment_id>/delete", methods=["POST"])
@login_required
def delete_payment(payment_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("suppliers.index"))

    payment = SupplierPayment.query.get_or_404(payment_id)
    supplier_id = payment.supplier_id
    db.session.delete(payment)
    db.session.commit()
    flash("تم حذف الدفعة بنجاح.", "success")
    return redirect(url_for("suppliers.detail", supplier_id=supplier_id))