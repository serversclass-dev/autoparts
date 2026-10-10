from flask import Blueprint

oil_service_bp = Blueprint("oil_service", __name__, url_prefix="/oil-service")

from app.modules.oil_service import routes  # noqa: E402, F401