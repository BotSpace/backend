"""Dynamic options loader registry.

Each loader has signature: (token: str, params: dict) -> list[{"value": ..., "label": ...}]
Add a new dynamic source by appending one entry to OPTION_LOADERS.

Module fallback: when resource is not in OPTION_LOADERS, load_module_options() is called.
It resolves the credential's type_key prefix to a ModuleModel, then calls options.load RPC.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"

_TIMEOUT = 10


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def load_google_spreadsheets(token: str, params: dict) -> list[dict]:
    """List all Google Spreadsheets accessible to the user (via Drive API)."""
    resp = requests.get(
        DRIVE_FILES_URL,
        headers=_auth_headers(token),
        params={
            "q": "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            "fields": "files(id,name)",
            "pageSize": 200,
        },
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Drive API error {resp.status_code}: {resp.text[:300]}")
    files = resp.json().get("files", [])
    return [{"value": f["id"], "label": f["name"]} for f in files]


def load_google_sheet_tabs(token: str, params: dict) -> list[dict]:
    """List sheet/tab names inside a spreadsheet."""
    spreadsheet_id = params.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ValueError("params.spreadsheet_id is required")
    resp = requests.get(
        f"{SHEETS_BASE_URL}/{spreadsheet_id}",
        headers=_auth_headers(token),
        params={"fields": "sheets.properties.title"},
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Sheets API error {resp.status_code}: {resp.text[:300]}")
    sheets = resp.json().get("sheets", [])
    titles = [s["properties"]["title"] for s in sheets if s.get("properties", {}).get("title")]
    return [{"value": t, "label": t} for t in titles]


def load_google_sheet_columns(token: str, params: dict) -> list[dict]:
    """Return first-row headers of a specific sheet tab as column options."""
    spreadsheet_id = params.get("spreadsheet_id")
    sheet = params.get("sheet")
    if not spreadsheet_id:
        raise ValueError("params.spreadsheet_id is required")
    if not sheet:
        raise ValueError("params.sheet is required")
    range_ref = f"{sheet}!1:1"
    resp = requests.get(
        f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{range_ref}",
        headers=_auth_headers(token),
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Sheets API error {resp.status_code}: {resp.text[:300]}")
    values = resp.json().get("values", [])
    if not values:
        return []
    headers = [h for h in values[0] if h and str(h).strip()]
    return [{"value": h, "label": h} for h in headers]


def load_google_drive_folders(token: str, params: dict) -> list[dict]:
    """List the user's Google Drive folders (optionally inside parent folder_id)."""
    q = "mimeType='application/vnd.google-apps.folder' and trashed=false"
    parent = params.get("folder_id")
    if parent:
        q += f" and '{parent}' in parents"
    resp = requests.get(
        DRIVE_FILES_URL,
        headers=_auth_headers(token),
        params={"q": q, "fields": "files(id,name)", "pageSize": 200, "orderBy": "name"},
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Drive API error {resp.status_code}: {resp.text[:300]}")
    files = resp.json().get("files", [])
    return [{"value": f["id"], "label": f["name"]} for f in files]


def load_google_drive_files(token: str, params: dict) -> list[dict]:
    """List the user's Google Drive files (non-folders; optionally inside folder_id)."""
    q = "mimeType!='application/vnd.google-apps.folder' and trashed=false"
    parent = params.get("folder_id")
    if parent:
        q += f" and '{parent}' in parents"
    resp = requests.get(
        DRIVE_FILES_URL,
        headers=_auth_headers(token),
        params={"q": q, "fields": "files(id,name)", "pageSize": 200, "orderBy": "name"},
        timeout=_TIMEOUT,
    )
    if not resp.ok:
        raise RuntimeError(f"Drive API error {resp.status_code}: {resp.text[:300]}")
    files = resp.json().get("files", [])
    return [{"value": f["id"], "label": f["name"]} for f in files]


OPTION_LOADERS: dict[str, callable] = {
    "google_spreadsheets": load_google_spreadsheets,
    "google_sheet_tabs": load_google_sheet_tabs,
    "google_sheet_columns": load_google_sheet_columns,
    "google_drive_folders": load_google_drive_folders,
    "google_drive_files": load_google_drive_files,
}

# ---------------------------------------------------------------------------
# Module fallback — options.load RPC
# ---------------------------------------------------------------------------

_MODULE_RPC_TIMEOUT = 10


def _slug_from_type_key(type_key: str) -> str:
    """Extract module slug from a namespaced type_key like 'openrouter.apikey' → 'openrouter'."""
    return type_key.split(".")[0] if "." in type_key else ""


def _get_module_and_endpoint(slug: str):
    """Return (module, endpoint) for the given slug, or raise RuntimeError."""
    # Late import to avoid circular dependency at module load time.
    from core.apps.api.models.module import ModuleModel  # noqa: PLC0415
    from core.apps.api.services.module_service import _shared_endpoint  # noqa: PLC0415

    module = ModuleModel.objects.filter(slug=slug, active=True).first()
    if module is None:
        raise RuntimeError(f"No active module found for slug={slug!r}")
    return module, _shared_endpoint(module)


def load_module_options(resource: str, cred_type_key: str, decrypted_data: dict, params: dict) -> list[dict]:
    """Call options.load RPC on the module that owns cred_type_key.

    Returns a list of {value, label} dicts.
    Raises RuntimeError on module-not-found or RPC errors (caller should catch and convert to error response).
    """
    slug = _slug_from_type_key(cred_type_key)
    if not slug:
        raise RuntimeError(f"Cannot determine module slug from type_key={cred_type_key!r}")

    try:
        module, endpoint = _get_module_and_endpoint(slug)
    except RuntimeError:
        raise RuntimeError(f"No active module found for slug={slug!r} (derived from type_key={cred_type_key!r})")

    # Credential payload sent to module: {type_key, mode, data}
    type_info = None
    try:
        from core.apps.credentials.registry import get_type
        type_info = get_type(cred_type_key) or {}
    except Exception:
        type_info = {}

    credential_payload = {
        "type_key": cred_type_key,
        "mode": type_info.get("mode", ""),
        "data": decrypted_data,
    }

    rpc_payload = {
        "jsonrpc": "2.0",
        "method": "options.load",
        "params": {
            "resource": resource,
            "params": params,
            "credentials": {"credential": credential_payload},
        },
        "id": 1,
    }

    headers = {}
    if module.auth_token:
        headers["Authorization"] = f"Bearer {module.auth_token}"

    try:
        resp = requests.post(endpoint, json=rpc_payload, headers=headers, timeout=_MODULE_RPC_TIMEOUT)
    except requests.Timeout:
        raise RuntimeError(f"Module {slug!r} options.load timed out after {_MODULE_RPC_TIMEOUT}s")
    except requests.RequestException as exc:
        raise RuntimeError(f"Module {slug!r} options.load network error: {exc}")

    if not resp.ok:
        raise RuntimeError(f"Module {slug!r} RPC error {resp.status_code}: {resp.text[:300]}")

    body = resp.json()
    if "error" in body:
        err = body["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(f"Module {slug!r} options.load returned error: {msg}")

    result = body.get("result", {})
    options = result.get("options", [])
    if not isinstance(options, list):
        raise RuntimeError(f"Module {slug!r} options.load returned non-list options: {options!r}")

    return options
