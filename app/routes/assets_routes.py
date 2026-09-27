from flask import Blueprint, jsonify, render_template, request, session

from app.services.asset_service import create_asset, delete_asset, list_assets, update_asset

assets_bp = Blueprint("assets", __name__)


def is_authenticated():
    return bool(session.get("user"))


def is_admin():
    return session.get("user", {}).get("role") == "ADMIN"


@assets_bp.route("/assets")
def assets_page():
    if not is_authenticated():
        return render_template("login.html"), 401
    return render_template("page2.html", user=session["user"])


@assets_bp.route("/api/assets", methods=["GET"])
def get_assets():
    if not is_authenticated():
        return jsonify({"error": "Authentication required."}), 401
    assets = list_assets(request.args.get("search"))
    return jsonify({"assets": assets, "total": len(assets)}), 200


@assets_bp.route("/api/assets", methods=["POST"])
def register_asset():
    if not is_authenticated():
        return jsonify({"error": "Authentication required."}), 401
    if not is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403

    asset, errors = create_asset(request.get_json(silent=True))
    if errors:
        return jsonify({"error": "Validation failed.", "fields": errors}), 400
    return jsonify({"success": True, "asset": asset}), 201


@assets_bp.route("/api/assets/<asset_id>", methods=["PUT"])
def edit_asset(asset_id):
    if not is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403

    asset, errors = update_asset(asset_id, request.get_json(silent=True))
    if errors:
        status = 404 if errors.get("asset_id") == "Asset not found." else 400
        return jsonify({"error": "Validation failed.", "fields": errors}), status
    return jsonify({"success": True, "asset": asset}), 200


@assets_bp.route("/api/assets/<asset_id>", methods=["DELETE"])
def remove_asset(asset_id):
    if not is_admin():
        return jsonify({"error": "Administrator privileges required."}), 403

    removed = delete_asset(asset_id)
    if not removed:
        return jsonify({"error": "Asset not found."}), 404
    return jsonify({"success": True}), 200
