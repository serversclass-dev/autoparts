from flask import Blueprint

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")

from app.modules.suppliers import routes  # noqa: E402, F401