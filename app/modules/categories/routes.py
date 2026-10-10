from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.modules.categories import categories_bp
from app.models.category import Category
from app.extensions import db


@categories_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    query = Category.query
    if search:
        query = query.filter(Category.name.ilike(f"%{search}%"))
    categories = query.order_by(Category.name).all()
    return render_template("categories/list.html", categories=categories, search=search)


@categories_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("categories.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("اسم التصنيف مطلوب.", "danger")
            return render_template("categories/form.html", category=None)

        if Category.query.filter_by(name=name).first():
            flash("هذا التصنيف موجود مسبقاً.", "danger")
            return render_template("categories/form.html", category=None)

        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        flash(f"تم إضافة التصنيف '{name}' بنجاح.", "success")
        return redirect(url_for("categories.index"))

    return render_template("categories/form.html", category=None)


@categories_bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit(category_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("categories.index"))

    category = Category.query.get_or_404(category_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("اسم التصنيف مطلوب.", "danger")
            return render_template("categories/form.html", category=category)

        existing = Category.query.filter_by(name=name).first()
        if existing and existing.id != category_id:
            flash("هذا التصنيف موجود مسبقاً.", "danger")
            return render_template("categories/form.html", category=category)

        category.name = name
        category.description = description
        db.session.commit()
        flash(f"تم تعديل التصنيف '{name}' بنجاح.", "success")
        return redirect(url_for("categories.index"))

    return render_template("categories/form.html", category=category)


@categories_bp.route("/<int:category_id>/delete", methods=["POST"])
@login_required
def delete(category_id):
    if not current_user.is_admin:
        flash("ليس لديك صلاحية لهذه العملية.", "danger")
        return redirect(url_for("categories.index"))

    category = Category.query.get_or_404(category_id)

    if category.product_count > 0:
        flash("لا يمكن حذف تصنيف يحتوي على منتجات.", "danger")
        return redirect(url_for("categories.index"))

    db.session.delete(category)
    db.session.commit()
    flash(f"تم حذف التصنيف '{category.name}'.", "success")
    return redirect(url_for("categories.index"))