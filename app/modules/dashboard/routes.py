from datetime import datetime, timedelta
from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app.modules.dashboard import dashboard_bp
from app.extensions import db
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.purchase import Purchase
from app.models.expense import Expense
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.customer_payment import CustomerPayment
from app.models.supplier_payment import SupplierPayment


@dashboard_bp.route("/")
@login_required
def index():
    today = datetime.utcnow().date()
    first_of_month = today.replace(day=1)

    # ── Today stats ───────────────────────────────────────────
    today_sales = Sale.query.filter(
        func.date(Sale.created_at) == today,
        Sale.status != "cancelled",
    ).all()
    today_revenue = sum(s.total for s in today_sales)
    today_profit = sum(s.profit for s in today_sales)
    today_count = len(today_sales)

    # ── Month stats ────────────────────────────────────────────
    month_sales = Sale.query.filter(
        Sale.created_at >= first_of_month,
        Sale.status != "cancelled",
    ).all()
    month_revenue = sum(s.total for s in month_sales)
    month_profit = sum(s.profit for s in month_sales)

    month_expenses = db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(Expense.expense_date >= first_of_month).scalar()

    # ── Inventory ──────────────────────────────────────────────
    total_products = Product.query.filter_by(is_active=True).count()
    low_stock = Product.query.filter(
        Product.quantity <= Product.low_stock_alert,
        Product.is_active == True,
    ).all()

    stock_value = db.session.query(
        func.coalesce(func.sum(Product.quantity * Product.purchase_price), 0)
    ).filter_by(is_active=True).scalar()

    # ── Customer debts — compute from transactions, NOT property ──
    # Sum of credit sales per customer minus payments
    credit_sales_sub = db.session.query(
        Sale.customer_id,
        func.coalesce(func.sum(Sale.total), 0).label("total_credit")
    ).filter(
        Sale.status == "on_credit",
        Sale.customer_id.isnot(None),
    ).group_by(Sale.customer_id).subquery()

    payments_sub = db.session.query(
        CustomerPayment.customer_id,
        func.coalesce(func.sum(CustomerPayment.amount), 0).label("total_paid")
    ).group_by(CustomerPayment.customer_id).subquery()

    # Total customer debt = sum of (credit_sales - payments) where positive
    all_customers = Customer.query.filter_by(is_active=True).all()
    customer_debts = sum(c.balance for c in all_customers if c.balance > 0)

    # ── Supplier debts ─────────────────────────────────────────
    all_suppliers = Supplier.query.filter_by(is_active=True).all()
    supplier_debts = sum(s.balance for s in all_suppliers if s.balance > 0)

    # ── Top products this month ────────────────────────────────
    top_products = (
        db.session.query(
            Product.name,
            func.sum(SaleItem.quantity).label("total_qty"),
            func.sum(SaleItem.total).label("total_amount"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.created_at >= first_of_month,
            Sale.status != "cancelled",
        )
        .group_by(Product.id)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(5)
        .all()
    )

    # ── Last 7 days chart ──────────────────────────────────────
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        label = day.strftime("%m/%d")
        amount = db.session.query(
            func.coalesce(func.sum(Sale.total), 0)
        ).filter(
            func.date(Sale.created_at) == day,
            Sale.status != "cancelled",
        ).scalar()
        chart_labels.append(label)
        chart_data.append(float(amount))

    # ── Recent sales ───────────────────────────────────────────
    recent_sales = (
        Sale.query.filter(Sale.status != "cancelled")
        .order_by(Sale.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        today_revenue=today_revenue,
        today_profit=today_profit,
        today_count=today_count,
        month_revenue=month_revenue,
        month_profit=month_profit,
        month_expenses=float(month_expenses),
        total_products=total_products,
        low_stock=low_stock,
        stock_value=float(stock_value),
        customer_debts=customer_debts,
        supplier_debts=supplier_debts,
        top_products=top_products,
        chart_labels=chart_labels,
        chart_data=chart_data,
        recent_sales=recent_sales,
    )