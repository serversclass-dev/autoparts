from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from app.modules.expenses import expenses_bp
from app.models.expense import Expense
from app.extensions import db


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("هذه الصفحة للمدير فقط.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


@expenses_bp.route("/")
@login_required
@admin_required
def index():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = request.args.get("page", 1, type=int)

    query = Expense.query

    if search:
        query = query.filter(Expense.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(Expense.category == category)
    if date_from:
        try:
            query = query.filter(Expense.expense_date >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Expense.expense_date <= dt)
        except ValueError:
            pass

    expenses = query.order_by(Expense.expense_date.desc()).paginate(page=page, per_page=20)

    # Total for filtered results
    total_amount = db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        *([Expense.category == category] if category else []),
        *([Expense.expense_date >= datetime.strptime(date_from, "%Y-%m-%d")] if date_from else []),
        *([Expense.expense_date <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)] if date_to else []),
    ).scalar()

    # Category totals
    cat_totals = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label("total")
    ).group_by(Expense.category).all()

    return render_template(
        "expenses/list.html",
        expenses=expenses,
        search=search,
        category=category,
        date_from=date_from,
        date_to=date_to,
        total_amount=total_amount,
        cat_totals=cat_totals,
        categories=Expense.CATEGORIES,
    )


@expenses_bp.route("/create", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "other")
        amount = float(request.form.get("amount", 0))
        payment_method = request.form.get("payment_method", "cash")
        notes = request.form.get("notes", "").strip() or None
        expense_date_str = request.form.get("expense_date", "")

        if not title:
            flash("عنوان المصروف مطلوب.", "danger")
            return render_template("expenses/form.html", expense=None,
                                   categories=Expense.CATEGORIES,
                                   payment_methods=Expense.PAYMENT_METHODS)
        if amount <= 0:
            flash("المبلغ يجب أن يكون أكبر من صفر.", "danger")
            return render_template("expenses/form.html", expense=None,
                                   categories=Expense.CATEGORIES,
                                   payment_methods=Expense.PAYMENT_METHODS)

        try:
            expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d") if expense_date_str else datetime.utcnow()
        except ValueError:
            expense_date = datetime.utcnow()

        expense = Expense(
            title=title,
            category=category,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            expense_date=expense_date,
            user_id=current_user.id,
        )
        db.session.add(expense)
        db.session.commit()
        flash(f"تم تسجيل المصروف '{title}' بمبلغ {amount:.2f} ر.س.", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", expense=None,
                           categories=Expense.CATEGORIES,
                           payment_methods=Expense.PAYMENT_METHODS)


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("عنوان المصروف مطلوب.", "danger")
            return render_template("expenses/form.html", expense=expense,
                                   categories=Expense.CATEGORIES,
                                   payment_methods=Expense.PAYMENT_METHODS)

        expense.title = title
        expense.category = request.form.get("category", "other")
        expense.amount = float(request.form.get("amount", 0))
        expense.payment_method = request.form.get("payment_method", "cash")
        expense.notes = request.form.get("notes", "").strip() or None
        date_str = request.form.get("expense_date", "")
        try:
            expense.expense_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else expense.expense_date
        except ValueError:
            pass

        db.session.commit()
        flash(f"تم تعديل المصروف '{title}' بنجاح.", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", expense=expense,
                           categories=Expense.CATEGORIES,
                           payment_methods=Expense.PAYMENT_METHODS)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash(f"تم حذف المصروف '{expense.title}'.", "success")
    return redirect(url_for("expenses.index"))


@expenses_bp.route("/export/excel")
@login_required
@admin_required
def export_excel():
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    import io

    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    category = request.args.get("category", "")

    query = Expense.query
    if category:
        query = query.filter(Expense.category == category)
    if date_from:
        try:
            query = query.filter(Expense.expense_date >= datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Expense.expense_date <= dt)
        except ValueError:
            pass

    expenses = query.order_by(Expense.expense_date.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "المصروفات"
    ws.sheet_view.rightToLeft = True

    header_fill = PatternFill("solid", fgColor="1e3a5f")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    headers = ["#", "التاريخ", "البند", "الفئة", "المبلغ", "طريقة الدفع", "ملاحظات", "المسجّل"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row, exp in enumerate(expenses, 2):
        ws.cell(row=row, column=1, value=row - 1)
        ws.cell(row=row, column=2, value=exp.expense_date.strftime("%Y-%m-%d"))
        ws.cell(row=row, column=3, value=exp.title)
        ws.cell(row=row, column=4, value=exp.category_label)
        ws.cell(row=row, column=5, value=exp.amount)
        ws.cell(row=row, column=6, value=exp.payment_method_label)
        ws.cell(row=row, column=7, value=exp.notes or "")
        ws.cell(row=row, column=8, value=exp.user.full_name if exp.user else "")

    # Total row
    total_row = len(expenses) + 2
    ws.cell(row=total_row, column=4, value="الإجمالي").font = Font(bold=True)
    ws.cell(row=total_row, column=5, value=sum(e.amount for e in expenses)).font = Font(bold=True)

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 25
    ws.column_dimensions["H"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=expenses.xlsx"},
    )