from flask import Blueprint

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

from app.modules.backup import routes  # noqa: E402, F401