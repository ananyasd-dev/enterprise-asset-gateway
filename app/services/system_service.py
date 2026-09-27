"""Live network-status checks for admin-registered hosts.

Unlike the original prototype (a hardcoded in-memory list tied to one
office's 10.0.x.x range), the host list is persisted in the database and
managed from the admin dashboard, so this works against whatever network the
app is actually deployed on.

Status is checked two ways, in order:
  1. ICMP ping (via the OS `ping` binary) — fast, but many networks and
     sandboxed/containerized environments block ICMP outright or don't ship
     a ping binary at all.
  2. A raw TCP connect attempt on a handful of commonly-open ports — this is
     what makes status checks useful on real-world networks/firewalls that
     drop ICMP but still serve on a normal service port.
A host counts as online if either check succeeds.
"""

import platform
import socket
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.database import get_db

REQUIRED_FIELDS = ("hostname", "ip_address")
OPTIONAL_FIELDS = ("os", "location")

# Ports to probe as a fallback when ICMP is blocked/unavailable.
_PROBE_PORTS = (80, 443, 22, 3389, 445)

# In-process only — remembers the last time each host was seen online so we
# can show "Lost at HH:MM:SS" instead of just "offline". Resets on restart;
# that's fine since it's cosmetic, not authoritative status.
_LAST_SEEN_ONLINE = {}


def _ping_host(ip_or_host: str, timeout: int = 1) -> bool:
    system = platform.system().lower()
    param = "-n" if system == "windows" else "-c"
    timeout_flag = "-w" if system == "windows" else "-W"
    timeout_val = str(timeout * 1000) if system == "windows" else str(timeout)
    cmd = ["ping", param, "1", timeout_flag, timeout_val, ip_or_host]

    try:
        res = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1
        )
        if res.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    for port in _PROBE_PORTS:
        try:
            with socket.create_connection((ip_or_host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def _describe_status(hostname, is_online):
    if is_online:
        _LAST_SEEN_ONLINE[hostname] = "Just now"
        return "Just now"
    previous = _LAST_SEEN_ONLINE.get(hostname)
    if previous and previous != "Never went online yet":
        label = f"Lost at {datetime.now().strftime('%H:%M:%S')}"
        _LAST_SEEN_ONLINE[hostname] = label
        return label
    return _LAST_SEEN_ONLINE.setdefault(hostname, "Never went online yet")


def list_systems():
    db = get_db()
    rows = db.execute("SELECT * FROM monitored_systems ORDER BY hostname COLLATE NOCASE").fetchall()
    return [dict(row) for row in rows]


def get_system_metrics():
    """Ping every registered host (in parallel) and return live counters."""
    rows = list_systems()

    if rows:
        with ThreadPoolExecutor(max_workers=min(16, len(rows))) as pool:
            reachable = list(pool.map(lambda r: _ping_host(r["ip_address"]), rows))
    else:
        reachable = []

    systems = []
    online_count = 0
    for row, is_online in zip(rows, reachable):
        if is_online:
            online_count += 1
        systems.append({
            "hostname": row["hostname"],
            "ip": row["ip_address"],
            "os": row["os"],
            "location": row["location"],
            "is_online": is_online,
            "last_ping": _describe_status(row["hostname"], is_online),
        })

    total = len(systems)
    offline_count = total - online_count
    uptime = round((online_count / total) * 100, 1) if total else 0

    return {
        "systems": systems,
        "total": total,
        "online": online_count,
        "offline": offline_count,
        "uptime_percentage": uptime,
    }


def _normalise_system(data):
    if not isinstance(data, dict):
        return None, {"request": "A JSON object is required."}

    values = {f: str(data.get(f, "")).strip() for f in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS)}
    errors = {f: "This field is required." for f in REQUIRED_FIELDS if not values[f]}
    if errors:
        return None, errors

    values["hostname"] = values["hostname"].upper()
    values["os"] = values["os"] or "Unknown"
    values["location"] = values["location"] or "Unspecified"
    return values, None


def create_system(data):
    system, errors = _normalise_system(data)
    if errors:
        return None, errors

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO monitored_systems (hostname, ip_address, os, location) VALUES (?, ?, ?, ?)",
            (system["hostname"], system["ip_address"], system["os"], system["location"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None, {"hostname": "A system with this hostname is already being monitored."}

    row = db.execute("SELECT * FROM monitored_systems WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row), None


def delete_system(hostname):
    hostname = hostname.strip().upper()
    db = get_db()
    result = db.execute("DELETE FROM monitored_systems WHERE hostname = ?", (hostname,))
    db.commit()
    _LAST_SEEN_ONLINE.pop(hostname, None)
    return result.rowcount > 0
