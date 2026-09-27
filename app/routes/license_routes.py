from flask import Blueprint, jsonify, request, session

from app.services.license_service import (
    create_license,
    delete_license,
    get_all_licenses_with_metrics,
    update_license,
)

licenses_bp = Blueprint("licenses", __name__)


def _is_admin():
    return session.get("user", {}).get("role") == "ADMIN"


@licenses_bp.route("/api/licenses", methods=["GET"])
def get_licenses():
    if not session.get("user"):
        return jsonify({"error": "Authentication required."}), 401
    return jsonify(get_all_licenses_with_metrics()), 200


@licenses_bp.route("/api/licenses", methods=["POST"])
def add_license():
    if not _is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403
    license_, errors = create_license(request.get_json(silent=True))
    if errors:
        return jsonify({"error": "Validation failed.", "fields": errors}), 400
    return jsonify({"success": True, "license": license_}), 201


@licenses_bp.route("/api/licenses/<license_id>", methods=["PUT"])
def edit_license(license_id):
    if not _is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403
    license_, errors = update_license(license_id, request.get_json(silent=True))
    if errors:
        status = 404 if "id" in errors and errors["id"] == "License not found." else 400
        return jsonify({"error": "Validation failed.", "fields": errors}), status
    return jsonify({"success": True, "license": license_}), 200


@licenses_bp.route("/api/licenses/<license_id>", methods=["DELETE"])
def remove_license(license_id):
    if not _is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403
    removed = delete_license(license_id)
    if not removed:
        return jsonify({"error": "License not found."}), 404
    return jsonify({"success": True}), 200
