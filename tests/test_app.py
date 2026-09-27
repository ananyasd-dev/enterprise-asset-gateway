import os
import tempfile

import pytest
from uuid import uuid4
from app import create_app

@pytest.fixture
def client():
    # Isolate each test run from the real dev/demo database instead of
    # sharing instance/hal_asset_control.db.
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_PATH"] = db_path
    try:
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
    finally:
        os.environ.pop("DATABASE_PATH", None)
        os.remove(db_path)

def test_admin_flow(client):
    login_res = client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    assert login_res.status_code == 200
    assert login_res.get_json()["user"]["role"] == "ADMIN"

    overview_res = client.get("/api/admin/overview")
    assert overview_res.status_code == 200
    data = overview_res.get_json()
    assert "licenses" in data
    assert "systems" in data

def test_login_rejects_wrong_password(client):
    res = client.post("/api/login", json={"employee_id": "EMP-001", "password": "wrong-password"})
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_login_rejects_unknown_employee_id(client):
    res = client.post("/api/login", json={"employee_id": "EMP-999", "password": "anything"})
    assert res.status_code == 401


def test_login_rejects_missing_fields(client):
    res = client.post("/api/login", json={"employee_id": "EMP-001"})
    assert res.status_code == 400


def test_login_handles_non_json_body_gracefully(client):
    # No JSON content-type at all — must not blow up with an unhandled 400
    # HTML error page; should degrade to the same clean JSON error path.
    res = client.post("/api/login", data="not-json", content_type="text/plain")
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_employee_restriction(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    forbidden_res = client.get("/api/admin/overview")
    assert forbidden_res.status_code == 403

def test_employee_workstation_status_requires_login(client):
    anonymous_res = client.get("/api/employee/workstation-status")
    assert anonymous_res.status_code == 401

    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    status_res = client.get("/api/employee/workstation-status")
    assert status_res.status_code == 200
    assert status_res.get_json()["status"] == "Operational"

def test_logout_clears_session(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    logout_res = client.post("/api/logout")
    assert logout_res.status_code == 200
    assert client.get("/api/me").status_code == 401


def test_asset_inventory_and_registration(client):
    assert client.get("/api/assets").status_code == 401
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})

    suffix = uuid4().hex[:8].upper()
    payload = {
        "asset_id": f"HAL-PC-{suffix}",
        "hostname": f"SERVER-{suffix}",
        "serial_number": f"SN-{suffix}",
        "department": "Avionics",
        "location": "LAB-01",
    }
    created = client.post("/api/assets", json=payload)
    assert created.status_code == 201
    assert created.get_json()["asset"]["asset_id"] == payload["asset_id"]

    inventory = client.get("/api/assets", query_string={"search": suffix})
    assert inventory.status_code == 200
    assert inventory.get_json()["total"] == 1


def test_employee_cannot_register_asset(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    response = client.post("/api/assets", json={})
    assert response.status_code == 403


def test_asset_update_and_delete(client):
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    suffix = uuid4().hex[:8].upper()
    payload = {
        "asset_id": f"HAL-PC-{suffix}",
        "hostname": f"SERVER-{suffix}",
        "serial_number": f"SN-{suffix}",
        "department": "Avionics",
        "location": "LAB-01",
    }
    created = client.post("/api/assets", json=payload)
    assert created.status_code == 201

    update_payload = {**payload, "location": "LAB-02", "status": "In Repair"}
    updated = client.put(f"/api/assets/{payload['asset_id']}", json=update_payload)
    assert updated.status_code == 200
    assert updated.get_json()["asset"]["status"] == "In Repair"
    assert updated.get_json()["asset"]["location"] == "LAB-02"

    bad_status = client.put(f"/api/assets/{payload['asset_id']}", json={**payload, "status": "Not A Real Status"})
    assert bad_status.status_code == 400

    assert client.delete(f"/api/assets/{payload['asset_id']}").status_code == 200
    assert client.delete(f"/api/assets/{payload['asset_id']}").status_code == 404


def test_asset_edit_and_delete_require_admin(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    assert client.put("/api/assets/HAL-PC-0001", json={}).status_code == 403
    assert client.delete("/api/assets/HAL-PC-0001").status_code == 403


def test_dashboard_uses_persisted_asset_metrics(client):
    assert client.get("/api/dashboard").status_code == 401
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    metrics = response.get_json()["assets"]
    assert {"total_assets", "active_assets", "departments", "locations"} <= metrics.keys()
    assert metrics["total_assets"] >= metrics["active_assets"]


def test_license_inventory_is_persistent_and_admin_managed(client):
    assert client.get("/api/licenses").status_code == 401
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    suffix = uuid4().hex[:8].upper()
    payload = {
        "id": f"LIC-{suffix}", "software": "Offline Test Suite", "license_key": "LOCAL-123",
        "vendor": "HAL", "expiry": "2027-12-31", "seats_total": 10, "seats_used": 3,
    }
    assert client.post("/api/licenses", json=payload).status_code == 201
    inventory = client.get("/api/licenses").get_json()
    assert any(item["id"] == payload["id"] for item in inventory["licenses"])
    payload.update({"seats_used": 4})
    assert client.put(f"/api/licenses/{payload['id']}", json=payload).status_code == 200


def test_employee_can_view_but_cannot_create_license(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    assert client.get("/api/licenses").status_code == 200
    assert client.post("/api/licenses", json={}).status_code == 403


def test_license_delete_requires_admin_and_removes_it(client):
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    suffix = uuid4().hex[:8].upper()
    payload = {
        "id": f"LIC-{suffix}", "software": "Deletable Suite", "license_key": "DEL-123",
        "vendor": "HAL", "expiry": "2027-12-31", "seats_total": 5, "seats_used": 1,
    }
    assert client.post("/api/licenses", json=payload).status_code == 201

    client.post("/api/logout")
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    assert client.delete(f"/api/licenses/{payload['id']}").status_code == 403

    client.post("/api/logout")
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    assert client.delete(f"/api/licenses/{payload['id']}").status_code == 200
    assert client.delete(f"/api/licenses/{payload['id']}").status_code == 404


def test_admin_can_register_and_remove_monitored_system(client):
    client.post("/api/login", json={"employee_id": "EMP-001", "password": "admin123"})
    suffix = uuid4().hex[:8].upper()
    payload = {"hostname": f"TEST-HOST-{suffix}", "ip_address": "192.0.2.123"}

    created = client.post("/api/admin/systems", json=payload)
    assert created.status_code == 201
    assert created.get_json()["system"]["hostname"] == payload["hostname"]

    overview = client.get("/api/admin/overview").get_json()
    hostnames = [s["hostname"] for s in overview["systems"]["systems"]]
    assert payload["hostname"] in hostnames

    assert client.delete(f"/api/admin/systems/{payload['hostname']}").status_code == 200
    assert client.delete(f"/api/admin/systems/{payload['hostname']}").status_code == 404


def test_registering_system_requires_admin(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    response = client.post("/api/admin/systems", json={"hostname": "X", "ip_address": "10.0.0.9"})
    assert response.status_code == 403


def test_employee_workstation_status_reflects_monitored_systems(client):
    client.post("/api/login", json={"employee_id": "EMP-002", "password": "employee123"})
    response = client.get("/api/employee/workstation-status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] in ("Operational", "Degraded")
    assert isinstance(data["systems_available"], int)
