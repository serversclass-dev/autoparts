from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def admin_required(f):
    """مدير فقط."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_admin:
            flash("هذه الصفحة متاحة للمدير فقط.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated


def login_required_custom(f):
    """تسجيل دخول مطلوب."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يرجى تسجيل الدخول أولاً.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def cashier_or_admin(f):
    """كاشير أو مدير."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        if current_user.role not in ("admin", "cashier"):
            flash("ليس لديك صلاحية للوصول.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Role checks (non-decorator) ───────────────────────────────────────────────
def is_admin():
    return current_user.is_authenticated and current_user.is_admin


def can_view_prices():
    """الكاشير لا يرى أسعار الشراء أو الأرباح."""
    return current_user.is_authenticated and current_user.is_admin


def can_delete():
    return current_user.is_authenticated and current_user.is_admin


def can_cancel_invoice():
    return current_user.is_authenticated and current_user.is_admin


def can_manage_users():
    return current_user.is_authenticated and current_user.is_admin