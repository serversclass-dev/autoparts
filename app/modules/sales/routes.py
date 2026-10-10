from datetime import datetime, date
from flask import (
    render_template, redirect, url_for, flash,
    request, jsonify, abort
)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.modules.sales import sales_bp
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.customer import Customer
from app.extensions import db


# ── POS Screen ────────────────────────────────────────────────────────────────
@sales_bp.route("/pos")
@login_required
def pos():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template("sales/pos.html", customers=customers)


# ── Save Sale (AJAX) ──────────────────────────────────────────────────────────
@sales_bp.route("/save", methods=["POST"])
@login_required
def save():
    data = request.get_json()
    if not data or not data.get("items"):
        return jsonify({"ok": False, "msg": "لا توجد بنود في الفاتورة."}), 400

    items_data = data["items"]
    customer_id = data.get("customer_id") or None
    discount = float(data.get("discount", 0))
    discount_type = data.get("discount_type", "amount")
    payment_method = data.get("payment_method", "cash")
    paid = float(data.get("paid", 0))
    notes = data.get("notes", "")

    try:
        with db.session.begin_nested():
            # Validate & lock products
            sale_items_to_create = []
            subtotal = 0.0

            for item in items_data:
                product = Product.query.filter_by(
                    id=int(item["product_id"]), is_active=True
                ).with_for_update().first()

                if not product:
                    raise ValueError(f"المنتج غير موجود.")

                qty = float(item["qty"])
                if qty <= 0:
                    raise ValueError(f"الكمية يجب أن تكون أكبر من صفر: {product.name}")

                if product.quantity < qty:
                    raise ValueError(
                        f"الكمية المطلوبة ({qty} {product.unit}) "
                        f"أكبر من المتوفر ({product.quantity} {product.unit}) "
                        f"للمنتج: {product.name}"
                    )

                unit_price = float(item.get("unit_price", product.sale_price))
                line_total = round(unit_price * qty, 2)
                subtotal += line_total

                sale_items_to_create.append({
                    "product": product,
                    "qty": qty,
                    "unit_price": unit_price,
                    "purchase_price": product.purchase_price,
                    "total": line_total,
                })

            # Calc discount & total
            if discount_type == "percent":
                discount_amount = round(subtotal * discount / 100, 2)
            else:
                discount_amount = round(discount, 2)

            total = round(subtotal - discount_amount, 2)
            change = round(max(paid - total, 0), 2)

            # Determine status
            if payment_method == "credit":
                status = "on_credit"
            else:
                status = "completed"

            # Create Sale
            sale = Sale(
                invoice_number=Sale.generate_invoice_number(),
                customer_id=customer_id,
                user_id=current_user.id,
                subtotal=subtotal,
                discount=discount,
                discount_type=discount_type,
                total=total,
                paid=paid if payment_method != "credit" else 0,
                change=change,
                payment_method=payment_method,
                status=status,
                notes=notes,
            )
            db.session.add(sale)
            db.session.flush()  # get sale.id

            # Create SaleItems & deduct stock
            for si in sale_items_to_create:
                db.session.add(SaleItem(
                    sale_id=sale.id,
                    product_id=si["product"].id,
                    quantity=si["qty"],
                    unit_price=si["unit_price"],
                    purchase_price=si["purchase_price"],
                    total=si["total"],
                ))
                si["product"].quantity -= si["qty"]

            # Update customer balance if on_credit
            if status == "on_credit" and customer_id:
                customer = Customer.query.get(customer_id)
                if customer:
                    customer.balance += total

        db.session.commit()
        return jsonify({
            "ok": True,
            "msg": "تم حفظ الفاتورة بنجاح.",
            "invoice_number": sale.invoice_number,
            "sale_id": sale.id,
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({"ok": False, "msg": str(e)}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "msg": "حدث خطأ أثناء الحفظ. حاول مجدداً."}), 500


# ── Sales List ────────────────────────────────────────────────────────────────
@sales_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    status_filter = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

    query = Sale.query

    if search:
        query = query.outerjoin(Customer).filter(
            db.or_(
                Sale.invoice_number.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
            )
        )
    if date_from:
        try:
            query = query.filter(Sale.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            dt_to = dt_to.replace(hour=23, minute=59, second=59)
            query = query.filter(Sale.created_at <= dt_to)
        except ValueError:
            pass
    if status_filter:
        query = query.filter(Sale.status == status_filter)

    sales = query.order_by(Sale.created_at.desc()).paginate(page=page, per_page=20)

    # Summary for filtered results
    all_sales = query.all()
    total_revenue = sum(s.total for s in all_sales if s.status != "cancelled")
    total_profit = sum(s.profit for s in all_sales if s.status != "cancelled")

    return render_template(
        "sales/list.html",
        sales=sales,
        search=search,
        date_from=date_from,
        date_to=date_to,
        status_filter=status_filter,
        total_revenue=total_revenue,
        total_profit=total_profit,
    )


# ── Sale Detail ───────────────────────────────────────────────────────────────
@sales_bp.route("/<int:sale_id>")
@login_required
def detail(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sales/detail.html", sale=sale)


# ── Cancel Sale ───────────────────────────────────────────────────────────────
@sales_bp.route("/<int:sale_id>/cancel", methods=["POST"])
@login_required
def cancel(sale_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية إلغاء الفواتير.", "danger")
        return redirect(url_for("sales.detail", sale_id=sale_id))

    sale = Sale.query.get_or_404(sale_id)

    if sale.status == "cancelled":
        flash("هذه الفاتورة ملغاة مسبقاً.", "warning")
        return redirect(url_for("sales.detail", sale_id=sale_id))

    try:
        # Return stock
        for item in sale.items:
            item.product.quantity += item.quantity

        # Remove customer debt if on_credit
        if sale.status == "on_credit" and sale.customer_id:
            sale.customer.balance -= sale.total
            sale.customer.balance = max(sale.customer.balance, 0)

        sale.status = "cancelled"
        db.session.commit()
        flash(f"تم إلغاء الفاتورة {sale.invoice_number} وإرجاع المخزون.", "success")
    except Exception:
        db.session.rollback()
        flash("حدث خطأ أثناء الإلغاء.", "danger")

    return redirect(url_for("sales.detail", sale_id=sale_id))


# ── Print / PDF ───────────────────────────────────────────────────────────────
@sales_bp.route("/<int:sale_id>/print")
@login_required
def print_invoice(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sales/print.html", sale=sale)


@sales_bp.route("/<int:sale_id>/pdf")
@login_required
def pdf_invoice(sale_id):
    from app.utils.pdf import generate_sale_pdf
    sale = Sale.query.get_or_404(sale_id)
    pdf_bytes = generate_sale_pdf(sale)
    from flask import Response
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{sale.invoice_number}.pdf"
        },
    )