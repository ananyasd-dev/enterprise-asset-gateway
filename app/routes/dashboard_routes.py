from flask import Blueprint, jsonify, session

from app.services.asset_service import get_asset_metrics

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Return live, local dashboard counters for the signed-in user."""
    if not session.get("user"):
        return jsonify({"error": "Authentication required."}), 401
    return jsonify({"assets": get_asset_metrics()}), 200
