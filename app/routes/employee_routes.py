from flask import Blueprint, jsonify, session

from app.services.system_service import get_system_metrics

employee_bp = Blueprint("employee", __name__, url_prefix="/api/employee")


@employee_bp.route("/workstation-status", methods=["GET"])
def workstation_status():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Unauthorized."}), 401

    metrics = get_system_metrics()
    status = "Operational" if metrics["total"] > 0 else "Degraded"

    return jsonify({
        "status": status,
        "office_network": f"{metrics['total']} host(s) monitored",
        "systems_available": metrics["online"],
        "user_workstation": "IT-WS-DEV01",
    }), 200
