from flask import Blueprint

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

from app.modules.expenses import routes  # noqa: E402, F401