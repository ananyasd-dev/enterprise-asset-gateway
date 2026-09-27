"""Asset inventory operations backed by the local SQLite database."""

import sqlite3

from app.database import get_db

REQUIRED_FIELDS = ("asset_id", "hostname", "serial_number", "department", "location")
OPTIONAL_FIELDS = ("asset_type", "status")

# Fixed vocabulary so the UI can always map a status to the right badge
# colour, instead of trusting arbitrary free text from the form.
VALID_STATUSES = ("Active", "In Repair", "Retired")
STATUS_BADGE = {"Active": "success", "In Repair": "warning", "Retired": "danger"}


def _normalise_asset(data, require_id=True):
    if not isinstance(data, dict):
        return None, {"request": "A JSON object is required."}

    required = REQUIRED_FIELDS if require_id else REQUIRED_FIELDS[1:]  # drop asset_id for edits
    fields = (*required, *OPTIONAL_FIELDS)
    asset = {field: str(data.get(field, "")).strip() for field in fields}

    errors = {field: "This field is required." for field in required if not asset[field]}
    if errors:
        return None, errors

    if require_id:
        asset["asset_id"] = asset["asset_id"].upper()
    asset["hostname"] = asset["hostname"].upper()
    asset["serial_number"] = asset["serial_number"].upper()
    asset["asset_type"] = asset["asset_type"] or "Workstation"
    status = asset["status"] or "Active"
    if status not in VALID_STATUSES:
        return None, {"status": f"Status must be one of: {', '.join(VALID_STATUSES)}."}
    asset["status"] = status
    return asset, None


def list_assets(search=None):
    db = get_db()
    query = "SELECT * FROM assets"
    params = []
    if search:
        value = f"%{search.strip()}%"
        query += " WHERE asset_id LIKE ? OR hostname LIKE ? OR serial_number LIKE ? OR department LIKE ? OR location LIKE ?"
        params = [value] * 5
    query += " ORDER BY asset_id COLLATE NOCASE"
    return [dict(row) for row in db.execute(query, params).fetchall()]


def get_asset_metrics():
    """Return dashboard counters calculated from the persisted asset inventory."""
    db = get_db()
    row = db.execute(
        """SELECT
               COUNT(*) AS total_assets,
               SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_assets,
               COUNT(DISTINCT department) AS departments,
               COUNT(DISTINCT location) AS locations
           FROM assets"""
    ).fetchone()
    return {
        "total_assets": row["total_assets"],
        "active_assets": row["active_assets"] or 0,
        "departments": row["departments"],
        "locations": row["locations"],
    }


def create_asset(data):
    asset, errors = _normalise_asset(data)
    if errors:
        return None, errors

    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO assets
               (asset_id, hostname, serial_number, department, location, asset_type, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            tuple(asset[field] for field in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None, {"asset_id": "Asset ID or serial number already exists."}

    row = db.execute("SELECT * FROM assets WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row), None


def update_asset(asset_id, data):
    asset, errors = _normalise_asset(data, require_id=False)
    if errors:
        return None, errors

    db = get_db()
    try:
        result = db.execute(
            """UPDATE assets
               SET hostname = ?, serial_number = ?, department = ?, location = ?,
                   asset_type = ?, status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE asset_id = ?""",
            (asset["hostname"], asset["serial_number"], asset["department"], asset["location"],
             asset["asset_type"], asset["status"], asset_id.upper()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None, {"serial_number": "Another asset already uses that serial number."}

    if result.rowcount == 0:
        return None, {"asset_id": "Asset not found."}

    row = db.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id.upper(),)).fetchone()
    return dict(row), None


def delete_asset(asset_id):
    db = get_db()
    result = db.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id.upper(),))
    db.commit()
    return result.rowcount > 0
