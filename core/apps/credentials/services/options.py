"""Dynamic options loader registry.

Each loader has signature: (token: str, params: dict) -> list[{"value": ..., "label": ...}]
Add a new dynamic source by appending one entry to OPTION_LOADERS.
"""
from __future__ import annotations

import requests

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
