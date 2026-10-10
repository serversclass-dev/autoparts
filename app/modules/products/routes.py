from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.modules.products import products_bp
from app.models.product import Product
from app.models.category import Category
from app.extensions import db


@products_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", "").strip()
    stock_filter = request.args.get("stock", "").strip()
    page = request.args.get("page", 1, type=int)

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
    if stock_filter == "low":
        query = query.filter(Product.quantity <= Product.low_stock_alert)
    elif stock_filter == "out":
        query = query.filter(Product.quantity <= 0)

    products = query.order_by(Product.name).paginate(page=page, per_page=20)
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "products/list.html",
        products=products,
        categories=categories,
        search=search,
        category_id=category_id,
        stock_filter=stock_filter,
    )


@products_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("products.index"))

    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        barcode = request.form.get("barcode", "").strip() or None
        category_id = request.form.get("category_id") or None
        description = request.form.get("description", "").strip()
        purchase_price = float(request.form.get("purchase_price", 0))
        sale_price = float(request.form.get("sale_price", 0))
        quantity = float(request.form.get("quantity", 0))
        unit = request.form.get("unit", "قطعة").strip()
        low_stock_alert = int(request.form.get("low_stock_alert", 5))

        if not name:
            flash("اسم المنتج مطلوب.", "danger")
            return render_template("products/form.html", categories=categories)

        if barcode and Product.query.filter_by(barcode=barcode).first():
            flash("الباركود مستخدم مسبقاً.", "danger")
            return render_template("products/form.html", categories=categories)

        product = Product(
            name=name,
            barcode=barcode,
            category_id=category_id,
            description=description,
            purchase_price=purchase_price,
            sale_price=sale_price,
            quantity=quantity,
            unit=unit,
            low_stock_alert=low_stock_alert,
        )
        db.session.add(product)
        db.session.commit()
        flash(f"تم إضافة المنتج '{name}' بنجاح.", "success")
        return redirect(url_for("products.index"))

    return render_template("products/form.html", categories=categories, product=None)


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit(product_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("products.index"))

    product = Product.query.get_or_404(product_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        barcode = request.form.get("barcode", "").strip() or None
        category_id = request.form.get("category_id") or None
        description = request.form.get("description", "").strip()
        purchase_price = float(request.form.get("purchase_price", 0))
        sale_price = float(request.form.get("sale_price", 0))
        quantity = float(request.form.get("quantity", 0))
        unit = request.form.get("unit", "قطعة").strip()
        low_stock_alert = int(request.form.get("low_stock_alert", 5))

        if not name:
            flash("اسم المنتج مطلوب.", "danger")
            return render_template("products/form.html", categories=categories, product=product)

        existing = Product.query.filter_by(barcode=barcode).first()
        if barcode and existing and existing.id != product_id:
            flash("الباركود مستخدم مسبقاً.", "danger")
            return render_template("products/form.html", categories=categories, product=product)

        product.name = name
        product.barcode = barcode
        product.category_id = category_id
        product.description = description
        product.purchase_price = purchase_price
        product.sale_price = sale_price
        product.quantity = quantity
        product.unit = unit
        product.low_stock_alert = low_stock_alert
        db.session.commit()
        flash(f"تم تعديل المنتج '{name}' بنجاح.", "success")
        return redirect(url_for("products.index"))

    return render_template("products/form.html", categories=categories, product=product)


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
def delete(product_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("products.index"))

    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash(f"تم حذف المنتج '{product.name}'.", "success")
    return redirect(url_for("products.index"))


@products_bp.route("/search-ajax")
@login_required
def search_ajax():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f"%{q}%"),
            Product.barcode.ilike(f"%{q}%"),
        ),
        Product.is_active == True,
        Product.quantity > 0,
    ).limit(10).all()

    result = [
        {
            "id": p.id,
            "name": p.name,
            "barcode": p.barcode or "",
            "sale_price": p.sale_price,
            "purchase_price": p.purchase_price,
            "quantity": p.quantity,
            "unit": p.unit,
        }
        for p in products
    ]
    return jsonify(result)