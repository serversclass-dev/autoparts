from flask import Blueprint

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")

from app.modules.categories import routes  # noqa: E402, F401