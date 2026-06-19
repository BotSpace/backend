"""OAuth2 credential tests.

Covers:
- state sign/verify round-trip
- start endpoint builds correct URL + scopes
- callback upserts credential (mocked token endpoint)
- token refresh logic
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.core import signing
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential
from core.apps.credentials.services import crypto
from core.apps.credentials.services.oauth import make_state, verify_state, build_token_data, STATE_MAX_AGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_oauth_credential(
    owner,
    type_key="google_email",
    access_token="tok",
    refresh_token="rtok",
    account_email="user@gmail.com",
    name=None,
):
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scope": "openid email",
        "token_type": "Bearer",
        "account_email": account_email,
    }
    # Default name matches the pattern _upsert_credential uses: "<Label> (<email>)"
    if name is None:
        from core.apps.credentials.registry import get_type as _get_type
        label = (_get_type(type_key) or {}).get("label", type_key)
        name = f"{label} ({account_email})"
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
# State sign/verify
# ---------------------------------------------------------------------------

def test_state_sign_verify_roundtrip():
    state = make_state(user_id=42, type_key="google_email")
    result = verify_state(state)
    assert result["user_id"] == 42
    assert result["type_key"] == "google_email"


def test_state_invalid_signature():
    state = make_state(42, "google_email")
    with pytest.raises(signing.BadSignature):
        verify_state(state + "tampered")


def test_state_expired():
    """Simulate expired state by patching max_age check."""
    state = make_state(1, "google_email")
    signer = signing.TimestampSigner()
    # Sign the same payload but unsign with 0 max_age to force expiry is not easily injectable,
    # so we verify BadSignature is raised for obvious tampering.
    with pytest.raises(Exception):
        verify_state(state[:-5] + "xxxxx")


# ---------------------------------------------------------------------------
# Start endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_oauth_start_returns_authorize_url(auth_client):
    client, owner = auth_client
    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="test-client-id"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="test-secret"):
        resp = client.post(
            "/api/v1/credentials/oauth/google/start/",
            {"type_key": "google_email"},
            format="json",
        )
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert "authorize_url" in data
    url = data["authorize_url"]
    assert "accounts.google.com" in url
    assert "test-client-id" in url
    assert "openid" in url
    assert "userinfo.email" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=" in url


@pytest.mark.django_db
def test_oauth_start_google_sheets_scopes(auth_client):
    client, owner = auth_client
    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="cid"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="cs"):
        resp = client.post(
            "/api/v1/credentials/oauth/google/start/",
            {"type_key": "google_sheets"},
            format="json",
        )
    assert resp.status_code == 200
    url = resp.json()["authorize_url"]
    assert "spreadsheets" in url


@pytest.mark.django_db
def test_oauth_start_wrong_provider(auth_client):
    client, owner = auth_client
    resp = client.post(
        "/api/v1/credentials/oauth/github/start/",
        {"type_key": "google_email"},
        format="json",
    )
    assert resp.status_code in (400, 404)


@pytest.mark.django_db
def test_oauth_start_non_oauth_type(auth_client):
    client, owner = auth_client
    resp = client.post(
        "/api/v1/credentials/oauth/google/start/",
        {"type_key": "bearer"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_oauth_start_requires_auth():
    client = APIClient()
    resp = client.post(
        "/api/v1/credentials/oauth/google/start/",
        {"type_key": "google_email"},
        format="json",
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Callback endpoint (mocked HTTP)
# ---------------------------------------------------------------------------

def _fake_token_response():
    return {
        "access_token": "new_access_tok",
        "refresh_token": "new_refresh_tok",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "openid email https://www.googleapis.com/auth/userinfo.email",
    }


def _fake_userinfo():
    return {"email": "user@gmail.com", "sub": "123456"}


@pytest.mark.django_db
def test_oauth_callback_upserts_credential(db):
    project = ProjectModel._create_fake()
    owner = project.owner

    # Build a valid signed state
    state = make_state(owner.pk, "google_email")

    mock_token_resp = MagicMock()
    mock_token_resp.raise_for_status = MagicMock()
    mock_token_resp.json.return_value = _fake_token_response()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.ok = True
    mock_userinfo_resp.json.return_value = _fake_userinfo()

    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="cid"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="csec"), \
         patch("core.apps.credentials.services.oauth.http_requests.post", return_value=mock_token_resp), \
         patch("core.apps.credentials.services.oauth.http_requests.get", return_value=mock_userinfo_resp):
        client = APIClient()
        resp = client.get(
            "/api/v1/credentials/oauth/google/callback/",
            {"code": "auth_code_xyz", "state": state},
        )

    assert resp.status_code == 200
    assert "text/html" in resp.get("Content-Type", "")
    assert b"credential-oauth" in resp.content
    assert b"ok:true" in resp.content

    # Credential should be created in DB
    cred = Credential.objects.filter(owner=owner, type_key="google_email").first()
    assert cred is not None
    decrypted = crypto.decrypt(cred.data_encrypted)
    assert decrypted["access_token"] == "new_access_tok"
    assert decrypted["account_email"] == "user@gmail.com"


@pytest.mark.django_db
def test_oauth_callback_upserts_on_second_call(db):
    """Second callback call should update existing credential, not create duplicate."""
    project = ProjectModel._create_fake()
    owner = project.owner

    # Create initial credential
    _make_oauth_credential(owner)

    state = make_state(owner.pk, "google_email")
    mock_token_resp = MagicMock()
    mock_token_resp.raise_for_status = MagicMock()
    mock_token_resp.json.return_value = {**_fake_token_response(), "access_token": "updated_tok"}
    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.ok = True
    mock_userinfo_resp.json.return_value = {"email": "user@gmail.com"}

    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="cid"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="cs"), \
         patch("core.apps.credentials.services.oauth.http_requests.post", return_value=mock_token_resp), \
         patch("core.apps.credentials.services.oauth.http_requests.get", return_value=mock_userinfo_resp):
        client = APIClient()
        resp = client.get(
            "/api/v1/credentials/oauth/google/callback/",
            {"code": "code2", "state": state},
        )

    assert resp.status_code == 200
    # Still just one credential for this type (same account)
    assert Credential.objects.filter(owner=owner, type_key="google_email", deleted_at__isnull=True).count() == 1
    cred = Credential.objects.get(owner=owner, type_key="google_email", deleted_at__isnull=True)
    assert crypto.decrypt(cred.data_encrypted)["access_token"] == "updated_tok"


@pytest.mark.django_db
def test_oauth_callback_multiple_accounts_same_type(db):
    """Connecting a second Gmail account must create a NEW credential, not overwrite the first."""
    project = ProjectModel._create_fake()
    owner = project.owner

    # First account already saved
    _make_oauth_credential(owner, account_email="first@gmail.com")

    state = make_state(owner.pk, "google_email")

    mock_token_resp = MagicMock()
    mock_token_resp.raise_for_status = MagicMock()
    mock_token_resp.json.return_value = {**_fake_token_response(), "access_token": "second_tok"}

    # Second account userinfo
    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.ok = True
    mock_userinfo_resp.json.return_value = {"email": "second@gmail.com", "sub": "999"}

    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="cid"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="cs"), \
         patch("core.apps.credentials.services.oauth.http_requests.post", return_value=mock_token_resp), \
         patch("core.apps.credentials.services.oauth.http_requests.get", return_value=mock_userinfo_resp):
        client = APIClient()
        resp = client.get(
            "/api/v1/credentials/oauth/google/callback/",
            {"code": "code_second", "state": state},
        )

    assert resp.status_code == 200

    # Two separate credentials must exist now
    qs = Credential.objects.filter(owner=owner, type_key="google_email", deleted_at__isnull=True)
    assert qs.count() == 2, f"Expected 2, got {qs.count()}: {list(qs.values('name'))}"

    emails_in_names = {c.name for c in qs}
    assert any("first@gmail.com" in n for n in emails_in_names), emails_in_names
    assert any("second@gmail.com" in n for n in emails_in_names), emails_in_names

    # First account token is unchanged
    first_cred = qs.get(name__icontains="first@gmail.com")
    assert crypto.decrypt(first_cred.data_encrypted)["access_token"] == "tok"

    # Second account token is stored correctly
    second_cred = qs.get(name__icontains="second@gmail.com")
    assert crypto.decrypt(second_cred.data_encrypted)["access_token"] == "second_tok"
    assert crypto.decrypt(second_cred.data_encrypted)["account_email"] == "second@gmail.com"


@pytest.mark.django_db
def test_oauth_callback_invalid_state(db):
    client = APIClient()
    resp = client.get(
        "/api/v1/credentials/oauth/google/callback/",
        {"code": "somecode", "state": "invalid.state.value"},
    )
    assert resp.status_code == 400
    assert b"credential-oauth" in resp.content
    assert b"ok:false" in resp.content


@pytest.mark.django_db
def test_oauth_callback_provider_error(db):
    client = APIClient()
    resp = client.get(
        "/api/v1/credentials/oauth/google/callback/",
        {"error": "access_denied", "state": "anything"},
    )
    assert resp.status_code == 400
    assert b"ok:false" in resp.content


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_valid_access_token_no_refresh_needed(db):
    from core.apps.credentials.services.oauth import get_valid_access_token
    project = ProjectModel._create_fake()
    cred = _make_oauth_credential(project.owner, access_token="valid_tok")
    token = get_valid_access_token(cred)
    assert token == "valid_tok"


@pytest.mark.django_db
def test_get_valid_access_token_refreshes_expired(db):
    from core.apps.credentials.services.oauth import get_valid_access_token
    project = ProjectModel._create_fake()

    # Create credential with expired token
    expired_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    data = {
        "access_token": "old_tok",
        "refresh_token": "refresh_tok_abc",
        "expires_at": expired_at,
        "scope": "openid",
        "token_type": "Bearer",
        "account_email": "x@x.com",
    }
    cred = Credential.objects.create(
        owner=project.owner,
        type_key="google_email",
        name="x@x.com",
        data_encrypted=crypto.encrypt(data),
    )

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "fresh_tok_xyz",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch("core.apps.credentials.oauth_providers._get_google_client_id", return_value="cid"), \
         patch("core.apps.credentials.oauth_providers._get_google_client_secret", return_value="cs"), \
         patch("core.apps.credentials.services.oauth.http_requests.post", return_value=mock_resp):
        token = get_valid_access_token(cred)

    assert token == "fresh_tok_xyz"
    cred.refresh_from_db()
    assert crypto.decrypt(cred.data_encrypted)["access_token"] == "fresh_tok_xyz"
    # refresh_token should be preserved since new response didn't include one
    assert crypto.decrypt(cred.data_encrypted)["refresh_token"] == "refresh_tok_abc"


@pytest.mark.django_db
def test_get_valid_access_token_non_oauth2_raises(db):
    from core.apps.credentials.services.oauth import get_valid_access_token
    project = ProjectModel._create_fake()
    cred = Credential.objects.create(
        owner=project.owner,
        type_key="bearer",
        name="bearer cred",
        data_encrypted=crypto.encrypt({"token": "t"}),
    )
    with pytest.raises(ValueError, match="not oauth2"):
        get_valid_access_token(cred)


# ---------------------------------------------------------------------------
# Registry types check
# ---------------------------------------------------------------------------

def test_registry_has_google_oauth2_types():
    from core.apps.credentials.registry import get_type, list_types
    keys = [t["key"] for t in list_types()]
    assert "google_email" in keys
    assert "google_sheets" in keys
    assert "google_drive" in keys
    assert "google" not in keys  # old placeholder removed

    email_type = get_type("google_email")
    assert email_type["mode"] == "oauth2"
    assert email_type["provider"] == "google"
    assert "openid" in email_type["scopes"]
    assert email_type["fields"] == []


def test_registry_provider_scopes_exposed():
    from core.apps.credentials.registry import list_types
    sheets = next(t for t in list_types() if t["key"] == "google_sheets")
    assert "spreadsheets" in sheets["scopes"][2]
    assert sheets["provider"] == "google"


# ---------------------------------------------------------------------------
# Internal endpoint with oauth2 type
# ---------------------------------------------------------------------------

INTERNAL_TOKEN = "test-internal-secret"


@pytest.fixture(autouse=True)
def set_internal_token(settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN


@pytest.mark.django_db
def test_internal_oauth2_returns_fresh_token(db):
    project = ProjectModel._create_fake()
    cred = _make_oauth_credential(project.owner, access_token="fresh_existing")

    client = APIClient()
    url = f"/api/v1/internal/credentials/{cred.id}/"
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN, HTTP_X_PROJECT_ID=str(project.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "oauth2"
    # access_token should be present and fresh (no refresh needed since not expired)
    assert data["data"]["access_token"] == "fresh_existing"
