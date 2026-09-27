"""Small SQLite helper used by the local-only application."""

import os
import sqlite3
from datetime import date, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash


USER_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'EMPLOYEE')),
    department TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

# Seed accounts for first run only. These are DEMO credentials — change them
# (or delete the seed step entirely) before this ever touches real data.
DEFAULT_USERS = [
    {
        "employee_id": "EMP-001",
        "password": "admin123",
        "name": "Senior Admin Officer",
        "role": "ADMIN",
        "department": "IT Operations",
    },
    {
        "employee_id": "EMP-002",
        "password": "employee123",
        "name": "Workstation Engineer",
        "role": "EMPLOYEE",
        "department": "Hardware Support",
    },
]

ASSET_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL UNIQUE,
    hostname TEXT NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    location TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'Workstation',
    status TEXT NOT NULL DEFAULT 'Active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

LICENSE_SCHEMA = """
CREATE TABLE IF NOT EXISTS software_licenses (
    id TEXT PRIMARY KEY,
    software TEXT NOT NULL,
    license_key TEXT NOT NULL,
    vendor TEXT NOT NULL,
    expiry TEXT NOT NULL,
    seats_total INTEGER NOT NULL CHECK(seats_total >= 0),
    seats_used INTEGER NOT NULL DEFAULT 0 CHECK(seats_used >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(seats_used <= seats_total)
)
"""

# Systems the admin wants live-monitored. Unlike the original prototype these
# are real, admin-managed rows rather than a hardcoded in-memory list tied to
# one office's IP range — any team can register the hosts on their own
# network here and the dashboard will ping whatever is actually configured.
SYSTEM_SCHEMA = """
CREATE TABLE IF NOT EXISTS monitored_systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL UNIQUE,
    ip_address TEXT NOT NULL,
    os TEXT NOT NULL DEFAULT 'Unknown',
    location TEXT NOT NULL DEFAULT 'Unspecified',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def get_db():
    """Return the request-local SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the local tables and migrate the original demo data once."""
    db = get_db()
    db.execute(USER_SCHEMA)
    db.execute(ASSET_SCHEMA)
    db.execute(LICENSE_SCHEMA)
    db.execute(SYSTEM_SCHEMA)
    _seed_default_users(db)
    _seed_legacy_licenses(db)
    _seed_legacy_systems(db)
    db.commit()


def _seed_default_users(db):
    """Create the demo accounts (hashed) on first run only."""
    existing = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing:
        return

    db.executemany(
        """INSERT INTO users (employee_id, password_hash, name, role, department)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (
                u["employee_id"], generate_password_hash(u["password"], method="pbkdf2:sha256"),
                u["name"], u["role"], u["department"],
            )
            for u in DEFAULT_USERS
        ],
    )


def _seed_legacy_licenses(db):
    """Preserve the original prototype's sample license inventory on first run.

    Expiry dates are computed relative to *now* (see app/models.py) so a
    fresh install always demonstrates one of each status — this table
    doesn't silently look "all expired" a few weeks after setup.
    """
    existing = db.execute("SELECT COUNT(*) FROM software_licenses").fetchone()[0]
    if existing:
        return

    from app.models import SOFTWARE_LICENSES

    today = date.today()
    db.executemany(
        """INSERT INTO software_licenses
           (id, software, license_key, vendor, expiry, seats_total, seats_used)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                license_["id"], license_["software"], license_["key"], license_["vendor"],
                (today + timedelta(days=license_["expiry_days_from_now"])).isoformat(),
                license_["seats_total"], license_["seats_used"],
            )
            for license_ in SOFTWARE_LICENSES
        ],
    )


def _seed_legacy_systems(db):
    """Preserve the original prototype's sample host list on first run only.

    These are demo IPs from the original office network — an admin should
    remove or replace them from the dashboard with hosts that actually exist
    on whatever network this instance is deployed to.
    """
    existing = db.execute("SELECT COUNT(*) FROM monitored_systems").fetchone()[0]
    if existing:
        return

    from app.models import OFFICE_SYSTEMS

    db.executemany(
        """INSERT INTO monitored_systems (hostname, ip_address, os, location)
           VALUES (?, ?, ?, ?)""",
        [
            (sys_["hostname"], sys_["ip"], sys_["os"], sys_["location"])
            for sys_ in OFFICE_SYSTEMS
        ],
    )


def init_app(app):
    app.teardown_appcontext(close_db)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with app.app_context():
        init_db()
