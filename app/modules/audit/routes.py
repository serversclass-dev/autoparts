from datetime import datetime
from flask import render_template, request
from flask_login import login_required
from app.modules.audit import audit_bp
from app.core.audit import AuditLog
from app.core.permissions import admin_required
from app.models.user import User
from app.extensions import db


@audit_bp.route("/")
@login_required
@admin_required
def index():
    search = request.args.get("search", "").strip()
    user_id = request.args.get("user_id", "")
    action = request.args.get("action", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = request.args.get("page", 1, type=int)

    query = AuditLog.query

    if search:
        query = query.filter(AuditLog.description.ilike(f"%{search}%"))
    if user_id:
        query = query.filter(AuditLog.user_id == int(user_id))
    if action:
        query = query.filter(AuditLog.action == action)
    if date_from:
        try:
            query = query.filter(
                AuditLog.created_at >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.created_at <= dt)
        except ValueError:
            pass

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=30)
    users = User.query.order_by(User.full_name).all()
    actions = AuditLog.ACTIONS

    return render_template(
        "audit/index.html",
        logs=logs,
        users=users,
        actions=actions,
        search=search,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )