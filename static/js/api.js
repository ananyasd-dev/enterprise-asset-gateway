function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = value ?? "";
    return node.innerHTML;
}

const ASSET_STATUS_BADGE = { "Active": "success", "In Repair": "warning", "Retired": "danger" };

let _lastAssets = [];

async function loadAssets(search = "") {
    const body = document.getElementById("assetTableBody");
    if (!body) return;
    const colspan = typeof IS_ADMIN !== "undefined" && IS_ADMIN ? 8 : 7;
    try {
        const query = search ? `?search=${encodeURIComponent(search)}` : "";
        const response = await fetch(`/api/assets${query}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Unable to load assets.");
        _lastAssets = data.assets;
        const badgeCol = typeof IS_ADMIN !== "undefined" && IS_ADMIN
            ? asset => `<td>
                <button class="btn btn-sm btn-primary" onclick="editAsset('${asset.asset_id}')">Edit</button>
                <button class="btn btn-sm btn-logout" onclick="removeAsset('${asset.asset_id}')">Delete</button>
              </td>`
            : () => "";
        body.innerHTML = data.assets.length
            ? data.assets.map(asset => `<tr>
                <td><strong>${escapeHtml(asset.asset_id)}</strong></td>
                <td>${escapeHtml(asset.hostname)}</td>
                <td><span class="code-badge">${escapeHtml(asset.serial_number)}</span></td>
                <td>${escapeHtml(asset.department)}</td>
                <td>${escapeHtml(asset.location)}</td>
                <td>${escapeHtml(asset.asset_type)}</td>
                <td><span class="badge badge-${ASSET_STATUS_BADGE[asset.status] || 'emp'}">${escapeHtml(asset.status)}</span></td>
                ${badgeCol(asset)}
            </tr>`).join("")
            : `<tr><td colspan="${colspan}" class="text-center">No assets found.</td></tr>`;
    } catch (error) {
        body.innerHTML = `<tr><td colspan="${colspan}" class="text-center text-danger">${escapeHtml(error.message)}</td></tr>`;
    }
}

function editAsset(assetId) {
    const asset = _lastAssets.find(a => a.asset_id === assetId);
    const form = document.getElementById("assetForm");
    if (!asset || !form) return;
    form.asset_id.value = asset.asset_id;
    form.asset_id.readOnly = true;
    form.hostname.value = asset.hostname;
    form.serial_number.value = asset.serial_number;
    form.department.value = asset.department;
    form.location.value = asset.location;
    form.asset_type.value = asset.asset_type;
    form.status.value = asset.status;
    document.getElementById("assetFormTitle").innerText = `Edit Asset — ${asset.asset_id}`;
    document.getElementById("assetFormSubmit").innerText = "Save Changes";
    document.getElementById("assetFormCancel").style.display = "inline-block";
    form.dataset.editing = "true";
    form.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetAssetForm() {
    const form = document.getElementById("assetForm");
    if (!form) return;
    form.reset();
    form.asset_id.readOnly = false;
    delete form.dataset.editing;
    document.getElementById("assetFormTitle").innerText = "Register Asset";
    document.getElementById("assetFormSubmit").innerText = "Register Asset";
    document.getElementById("assetFormCancel").style.display = "none";
    document.getElementById("assetFormMessage").textContent = "";
}

async function registerAsset(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = document.getElementById("assetFormMessage");
    const editing = form.dataset.editing === "true";
    const values = Object.fromEntries(new FormData(form).entries());
    message.className = "form-message";
    message.textContent = editing ? "Saving changes…" : "Registering asset…";

    try {
        const response = await fetch(editing ? `/api/assets/${encodeURIComponent(values.asset_id)}` : "/api/assets", {
            method: editing ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(values),
        });
        const data = await response.json();
        if (!response.ok) {
            const details = data.fields ? Object.values(data.fields).join(" ") : data.error;
            throw new Error(details || "Asset save failed.");
        }
        message.className = "form-message text-success";
        message.textContent = editing ? "Asset updated." : `${data.asset.asset_id} registered successfully.`;
        resetAssetForm();
        loadAssets();
    } catch (error) {
        message.className = "form-message text-danger";
        message.textContent = error.message;
    }
}

async function removeAsset(assetId) {
    if (!confirm(`Delete asset ${assetId}? This can't be undone.`)) return;
    const response = await fetch(`/api/assets/${encodeURIComponent(assetId)}`, { method: "DELETE" });
    if (response.ok) loadAssets();
}

document.addEventListener("DOMContentLoaded", () => {
    loadAssets();
    const form = document.getElementById("assetForm");
    if (form) form.addEventListener("submit", registerAsset);
    const search = document.getElementById("assetSearch");
    if (search) search.addEventListener("input", event => loadAssets(event.target.value));
});
