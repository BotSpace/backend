"""Tests for OAuth 2.1 Authorization Server endpoints.

Covers: metadata shape, DCR register (valid/invalid redirect_uri),
authorize meta validation, approve→code→token happy path,
bad code_verifier, code reuse prevention, refresh grant.
"""

from __future__ import annotations

import base64
import hashlib
import secrets

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _make_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge)."""
    verifier = secrets.token_urlsafe(43)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _register_client(api_client: APIClient, redirect_uris=None):
    if redirect_uris is None:
        redirect_uris = ["http://localhost:3000/callback"]
    return api_client.post(
        reverse("oauth-register"),
        {"redirect_uris": redirect_uris, "client_name": "Test MCP"},
        format="json",
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def clear_cache():
    """Flush relevant cache keys before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registered_client(api_client):
    resp = _register_client(api_client)
    assert resp.status_code == 201
    return resp.json()


# --------------------------------------------------------------------------- #
# 1. Metadata
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_metadata_shape(api_client):
    resp = api_client.get("/.well-known/oauth-authorization-server")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    for key in (
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "registration_endpoint",
        "response_types_supported",
        "grant_types_supported",
        "code_challenge_methods_supported",
        "token_endpoint_auth_methods_supported",
        "scopes_supported",
    ):
        assert key in data, f"Missing key: {key}"
    # Must NOT have envelope keys
    assert "status" not in data
    assert "data" not in data
    assert data["code_challenge_methods_supported"] == ["S256"]


# --------------------------------------------------------------------------- #
# 2. DCR Register
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_register_valid_localhost(api_client):
    resp = _register_client(api_client, ["http://localhost:54321/cb"])
    assert resp.status_code == 201
    data = resp.json()
    assert "client_id" in data
    assert "client_id_issued_at" in data
    assert data["token_endpoint_auth_method"] == "none"
    assert "authorization_code" in data["grant_types"]
    # no envelope
    assert "status" not in data


@pytest.mark.django_db
def test_register_valid_https(api_client):
    resp = _register_client(api_client, ["https://app.example.com/callback"])
    assert resp.status_code == 201


@pytest.mark.django_db
def test_register_multiple_uris(api_client):
    uris = ["http://localhost:3000/callback", "https://app.example.com/cb"]
    resp = _register_client(api_client, uris)
    assert resp.status_code == 201
    assert resp.json()["redirect_uris"] == uris


@pytest.mark.django_db
def test_register_invalid_http_non_localhost(api_client):
    resp = _register_client(api_client, ["http://evil.com/callback"])
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_redirect_uri"


@pytest.mark.django_db
def test_register_missing_redirect_uris(api_client):
    resp = api_client.post(reverse("oauth-register"), {"client_name": "bad"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_client_metadata"


@pytest.mark.django_db
def test_register_bad_scheme(api_client):
    resp = _register_client(api_client, ["ftp://localhost/cb"])
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_redirect_uri"


# --------------------------------------------------------------------------- #
# 3. Authorize meta
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_authorize_meta_valid(api_client, registered_client):
    verifier, challenge = _make_pkce()
    resp = api_client.get(
        reverse("oauth-authorize-meta"),
        {
            "client_id": registered_client["client_id"],
            "redirect_uri": registered_client["redirect_uris"][0],
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["client_name"] == "Test MCP"


@pytest.mark.django_db
def test_authorize_meta_unknown_client(api_client):
    _, challenge = _make_pkce()
    resp = api_client.get(
        reverse("oauth-authorize-meta"),
        {
            "client_id": "nonexistent",
            "redirect_uri": "http://localhost:3000/callback",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_authorize_meta_wrong_redirect_uri(api_client, registered_client):
    _, challenge = _make_pkce()
    resp = api_client.get(
        reverse("oauth-authorize-meta"),
        {
            "client_id": registered_client["client_id"],
            "redirect_uri": "http://localhost:9999/other",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_authorize_meta_missing_challenge(api_client, registered_client):
    resp = api_client.get(
        reverse("oauth-authorize-meta"),
        {
            "client_id": registered_client["client_id"],
            "redirect_uri": registered_client["redirect_uris"][0],
            "response_type": "code",
            "code_challenge_method": "S256",
        },
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# 4 & 5. Full happy path: approve → code → token exchange
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_full_oauth_flow(auth_client, registered_client):
    """Authenticate user, approve, exchange code for tokens."""
    verifier, challenge = _make_pkce()
    redirect_uri = registered_client["redirect_uris"][0]
    client_id = registered_client["client_id"]

    # Step 1: approve
    approve_resp = auth_client.post(
        reverse("oauth-authorize-approve"),
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "mystate",
            "scope": "mcp",
        },
        format="json",
    )
    assert approve_resp.status_code == 200, approve_resp.json()
    redirect_url = approve_resp.json()["data"]["redirect_url"]
    assert "code=" in redirect_url
    assert "state=mystate" in redirect_url

    # Extract code
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(redirect_url)
    code = parse_qs(parsed.query)["code"][0]

    # Step 2: token exchange
    token_resp = auth_client.post(
        reverse("oauth-token"),
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        },
        format="json",
    )
    assert token_resp.status_code == 200, token_resp.json()
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "Bearer"
    assert "expires_in" in token_data
    assert token_data["scope"] == "mcp"
    # no envelope
    assert "status" not in token_data


@pytest.mark.django_db
def test_wrong_code_verifier_rejected(auth_client, registered_client):
    verifier, challenge = _make_pkce()
    redirect_uri = registered_client["redirect_uris"][0]
    client_id = registered_client["client_id"]

    approve_resp = auth_client.post(
        reverse("oauth-authorize-approve"),
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        format="json",
    )
    from urllib.parse import parse_qs, urlparse
    code = parse_qs(urlparse(approve_resp.json()["data"]["redirect_url"]).query)["code"][0]

    resp = auth_client.post(
        reverse("oauth-token"),
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": "wrong-verifier-that-does-not-match-the-challenge",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_grant"


@pytest.mark.django_db
def test_code_reuse_rejected(auth_client, registered_client):
    verifier, challenge = _make_pkce()
    redirect_uri = registered_client["redirect_uris"][0]
    client_id = registered_client["client_id"]

    approve_resp = auth_client.post(
        reverse("oauth-authorize-approve"),
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        format="json",
    )
    from urllib.parse import parse_qs, urlparse
    code = parse_qs(urlparse(approve_resp.json()["data"]["redirect_url"]).query)["code"][0]

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    # First use: OK
    first = auth_client.post(reverse("oauth-token"), payload, format="json")
    assert first.status_code == 200

    # Second use: must fail (code deleted from cache)
    second = auth_client.post(reverse("oauth-token"), payload, format="json")
    assert second.status_code == 400
    assert second.json()["error"] == "invalid_grant"


@pytest.mark.django_db
def test_refresh_grant(auth_client, registered_client):
    verifier, challenge = _make_pkce()
    redirect_uri = registered_client["redirect_uris"][0]
    client_id = registered_client["client_id"]

    approve_resp = auth_client.post(
        reverse("oauth-authorize-approve"),
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        format="json",
    )
    from urllib.parse import parse_qs, urlparse
    code = parse_qs(urlparse(approve_resp.json()["data"]["redirect_url"]).query)["code"][0]

    token_resp = auth_client.post(
        reverse("oauth-token"),
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        },
        format="json",
    )
    refresh_token = token_resp.json()["refresh_token"]

    # Use refresh token
    refresh_resp = auth_client.post(
        reverse("oauth-token"),
        {"grant_type": "refresh_token", "refresh_token": refresh_token},
        format="json",
    )
    assert refresh_resp.status_code == 200, refresh_resp.json()
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    assert refresh_data["token_type"] == "Bearer"
    assert "expires_in" in refresh_data
    # no envelope
    assert "status" not in refresh_data


@pytest.mark.django_db
def test_refresh_grant_invalid_token(api_client):
    resp = api_client.post(
        reverse("oauth-token"),
        {"grant_type": "refresh_token", "refresh_token": "totally.invalid.token"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_grant"


@pytest.mark.django_db
def test_unsupported_grant_type(api_client):
    resp = api_client.post(
        reverse("oauth-token"),
        {"grant_type": "client_credentials"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "unsupported_grant_type"
