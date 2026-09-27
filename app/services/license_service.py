from datetime import date, datetime
import sqlite3

from app.database import get_db

REQUIRED_FIELDS = ("id", "software", "license_key", "vendor", "expiry", "seats_total", "seats_used")

def get_all_licenses_with_metrics():
    today = date.today()
    processed = []
    expiring_soon = 0
    expired = 0

    rows = get_db().execute("SELECT * FROM software_licenses ORDER BY expiry, software").fetchall()
    for row in rows:
        lic = dict(row)
        expiry_dt = datetime.strptime(lic["expiry"], "%Y-%m-%d").date()
        remaining_days = (expiry_dt - today).days

        if remaining_days < 0:
            status = "EXPIRED"
            badge = "danger"
            expired += 1
        elif remaining_days <= 14:
            status = "EXPIRING CRITICAL"
            badge = "danger"
            expiring_soon += 1
        elif remaining_days <= 30:
            status = "EXPIRING SOON"
            badge = "warning"
            expiring_soon += 1
        else:
            status = "HEALTHY"
            badge = "success"

        processed.append({
            "id": lic["id"],
            "software": lic["software"],
            "key": lic["license_key"],
            "vendor": lic["vendor"],
            "expiry": lic["expiry"],
            "seats_total": lic["seats_total"],
            "seats_used": lic["seats_used"],
            "days_left": remaining_days,
            "status": status,
            "badge": badge
        })

    return {
        "licenses": processed,
        "total": len(processed),
        "expiring_soon": expiring_soon,
        "expired": expired
    }


def _normalise_license(data, include_id=True):
    if not isinstance(data, dict):
        return None, {"request": "A JSON object is required."}
    fields = REQUIRED_FIELDS if include_id else REQUIRED_FIELDS[1:]
    values = {field: str(data.get(field, "")).strip() for field in fields}
    errors = {field: "This field is required." for field in fields if not values[field]}
    if errors:
        return None, errors
    try:
        datetime.strptime(values["expiry"], "%Y-%m-%d")
        values["seats_total"] = int(values["seats_total"])
        values["seats_used"] = int(values["seats_used"])
        if values["seats_total"] < 0 or values["seats_used"] < 0:
            raise ValueError
        if values["seats_used"] > values["seats_total"]:
            return None, {"seats_used": "Seats used cannot exceed seats total."}
    except ValueError:
        return None, {"expiry": "Use YYYY-MM-DD; seats must be non-negative whole numbers."}
    if include_id:
        values["id"] = values["id"].upper()
    return values, None


def create_license(data):
    license_, errors = _normalise_license(data)
    if errors:
        return None, errors
    try:
        get_db().execute(
            """INSERT INTO software_licenses
               (id, software, license_key, vendor, expiry, seats_total, seats_used)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            tuple(license_[field] for field in REQUIRED_FIELDS),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return None, {"id": "License ID already exists."}
    return license_, None


def update_license(license_id, data):
    license_, errors = _normalise_license(data, include_id=False)
    if errors:
        return None, errors
    db = get_db()
    result = db.execute(
        """UPDATE software_licenses
           SET software = ?, license_key = ?, vendor = ?, expiry = ?, seats_total = ?, seats_used = ?,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (license_["software"], license_["license_key"], license_["vendor"], license_["expiry"],
         license_["seats_total"], license_["seats_used"], license_id.upper()),
    )
    db.commit()
    if result.rowcount == 0:
        return None, {"id": "License not found."}
    license_["id"] = license_id.upper()
    return license_, None


def delete_license(license_id):
    db = get_db()
    result = db.execute("DELETE FROM software_licenses WHERE id = ?", (license_id.upper(),))
    db.commit()
    return result.rowcount > 0
