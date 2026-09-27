async function submitLogin(e) {
    e.preventDefault();
    const employee_id = document.getElementById("employeeIdInput").value.trim().toUpperCase();
    const password = document.getElementById("passwordInput").value;
    const alertBox = document.getElementById("loginAlert");

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ employee_id, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            window.location.reload();
        } else {
            alertBox.style.display = "block";
            alertBox.innerText = data.message || "Login authentication failed.";
        }
    } catch {
        alertBox.style.display = "block";
        alertBox.innerText = "Network communication error.";
    }
}

async function logout() {
    await fetch("/api/logout", { method: "POST" });
    window.location.reload();
}

async function fetchAdminData() {
    try {
        const res = await fetch("/api/admin/overview");
        if (!res.ok) return;
        const data = await res.json();

        // Metrics
        document.getElementById("m-sys-online").innerText = data.systems.online;
        document.getElementById("m-sys-total").innerText = `${data.systems.total} Total Configured (${data.systems.uptime_percentage}% Uptime)`;
        document.getElementById("m-sys-offline").innerText = data.systems.offline;
        document.getElementById("m-lic-threats").innerText = data.licenses.expiring_soon;
        document.getElementById("m-lic-expired").innerText = data.licenses.expired;

        // Software Licenses
        window._lastLicenses = data.licenses.licenses;
        const licBody = document.getElementById("licenseTableBody");
        licBody.innerHTML = data.licenses.licenses.map(lic => `
            <tr>
                <td><strong>${escapeHtml(lic.software)}</strong></td>
                <td>${escapeHtml(lic.vendor)}</td>
                <td><span class="code-badge">${escapeHtml(lic.key)}</span></td>
                <td>${escapeHtml(lic.expiry)}</td>
                <td>
                    <strong class="text-${lic.badge}">
                        ${lic.days_left < 0 ? `${Math.abs(lic.days_left)} days ago` : `${lic.days_left} days`}
                    </strong>
                </td>
                <td>${lic.seats_used} / ${lic.seats_total}</td>
                <td><span class="badge badge-${lic.badge}">${escapeHtml(lic.status)}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editLicense('${lic.id}')">Edit</button>
                    <button class="btn btn-sm btn-logout" onclick="removeLicense('${lic.id}')">Delete</button>
                </td>
            </tr>
        `).join('');

        // Office Systems (live ping + TCP-fallback status against admin-registered hosts)
        const sysBody = document.getElementById("systemTableBody");
        sysBody.innerHTML = data.systems.systems.map(sys => `
            <tr>
                <td><strong>${escapeHtml(sys.hostname)}</strong></td>
                <td><span class="code-badge">${escapeHtml(sys.ip)}</span></td>
                <td>${escapeHtml(sys.os)}</td>
                <td>${escapeHtml(sys.location)}</td>
                <td>
                    <span class="status-indicator">
                        <span class="indicator-dot ${sys.is_online ? 'dot-online' : 'dot-offline'}"></span>
                        <span class="${sys.is_online ? 'text-success' : 'text-danger'}">${sys.is_online ? 'ONLINE' : 'OFFLINE'}</span>
                    </span>
                </td>
                <td class="text-muted">${escapeHtml(sys.last_ping)}</td>
                <td>
                    <button class="btn btn-sm btn-logout" onclick="removeSystem('${sys.hostname}')">Remove</button>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        console.error("Error refreshing dashboard:", err);
    }
}

function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = value ?? "";
    return node.innerHTML;
}

// --- License management (Add / Edit / Delete) ---

function editLicense(id) {
    const lic = (window._lastLicenses || []).find(l => l.id === id);
    if (!lic) return;
    const form = document.getElementById("licenseForm");
    form.id.value = lic.id;
    form.id.readOnly = true;
    form.software.value = lic.software;
    form.license_key.value = lic.key;
    form.vendor.value = lic.vendor;
    form.expiry.value = lic.expiry;
    form.seats_total.value = lic.seats_total;
    form.seats_used.value = lic.seats_used;
    document.getElementById("licenseFormTitle").innerText = `Edit License — ${lic.id}`;
    document.getElementById("licenseFormSubmit").innerText = "Save Changes";
    document.getElementById("licenseFormCancel").style.display = "inline-block";
    form.dataset.editing = "true";
    form.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetLicenseForm() {
    const form = document.getElementById("licenseForm");
    form.reset();
    form.id.readOnly = false;
    delete form.dataset.editing;
    document.getElementById("licenseFormTitle").innerText = "Add License";
    document.getElementById("licenseFormSubmit").innerText = "Add License";
    document.getElementById("licenseFormCancel").style.display = "none";
    document.getElementById("licenseFormMessage").textContent = "";
}

async function submitLicenseForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = document.getElementById("licenseFormMessage");
    const editing = form.dataset.editing === "true";
    const values = Object.fromEntries(new FormData(form).entries());
    message.className = "form-message";
    message.textContent = editing ? "Saving changes…" : "Adding license…";

    try {
        const response = await fetch(editing ? `/api/licenses/${encodeURIComponent(values.id)}` : "/api/licenses", {
            method: editing ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(values),
        });
        const data = await response.json();
        if (!response.ok) {
            const details = data.fields ? Object.values(data.fields).join(" ") : data.error;
            throw new Error(details || "License save failed.");
        }
        message.className = "form-message text-success";
        message.textContent = editing ? "License updated." : `${data.license.id} added.`;
        resetLicenseForm();
        fetchAdminData();
    } catch (error) {
        message.className = "form-message text-danger";
        message.textContent = error.message;
    }
}

async function removeLicense(id) {
    if (!confirm(`Delete license ${id}? This can't be undone.`)) return;
    const response = await fetch(`/api/licenses/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (response.ok) fetchAdminData();
}

// --- Monitored-system management (Register / Remove) ---

async function submitSystemForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = document.getElementById("systemFormMessage");
    const values = Object.fromEntries(new FormData(form).entries());
    message.className = "form-message";
    message.textContent = "Registering system…";

    try {
        const response = await fetch("/api/admin/systems", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(values),
        });
        const data = await response.json();
        if (!response.ok) {
            const details = data.fields ? Object.values(data.fields).join(" ") : data.error;
            throw new Error(details || "Registration failed.");
        }
        form.reset();
        message.className = "form-message text-success";
        message.textContent = `${data.system.hostname} registered for monitoring.`;
        fetchAdminData();
    } catch (error) {
        message.className = "form-message text-danger";
        message.textContent = error.message;
    }
}

async function removeSystem(hostname) {
    if (!confirm(`Stop monitoring ${hostname}?`)) return;
    const response = await fetch(`/api/admin/systems/${encodeURIComponent(hostname)}`, { method: "DELETE" });
    if (response.ok) fetchAdminData();
}

async function fetchDashboardData() {
    const total = document.getElementById("m-assets-total");
    if (!total) return;
    try {
        const res = await fetch("/api/dashboard");
        if (!res.ok) throw new Error("Unable to load dashboard data");
        const data = await res.json();
        total.innerText = data.assets.total_assets;
        document.getElementById("m-assets-scope").innerText =
            `${data.assets.active_assets} Active · ${data.assets.departments} Departments · ${data.assets.locations} Locations`;
    } catch {
        total.innerText = "--";
        document.getElementById("m-assets-scope").innerText = "Local asset database unavailable";
    }
}

async function fetchWorkstationStatus() {
    const status = document.getElementById("workstationStatus");
    const badge = document.getElementById("workstationBadge");
    const message = document.getElementById("workstationMessage");

    try {
        const res = await fetch("/api/employee/workstation-status");
        if (!res.ok) throw new Error("Unable to load workstation status");

        const data = await res.json();
        status.innerText = `Workstation Node: ${data.status}`;
        badge.innerText = data.status.toUpperCase();
        badge.className = `badge ${data.status === "Operational" ? "badge-success" : "badge-danger"}`;
        message.innerText = "Your employee access is active. Administrative configurations remain restricted.";
        document.getElementById("officeNetwork").innerText = data.office_network;
        document.getElementById("systemsAvailable").innerText = data.systems_available;
    } catch {
        status.innerText = "Workstation status unavailable";
        badge.innerText = "ERROR";
        badge.className = "badge badge-danger";
        message.innerText = "The office network heartbeat could not be retrieved.";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("licenseTableBody")) {
        fetchAdminData();
        fetchDashboardData();
        setInterval(fetchAdminData, 10000);
        setInterval(fetchDashboardData, 10000);
    }
    const licenseForm = document.getElementById("licenseForm");
    if (licenseForm) licenseForm.addEventListener("submit", submitLicenseForm);
    const systemForm = document.getElementById("systemForm");
    if (systemForm) systemForm.addEventListener("submit", submitSystemForm);
    if (document.getElementById("workstationStatus")) {
        fetchWorkstationStatus();
        setInterval(fetchWorkstationStatus, 10000);
    }
});
