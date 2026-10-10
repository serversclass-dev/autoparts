import os
import shutil
import glob
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required
from app.modules.backup import backup_bp
from app.core.permissions import admin_required
from app.core.audit import log_action


def get_backup_dir():
    backup_dir = os.path.join(current_app.root_path, "..", "instance", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return os.path.abspath(backup_dir)


def get_db_path():
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(current_app.root_path, "..", path)
        return os.path.abspath(path)
    return None


def create_backup(label="manual"):
    db_path = get_db_path()
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError("لم يتم العثور على قاعدة البيانات.")

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"autoparts_{label}_{timestamp}.db"
    dest = os.path.join(backup_dir, filename)
    shutil.copy2(db_path, dest)
    return filename, dest


def cleanup_old_backups(keep=30):
    backup_dir = get_backup_dir()
    pattern = os.path.join(backup_dir, "autoparts_*.db")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for old_file in files[keep:]:
        try:
            os.remove(old_file)
        except Exception:
            pass


def list_backups():
    backup_dir = get_backup_dir()
    pattern = os.path.join(backup_dir, "autoparts_*.db")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    result = []
    for f in files:
        stat = os.stat(f)
        result.append({
            "filename": os.path.basename(f),
            "path": f,
            "size_kb": round(stat.st_size / 1024, 1),
            "created": datetime.fromtimestamp(stat.st_mtime),
        })
    return result


@backup_bp.route("/")
@login_required
@admin_required
def index():
    backups = list_backups()
    return render_template("backup/index.html", backups=backups)


@backup_bp.route("/create", methods=["POST"])
@login_required
@admin_required
def create():
    try:
        filename, _ = create_backup(label="manual")
        cleanup_old_backups(keep=30)
        log_action("backup_create", description=f"نسخة احتياطية يدوية: {filename}")
        flash(f"تم إنشاء النسخة الاحتياطية: {filename}", "success")
    except Exception as e:
        flash(f"فشل إنشاء النسخة الاحتياطية: {str(e)}", "danger")
    return redirect(url_for("backup.index"))


@backup_bp.route("/download/<filename>")
@login_required
@admin_required
def download(filename):
    backup_dir = get_backup_dir()
    file_path = os.path.join(backup_dir, filename)
    if not os.path.exists(file_path):
        flash("الملف غير موجود.", "danger")
        return redirect(url_for("backup.index"))
    # Security: ensure file is inside backup_dir
    if not os.path.abspath(file_path).startswith(backup_dir):
        flash("مسار غير صالح.", "danger")
        return redirect(url_for("backup.index"))
    return send_file(file_path, as_attachment=True, download_name=filename)


@backup_bp.route("/restore/<filename>", methods=["POST"])
@login_required
@admin_required
def restore(filename):
    backup_dir = get_backup_dir()
    file_path = os.path.join(backup_dir, filename)

    if not os.path.exists(file_path):
        flash("الملف غير موجود.", "danger")
        return redirect(url_for("backup.index"))

    if not os.path.abspath(file_path).startswith(backup_dir):
        flash("مسار غير صالح.", "danger")
        return redirect(url_for("backup.index"))

    try:
        # Safety backup before restore
        safety_name, _ = create_backup(label="pre_restore")

        db_path = get_db_path()
        if not db_path:
            raise Exception("لم يتم العثور على قاعدة البيانات.")

        shutil.copy2(file_path, db_path)
        log_action("backup_restore",
                   description=f"استعادة نسخة: {filename} — نسخة أمان: {safety_name}")
        flash(f"تمت الاستعادة من: {filename}. نسخة أمان أُنشئت: {safety_name}", "success")
    except Exception as e:
        flash(f"فشل الاستعادة: {str(e)}", "danger")

    return redirect(url_for("backup.index"))


@backup_bp.route("/delete/<filename>", methods=["POST"])
@login_required
@admin_required
def delete(filename):
    backup_dir = get_backup_dir()
    file_path = os.path.join(backup_dir, filename)

    if not os.path.abspath(file_path).startswith(backup_dir):
        flash("مسار غير صالح.", "danger")
        return redirect(url_for("backup.index"))

    try:
        os.remove(file_path)
        flash(f"تم حذف النسخة: {filename}", "success")
    except Exception as e:
        flash(f"فشل الحذف: {str(e)}", "danger")

    return redirect(url_for("backup.index"))