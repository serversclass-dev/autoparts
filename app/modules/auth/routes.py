from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.modules.auth import auth_bp
from app.models.user import User
from app.models.setting import Setting
from app.core.audit import log_action
from app.extensions import db


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not username or not password:
            flash("يرجى إدخال اسم المستخدم وكلمة المرور.", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("هذا الحساب معطل. تواصل مع المدير.", "danger")
            return render_template("auth/login.html")

        # Check lockout
        if user.is_locked:
            remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            flash(f"الحساب مقفل مؤقتاً. حاول بعد {remaining} دقيقة.", "danger")
            return render_template("auth/login.html")

        if not user.check_password(password):
            # Get settings for lockout config
            max_attempts = int(Setting.get("login_max_attempts", 5))
            lockout_minutes = int(Setting.get("login_lockout_minutes", 15))
            user.record_failed_login(max_attempts=max_attempts, lockout_minutes=lockout_minutes)
            db.session.commit()

            remaining_attempts = max_attempts - user.failed_attempts
            if user.is_locked:
                flash(f"تم قفل الحساب مؤقتاً لمدة {lockout_minutes} دقيقة بسبب محاولات خاطئة متعددة.", "danger")
            else:
                flash(f"كلمة المرور غير صحيحة. المحاولات المتبقية: {max(remaining_attempts, 0)}", "danger")
            return render_template("auth/login.html")

        # Success
        user.record_success_login()
        db.session.commit()
        login_user(user, remember=remember)
        log_action("login", entity="User", entity_id=user.id,
                   description=f"تسجيل دخول: {user.username}")

        # Force password change
        if user.force_password_change:
            flash("يجب عليك تغيير كلمة المرور قبل المتابعة.", "warning")
            return redirect(url_for("auth.force_change_password"))

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("logout", entity="User", entity_id=current_user.id,
               description=f"تسجيل خروج: {current_user.username}")
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/force-change-password", methods=["GET", "POST"])
@login_required
def force_change_password():
    if not current_user.force_password_change:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if len(new_password) < 6:
            flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "danger")
            return render_template("auth/force_change_password.html")

        if new_password != confirm:
            flash("كلمتا المرور غير متطابقتين.", "danger")
            return render_template("auth/force_change_password.html")

        current_user.set_password(new_password)
        current_user.force_password_change = False
        db.session.commit()
        log_action("password_reset", entity="User", entity_id=current_user.id,
                   description="تغيير كلمة المرور الإجباري")
        flash("تم تغيير كلمة المرور بنجاح. مرحباً!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/force_change_password.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if full_name:
            current_user.full_name = full_name

        if current_password:
            if not current_user.check_password(current_password):
                flash("كلمة المرور الحالية غير صحيحة.", "danger")
                return render_template("auth/profile.html")
            if new_password != confirm_password:
                flash("كلمة المرور الجديدة غير متطابقة.", "danger")
                return render_template("auth/profile.html")
            if len(new_password) < 6:
                flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "danger")
                return render_template("auth/profile.html")
            current_user.set_password(new_password)
            log_action("password_reset", entity="User", entity_id=current_user.id,
                       description="تغيير كلمة المرور الشخصية")

        db.session.commit()
        flash("تم تحديث البيانات بنجاح.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")