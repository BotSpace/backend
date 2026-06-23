"""Tests for dynamic options endpoint and loader registry.

Covers:
- Each of the 5 Google loaders (mocked requests)
- Endpoint: 200 with valid owner credential
- Endpoint: 404 when credential belongs to another user
- Module fallback: options.load RPC proxied to module endpoint
- Module fallback: graceful error when module not found / RPC fails
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential
from core.apps.credentials.services import crypto

OPTIONS_URL = "/api/v1/credentials/options/{resource}/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_oauth_credential(owner, type_key="google_sheets", name="My Sheets"):
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    data = {
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token",
        "expires_at": expires_at,
        "scope": "openid email https://www.googleapis.com/auth/spreadsheets",
        "token_type": "Bearer",
        "account_email": "user@gmail.com",
    }
    return Credential.objects.create(
        owner=owner,
        type_key=type_key,
        name=name,
        data_encrypted=crypto.encrypt(data),
    )


@pytest.fixture
def auth_client(db):
    project = ProjectModel._create_fake()
    client = APIClient()
    client.force_authenticate(project.owner)
    return client, project.owner


# ---------------------------------------------------------------------------
# Unit tests: loader functions (mocked requests)
# ---------------------------------------------------------------------------

def test_load_google_spreadsheets_parses_response():
    from core.apps.credentials.services.options import load_google_spreadsheets

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "files": [
            {"id": "sheet_id_1", "name": "Budget 2024"},
            {"id": "sheet_id_2", "name": "Sales Q1"},
        ]
    }

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        result = load_google_spreadsheets("token_abc", {})

    assert result == [
        {"value": "sheet_id_1", "label": "Budget 2024"},
        {"value": "sheet_id_2", "label": "Sales Q1"},
    ]


def test_load_google_spreadsheets_api_error_raises():
    from core.apps.credentials.services.options import load_google_spreadsheets

    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden"

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Drive API error 403"):
            load_google_spreadsheets("bad_token", {})


def test_load_google_sheet_tabs_parses_response():
    from core.apps.credentials.services.options import load_google_sheet_tabs

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "sheets": [
            {"properties": {"title": "Sheet1"}},
            {"properties": {"title": "Data"}},
        ]
    }

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        result = load_google_sheet_tabs("token_abc", {"spreadsheet_id": "spr_123"})

    assert result == [
        {"value": "Sheet1", "label": "Sheet1"},
        {"value": "Data", "label": "Data"},
    ]


def test_load_google_sheet_tabs_missing_param_raises():
    from core.apps.credentials.services.options import load_google_sheet_tabs

    with pytest.raises(ValueError, match="spreadsheet_id"):
        load_google_sheet_tabs("tok", {})


def test_load_google_sheet_tabs_api_error_raises():
    from core.apps.credentials.services.options import load_google_sheet_tabs

    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    mock_resp.text = "Not found"

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Sheets API error 404"):
            load_google_sheet_tabs("tok", {"spreadsheet_id": "nonexistent"})


def test_load_google_sheet_columns_parses_response():
    from core.apps.credentials.services.options import load_google_sheet_columns

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "values": [["Name", "Email", "Phone", ""]]
    }

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        result = load_google_sheet_columns(
            "token_abc",
            {"spreadsheet_id": "spr_123", "sheet": "Sheet1"},
        )

    # Blank trailing header skipped
    assert result == [
        {"value": "Name", "label": "Name"},
        {"value": "Email", "label": "Email"},
        {"value": "Phone", "label": "Phone"},
    ]


def test_load_google_sheet_columns_empty_sheet():
    from core.apps.credentials.services.options import load_google_sheet_columns

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {}  # no "values" key

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        result = load_google_sheet_columns("tok", {"spreadsheet_id": "s", "sheet": "Tab"})

    assert result == []


def test_load_google_sheet_columns_missing_params_raise():
    from core.apps.credentials.services.options import load_google_sheet_columns

    with pytest.raises(ValueError, match="spreadsheet_id"):
        load_google_sheet_columns("tok", {})

    with pytest.raises(ValueError, match="sheet"):
        load_google_sheet_columns("tok", {"spreadsheet_id": "s"})


# ---------------------------------------------------------------------------
# Endpoint integration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_options_endpoint_200_google_spreadsheets(auth_client):
    client, owner = auth_client
    cred = _make_oauth_credential(owner)

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"files": [{"id": "aaa", "name": "My Sheet"}]}

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        resp = client.post(
            OPTIONS_URL.format(resource="google_spreadsheets"),
            {"credential_id": cred.id, "params": {}},
            format="json",
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "options" in data
    assert data["options"] == [{"value": "aaa", "label": "My Sheet"}]


@pytest.mark.django_db
def test_options_endpoint_200_google_sheet_tabs(auth_client):
    client, owner = auth_client
    cred = _make_oauth_credential(owner)

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "sheets": [{"properties": {"title": "Tab1"}}, {"properties": {"title": "Tab2"}}]
    }

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        resp = client.post(
            OPTIONS_URL.format(resource="google_sheet_tabs"),
            {"credential_id": cred.id, "params": {"spreadsheet_id": "spr_x"}},
            format="json",
        )

    assert resp.status_code == 200
    assert resp.json()["options"] == [
        {"value": "Tab1", "label": "Tab1"},
        {"value": "Tab2", "label": "Tab2"},
    ]


@pytest.mark.django_db
def test_options_endpoint_200_google_sheet_columns(auth_client):
    client, owner = auth_client
    cred = _make_oauth_credential(owner)

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"values": [["Col A", "Col B"]]}

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        resp = client.post(
            OPTIONS_URL.format(resource="google_sheet_columns"),
            {
                "credential_id": cred.id,
                "params": {"spreadsheet_id": "spr_x", "sheet": "Sheet1"},
            },
            format="json",
        )

    assert resp.status_code == 200
    assert resp.json()["options"] == [
        {"value": "Col A", "label": "Col A"},
        {"value": "Col B", "label": "Col B"},
    ]


@pytest.mark.django_db
def test_options_endpoint_404_wrong_owner(db):
    """User A cannot fetch options using User B's credential."""
    project_a = ProjectModel._create_fake()
    project_b = ProjectModel._create_fake()
    cred_b = _make_oauth_credential(project_b.owner, name="B Sheets")

    client_a = APIClient()
    client_a.force_authenticate(project_a.owner)

    resp = client_a.post(
        OPTIONS_URL.format(resource="google_spreadsheets"),
        {"credential_id": cred_b.id, "params": {}},
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_options_endpoint_unknown_resource_no_module_returns_200_error(auth_client):
    """Unknown resource with no matching module → 200 + options=[] + error (graceful fallback)."""
    client, owner = auth_client
    cred = _make_oauth_credential(owner)
    resp = client.post(
        OPTIONS_URL.format(resource="nonexistent_resource"),
        {"credential_id": cred.id, "params": {}},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == []
    assert "error" in data


@pytest.mark.django_db
def test_options_endpoint_401_unauthenticated(db):
    project = ProjectModel._create_fake()
    cred = _make_oauth_credential(project.owner)
    client = APIClient()
    resp = client.post(
        OPTIONS_URL.format(resource="google_spreadsheets"),
        {"credential_id": cred.id, "params": {}},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_options_endpoint_returns_error_on_api_failure(auth_client):
    """Google API error should return 200 with options=[] and error key (no 500)."""
    client, owner = auth_client
    cred = _make_oauth_credential(owner)

    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("core.apps.credentials.services.options.requests.get", return_value=mock_resp):
        resp = client.post(
            OPTIONS_URL.format(resource="google_spreadsheets"),
            {"credential_id": cred.id, "params": {}},
            format="json",
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == []
    assert "error" in data
    assert "401" in data["error"]


# ---------------------------------------------------------------------------
# Module fallback tests
# ---------------------------------------------------------------------------

def _make_module_credential(owner, type_key="openrouter.apikey", name="OpenRouter Key"):
    """Non-oauth credential with a namespaced type_key (module-style)."""
    data = {"api_key": "sk-or-test-123"}
    return Credential.objects.create(
        owner=owner,
        type_key=type_key,
        name=name,
        data_encrypted=crypto.encrypt(data),
    )


def _mock_module(slug: str, auth_token: str = ""):
    """Helper: create a mock module object."""
    m = MagicMock()
    m.slug = slug
    m.auth_token = auth_token
    m.manifest_cache = {}
    return m


_GET_MOD_EP = "core.apps.credentials.services.options._get_module_and_endpoint"


@pytest.mark.django_db
def test_options_module_fallback_success(auth_client):
    """Module fallback: RPC returns options list → view returns 200 with options."""
    client, owner = auth_client
    cred = _make_module_credential(owner)

    mock_rpc_resp = MagicMock()
    mock_rpc_resp.ok = True
    mock_rpc_resp.json.return_value = {
        "jsonrpc": "2.0",
        "result": {
            "options": [
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "claude-3", "label": "Claude 3"},
            ]
        },
        "id": 1,
    }

    with patch("core.apps.credentials.services.options.requests.post", return_value=mock_rpc_resp):
        with patch(_GET_MOD_EP, return_value=(_mock_module("openrouter", "module-secret"), "http://module-openrouter:8100/rpc")):
            resp = client.post(
                OPTIONS_URL.format(resource="models"),
                {"credential_id": cred.id, "params": {"search": "gpt"}},
                format="json",
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == [
        {"value": "gpt-4o", "label": "GPT-4o"},
        {"value": "claude-3", "label": "Claude 3"},
    ]
    assert "error" not in data


@pytest.mark.django_db
def test_options_module_fallback_no_module_returns_200_error(auth_client):
    """Module fallback: no active module → 200 with options=[] and error message."""
    client, owner = auth_client
    cred = _make_module_credential(owner)

    with patch(_GET_MOD_EP, side_effect=RuntimeError("No active module found for slug='openrouter'")):
        resp = client.post(
            OPTIONS_URL.format(resource="models"),
            {"credential_id": cred.id, "params": {}},
            format="json",
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == []
    assert "error" in data
    assert "openrouter" in data["error"]


@pytest.mark.django_db
def test_options_module_fallback_rpc_error_returns_200_error(auth_client):
    """Module fallback: RPC returns JSON-RPC error → 200 with options=[] + error."""
    client, owner = auth_client
    cred = _make_module_credential(owner)

    mock_rpc_resp = MagicMock()
    mock_rpc_resp.ok = True
    mock_rpc_resp.json.return_value = {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": "Method not found"},
        "id": 1,
    }

    with patch("core.apps.credentials.services.options.requests.post", return_value=mock_rpc_resp):
        with patch(_GET_MOD_EP, return_value=(_mock_module("openrouter"), "http://module-openrouter:8100/rpc")):
            resp = client.post(
                OPTIONS_URL.format(resource="models"),
                {"credential_id": cred.id, "params": {}},
                format="json",
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == []
    assert "error" in data
    assert "Method not found" in data["error"]


@pytest.mark.django_db
def test_options_module_fallback_rpc_http_error_returns_200_error(auth_client):
    """Module fallback: RPC HTTP error → 200 with options=[] + error."""
    client, owner = auth_client
    cred = _make_module_credential(owner)

    mock_rpc_resp = MagicMock()
    mock_rpc_resp.ok = False
    mock_rpc_resp.status_code = 503
    mock_rpc_resp.text = "Service Unavailable"

    with patch("core.apps.credentials.services.options.requests.post", return_value=mock_rpc_resp):
        with patch(_GET_MOD_EP, return_value=(_mock_module("openrouter"), "http://module-openrouter:8100/rpc")):
            resp = client.post(
                OPTIONS_URL.format(resource="models"),
                {"credential_id": cred.id, "params": {}},
                format="json",
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["options"] == []
    assert "error" in data
    assert "503" in data["error"]


@pytest.mark.django_db
def test_options_module_fallback_rpc_sends_correct_payload(auth_client):
    """Verify the RPC payload structure sent to the module endpoint."""
    client, owner = auth_client
    cred = _make_module_credential(owner, type_key="mymod.oauth")

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"jsonrpc": "2.0", "result": {"options": []}, "id": 1}
        return mock_resp

    with patch("core.apps.credentials.services.options.requests.post", side_effect=fake_post):
        with patch(_GET_MOD_EP, return_value=(_mock_module("mymod", "tok123"), "http://module-mymod:8100/rpc")):
            client.post(
                OPTIONS_URL.format(resource="connections"),
                {"credential_id": cred.id, "params": {"region": "us-east"}},
                format="json",
            )

    assert captured["url"] == "http://module-mymod:8100/rpc"
    assert captured["headers"] == {"Authorization": "Bearer tok123"}
    payload = captured["json"]
    assert payload["method"] == "options.load"
    rpc_params = payload["params"]
    assert rpc_params["resource"] == "connections"
    assert rpc_params["params"] == {"region": "us-east"}
    cred_payload = rpc_params["credentials"]["credential"]
    assert cred_payload["type_key"] == "mymod.oauth"
    assert cred_payload["data"]["api_key"] == "sk-or-test-123"


def test_slug_from_type_key():
    """Unit test for slug extraction helper."""
    from core.apps.credentials.services.options import _slug_from_type_key

    assert _slug_from_type_key("openrouter.apikey") == "openrouter"
    assert _slug_from_type_key("mymod.oauth2") == "mymod"
    assert _slug_from_type_key("no_dot") == ""
    assert _slug_from_type_key("a.b.c") == "a"
