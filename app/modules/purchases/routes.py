from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.modules.purchases import purchases_bp
from app.models.purchase import Purchase, PurchaseItem
from app.models.product import Product
from app.models.supplier import Supplier
from app.extensions import db


# ── List ──────────────────────────────────────────────────────────────────────
@purchases_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    status_filter = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

    query = Purchase.query

    if search:
        query = query.outerjoin(Supplier).filter(
            db.or_(
                Purchase.invoice_number.ilike(f"%{search}%"),
                Supplier.name.ilike(f"%{search}%"),
            )
        )
    if date_from:
        try:
            query = query.filter(Purchase.purchase_date >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Purchase.purchase_date <= dt)
        except ValueError:
            pass
    if status_filter:
        query = query.filter(Purchase.status == status_filter)

    purchases = query.order_by(Purchase.purchase_date.desc()).paginate(page=page, per_page=20)

    all_q = query.all()
    total_cost = sum(p.total for p in all_q if p.status == "received")

    return render_template(
        "purchases/list.html",
        purchases=purchases,
        search=search,
        date_from=date_from,
        date_to=date_to,
        status_filter=status_filter,
        total_cost=total_cost,
    )


# ── Create ────────────────────────────────────────────────────────────────────
@purchases_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == "POST":
        supplier_id = request.form.get("supplier_id") or None
        payment_method = request.form.get("payment_method", "cash")
        paid = float(request.form.get("paid", 0))
        notes = request.form.get("notes", "").strip() or None
        purchase_date_str = request.form.get("purchase_date", "")
        supplier_invoice = request.form.get("supplier_invoice", "").strip() or None

        try:
            purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d") if purchase_date_str else datetime.utcnow()
        except ValueError:
            purchase_date = datetime.utcnow()

        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")

        if not product_ids:
            flash("أضف منتجاً واحداً على الأقل.", "danger")
            return render_template("purchases/form.html", suppliers=suppliers, products=products)

        try:
            with db.session.begin_nested():
                subtotal = 0.0
                items_to_create = []

                for pid, qty_str, price_str in zip(product_ids, quantities, unit_prices):
                    product = Product.query.get(int(pid))
                    if not product:
                        raise ValueError(f"منتج غير موجود.")
                    qty = float(qty_str)
                    price = float(price_str)
                    if qty <= 0:
                        raise ValueError(f"الكمية يجب أن تكون أكبر من صفر: {product.name}")
                    if price < 0:
                        raise ValueError(f"السعر لا يمكن أن يكون سالباً: {product.name}")
                    line_total = round(qty * price, 2)
                    subtotal += line_total
                    items_to_create.append({
                        "product": product,
                        "qty": qty,
                        "price": price,
                        "total": line_total,
                    })

                total = round(subtotal, 2)
                status = "received"

                purchase = Purchase(
                    invoice_number=Purchase.generate_invoice_number(),
                    supplier_id=supplier_id,
                    user_id=current_user.id,
                    subtotal=subtotal,
                    discount=0,
                    total=total,
                    paid=paid if payment_method != "credit" else 0,
                    payment_method=payment_method,
                    status=status,
                    notes=f"{supplier_invoice+' — ' if supplier_invoice else ''}{notes or ''}",
                    purchase_date=purchase_date,
                )
                db.session.add(purchase)
                db.session.flush()

                for item in items_to_create:
                    db.session.add(PurchaseItem(
                        purchase_id=purchase.id,
                        product_id=item["product"].id,
                        quantity=item["qty"],
                        unit_price=item["price"],
                        total=item["total"],
                    ))
                    # Update stock and purchase price
                    item["product"].quantity += item["qty"]
                    item["product"].purchase_price = item["price"]

                # Update supplier balance if credit
                if payment_method == "credit" and supplier_id:
                    supplier = Supplier.query.get(supplier_id)
                    # balance is computed dynamically — no action needed

            db.session.commit()
            flash(f"تم حفظ فاتورة الشراء {purchase.invoice_number} وتحديث المخزون.", "success")
            return redirect(url_for("purchases.detail", purchase_id=purchase.id))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except Exception as e:
            db.session.rollback()
            flash("حدث خطأ أثناء الحفظ. حاول مجدداً.", "danger")

    return render_template("purchases/form.html", suppliers=suppliers, products=products)


# ── Detail ────────────────────────────────────────────────────────────────────
@purchases_bp.route("/<int:purchase_id>")
@login_required
def detail(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template("purchases/detail.html", purchase=purchase)


# ── Cancel ────────────────────────────────────────────────────────────────────
@purchases_bp.route("/<int:purchase_id>/cancel", methods=["POST"])
@login_required
def cancel(purchase_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية إلغاء فواتير الشراء.", "danger")
        return redirect(url_for("purchases.detail", purchase_id=purchase_id))

    purchase = Purchase.query.get_or_404(purchase_id)

    if purchase.status == "cancelled":
        flash("هذه الفاتورة ملغاة مسبقاً.", "warning")
        return redirect(url_for("purchases.detail", purchase_id=purchase_id))

    # Check if cancellation would make stock negative
    errors = []
    for item in purchase.items:
        if item.product.quantity < item.quantity:
            errors.append(
                f"لا يمكن الإلغاء: المخزون الحالي للمنتج '{item.product.name}' "
                f"({item.product.quantity}) أقل من كمية الفاتورة ({item.quantity})."
            )
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("purchases.detail", purchase_id=purchase_id))

    try:
        for item in purchase.items:
            item.product.quantity -= item.quantity
        purchase.status = "cancelled"
        db.session.commit()
        flash(f"تم إلغاء فاتورة الشراء {purchase.invoice_number} وخصم الكميات من المخزون.", "success")
    except Exception:
        db.session.rollback()
        flash("حدث خطأ أثناء الإلغاء.", "danger")

    return redirect(url_for("purchases.detail", purchase_id=purchase_id))


# ── Product search AJAX ───────────────────────────────────────────────────────
@purchases_bp.route("/product-search")
@login_required
def product_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f"%{q}%"),
            Product.barcode.ilike(f"%{q}%"),
        ),
        Product.is_active == True,
    ).limit(10).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "barcode": p.barcode or "",
            "purchase_price": p.purchase_price,
            "unit": p.unit,
            "quantity": p.quantity,
        }
        for p in products
    ])