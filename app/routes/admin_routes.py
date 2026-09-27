from flask import Blueprint, jsonify, request, session

from app.services.license_service import get_all_licenses_with_metrics
from app.services.system_service import create_system, delete_system, get_system_metrics

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def is_admin():
    return session.get("user") and session["user"]["role"] == "ADMIN"


@admin_bp.route("/overview", methods=["GET"])
def get_overview():
    if not is_admin():
        return jsonify({"error": "Unauthorized. Admin privileges required."}), 403

    lic_data = get_all_licenses_with_metrics()
    sys_data = get_system_metrics()

    return jsonify({
        "licenses": lic_data,
        "systems": sys_data
    }), 200


@admin_bp.route("/systems", methods=["POST"])
def register_system():
    if not is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403

    system, errors = create_system(request.get_json(silent=True))
    if errors:
        return jsonify({"error": "Validation failed.", "fields": errors}), 400
    return jsonify({"success": True, "system": system}), 201


@admin_bp.route("/systems/<hostname>", methods=["DELETE"])
def unregister_system(hostname):
    if not is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403

    removed = delete_system(hostname)
    if not removed:
        return jsonify({"error": "System not found."}), 404
    return jsonify({"success": True}), 200
