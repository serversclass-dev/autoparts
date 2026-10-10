from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.modules.inventory import inventory_bp
from app.models.product import Product
from app.core.permissions import admin_required
from app.core.audit import log_action
from app.extensions import db


@inventory_bp.route("/")
@login_required
@admin_required
def index():
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", "")

    from app.models.category import Category
    categories = Category.query.order_by(Category.name).all()

    query = Product.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter_by(category_id=int(category_id))

    products = query.order_by(Product.name).all()

    return render_template(
        "inventory/index.html",
        products=products,
        categories=categories,
        search=search,
        category_id=category_id,
    )


@inventory_bp.route("/commit", methods=["POST"])
@login_required
@admin_required
def commit():
    """اعتماد الجرد وتحديث الكميات."""
    product_ids = request.form.getlist("product_id[]")
    actual_qtys = request.form.getlist("actual_qty[]")

    if not product_ids:
        flash("لا توجد بيانات للجرد.", "warning")
        return redirect(url_for("inventory.index"))

    adjustments = []
    errors = []

    for pid, qty_str in zip(product_ids, actual_qtys):
        try:
            product = Product.query.get(int(pid))
            if not product:
                continue

            actual = float(qty_str)
            if actual < 0:
                errors.append(f"الكمية لا يمكن أن تكون سالبة: {product.name}")
                continue

            diff = actual - product.quantity
            if diff != 0:
                adjustments.append({
                    "product": product,
                    "old_qty": product.quantity,
                    "new_qty": actual,
                    "diff": diff,
                })
        except (ValueError, TypeError):
            errors.append(f"قيمة غير صالحة للمنتج ID={pid}")

    if errors:
        for e in errors:
            flash(e, "warning")
        return redirect(url_for("inventory.index"))

    if not adjustments:
        flash("لا توجد تغييرات في الكميات.", "info")
        return redirect(url_for("inventory.index"))

    # Apply adjustments
    desc_parts = []
    for adj in adjustments:
        adj["product"].quantity = adj["new_qty"]
        sign = "+" if adj["diff"] > 0 else ""
        desc_parts.append(
            f"{adj['product'].name}: {adj['old_qty']} → {adj['new_qty']} ({sign}{adj['diff']:.2f})"
        )

    db.session.commit()

    log_action(
        "inventory_commit",
        description=f"جرد مخزون اعتمده {current_user.full_name}:\n" + "\n".join(desc_parts),
    )

    flash(f"تم اعتماد الجرد وتحديث {len(adjustments)} منتج.", "success")
    return redirect(url_for("inventory.index"))