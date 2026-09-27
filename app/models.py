# NOTE: user accounts now live in the `users` table (see app/database.py) with
# hashed passwords, rather than as a hardcoded dict here.

# Software licenses inventory. Expiry is expressed as an offset from the
# seeding date (see app/database.py) rather than a fixed calendar date, so a
# fresh install always shows one of each health state (healthy / expiring
# soon / expiring critical / expired) instead of drifting to "everything
# expired" a few weeks after the original hardcoded dates passed.
SOFTWARE_LICENSES = [
    {"id": "LIC-01", "software": "Enterprise Sentinel EDR", "key": "SNT-9921-X", "vendor": "CrowdStrike", "expiry_days_from_now": 2, "seats_total": 150, "seats_used": 142},
    {"id": "LIC-02", "software": "VMware vSphere Enterprise", "key": "VMW-4412-Z", "vendor": "Broadcom", "expiry_days_from_now": 20, "seats_total": 32, "seats_used": 28},
    {"id": "LIC-03", "software": "Red Hat OpenShift Cluster", "key": "RHT-1029-A", "vendor": "Red Hat", "expiry_days_from_now": 240, "seats_total": 10, "seats_used": 10},
    {"id": "LIC-04", "software": "Cisco AnyConnect VPN", "key": "CSCO-8830-B", "vendor": "Cisco", "expiry_days_from_now": -6, "seats_total": 500, "seats_used": 489},
]

# Seed rows only — real status (online/offline, last-seen) is no longer
# tracked here. It's computed live by app.services.system_service against
# whatever hosts are actually registered in the `monitored_systems` table,
# so this list just bootstraps the demo on first run. These are the original
# prototype's office IPs; swap them for real hosts via the admin dashboard
# ("Register System to Monitor") once deployed on an actual network.
OFFICE_SYSTEMS = [
    {"hostname": "IT-SRV-CORE01", "ip": "127.0.0.1", "os": "Ubuntu Server", "location": "Virtual-Rack-1"},
    {"hostname": "IT-SRV-BACKUP", "ip": "127.0.0.2", "os": "Debian Server", "location": "Virtual-Rack-1"},
    {"hostname": "IT-WS-DEV01", "ip": "127.0.0.3", "os": "Windows 11 Pro", "location": "IT Bay Desk 1"},
    {"hostname": "IT-WS-DEV02", "ip": "127.0.0.4", "os": "macOS Sequoia", "location": "IT Bay Desk 2"},
    {"hostname": "IT-GATEWAY-FW", "ip": "127.0.0.5", "os": "pfSense Firewall", "location": "Edge Gateway"},
    {"hostname": "IT-PRINT-MGMT", "ip": "127.0.0.6", "os": "Embedded Linux", "location": "Utility Room"}
]

