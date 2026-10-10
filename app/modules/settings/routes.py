import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
from app.modules.settings import settings_bp
from app.models.setting import Setting
from app.core.permissions import admin_required
from app.core.audit import log_action
from app.extensions import db


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    if request.method == "POST":
        fields = [
            "shop_name", "shop_name_en", "shop_address",
            "shop_phone", "shop_email", "currency",
            "invoice_footer", "vat_number", "vat_rate",
            "low_stock_default",
        ]
        for field in fields:
            val = request.form.get(field, "").strip()
            Setting.set(field, val)

        # Handle logo upload
        logo_file = request.files.get("shop_logo")
        if logo_file and logo_file.filename:
            allowed = {"png", "jpg", "jpeg", "svg", "webp"}
            ext = logo_file.filename.rsplit(".", 1)[-1].lower()
            if ext in allowed:
                upload_dir = os.path.join(current_app.root_path, "..", "instance", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                logo_path = os.path.join(upload_dir, f"shop_logo.{ext}")
                logo_file.save(logo_path)
                Setting.set("shop_logo", f"shop_logo.{ext}")
            else:
                flash("صيغة الشعار غير مدعومة. استخدم PNG أو JPG أو SVG.", "warning")

        log_action("settings_update", description="تحديث إعدادات المحل")
        flash("تم حفظ الإعدادات بنجاح.", "success")
        return redirect(url_for("settings.index"))

    settings = Setting.get_all()
    return render_template("settings/index.html", settings=settings)


@settings_bp.route("/users")
@login_required
@admin_required
def users():
    from app.models.user import User
    users = User.query.order_by(User.role, User.full_name).all()
    return render_template("settings/users.html", users=users)


@settings_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    from app.models.user import User

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "cashier")
        password = request.form.get("password", "")

        if not username or not full_name or not password:
            flash("جميع الحقول مطلوبة.", "danger")
            return render_template("settings/user_form.html", user=None)

        if len(password) < 6:
            flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "danger")
            return render_template("settings/user_form.html", user=None)

        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم موجود مسبقاً.", "danger")
            return render_template("settings/user_form.html", user=None)

        user = User(
            username=username,
            full_name=full_name,
            role=role,
            is_active=True,
            force_password_change=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action("user_create", entity="User", entity_id=user.id,
                   description=f"إنشاء مستخدم: {username} ({role})")
        flash(f"تم إنشاء المستخدم '{username}' بنجاح.", "success")
        return redirect(url_for("settings.users"))

    return render_template("settings/user_form.html", user=None)


@settings_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    from app.models.user import User

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", user.role)
        is_active = request.form.get("is_active") == "1"

        # Prevent disabling/changing last active admin
        if user.is_admin and (not is_active or role != "admin"):
            active_admins = User.query.filter_by(role="admin", is_active=True).count()
            if active_admins <= 1:
                flash("لا يمكن تغيير دور أو تعطيل آخر مدير نشط.", "danger")
                return render_template("settings/user_form.html", user=user)

        old_role = user.role
        user.full_name = full_name
        user.role = role
        user.is_active = is_active
        db.session.commit()

        if old_role != role:
            log_action("user_role_change", entity="User", entity_id=user.id,
                       description=f"تغيير دور {user.username}: {old_role} → {role}")
        else:
            log_action("user_edit", entity="User", entity_id=user.id,
                       description=f"تعديل بيانات: {user.username}")

        flash(f"تم تعديل بيانات '{user.username}' بنجاح.", "success")
        return redirect(url_for("settings.users"))

    return render_template("settings/user_form.html", user=user)


@settings_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    from app.models.user import User

    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "")

    if len(new_password) < 6:
        flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "danger")
        return redirect(url_for("settings.users"))

    user.set_password(new_password)
    user.force_password_change = True
    db.session.commit()
    log_action("password_reset", entity="User", entity_id=user.id,
               description=f"إعادة تعيين كلمة مرور: {user.username}")
    flash(f"تم إعادة تعيين كلمة مرور '{user.username}'.", "success")
    return redirect(url_for("settings.users"))


@settings_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    from app.models.user import User

    user = User.query.get_or_404(user_id)

    if user.id == current_app.config.get("CURRENT_USER_ID"):
        flash("لا يمكنك تعطيل حسابك الخاص.", "danger")
        return redirect(url_for("settings.users"))

    if user.is_admin and user.is_active:
        active_admins = User.query.filter_by(role="admin", is_active=True).count()
        if active_admins <= 1:
            flash("لا يمكن تعطيل آخر مدير نشط.", "danger")
            return redirect(url_for("settings.users"))

    user.is_active = not user.is_active
    db.session.commit()
    status = "تفعيل" if user.is_active else "تعطيل"
    log_action("user_edit", entity="User", entity_id=user.id,
               description=f"{status} المستخدم: {user.username}")
    flash(f"تم {status} المستخدم '{user.username}'.", "success")
    return redirect(url_for("settings.users"))