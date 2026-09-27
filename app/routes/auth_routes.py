from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash

from app.database import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id", "").strip().upper()
    password = data.get("password", "")

    if not employee_id or not password:
        return jsonify({"success": False, "message": "Employee ID and password are required."}), 400

    db = get_db()
    row = db.execute(
        "SELECT employee_id, password_hash, name, role, department FROM users WHERE employee_id = ?",
        (employee_id,),
    ).fetchone()

    # Always run check_password_hash even on a miss (against a dummy hash) so
    # a nonexistent employee_id doesn't respond faster than a wrong password —
    # that timing difference is enough to let an attacker enumerate valid IDs.
    dummy_hash = "pbkdf2:sha256:600000$00000000000000000000000000000000"
    stored_hash = row["password_hash"] if row else dummy_hash
    password_ok = check_password_hash(stored_hash, password)

    if row is None or not password_ok:
        return jsonify({"success": False, "message": "Access Denied: Invalid credentials."}), 401

    session["user"] = {
        "token": row["employee_id"],
        "name": row["name"],
        "role": row["role"],
        "department": row["department"],
    }
    return jsonify({"success": True, "user": session["user"]}), 200


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True}), 200


@auth_bp.route("/api/me", methods=["GET"])
def current_user():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user}), 200
