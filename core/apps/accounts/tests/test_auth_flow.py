"""Integration tests for the auth + permission boundaries.

Covers the rotation/blacklist behaviour enabled in phase 0 and that
the legacy and /api/v1/ surfaces both accept tokens.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def authed_pair(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


@pytest.mark.django_db
def test_me_requires_authentication():
    response = APIClient().get("/api/v1/auth/me/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_me_returns_user_when_authenticated(user, authed_pair):
    access, _refresh = authed_pair
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_legacy_path_also_accepts_jwt(user, authed_pair):
    access, _ = authed_pair
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/auth/me/")
    # legacy alias should still resolve
    assert response.status_code == 200
    assert response.headers.get("Deprecation") in (None, "true")  # root path has no /api/ prefix


@pytest.mark.django_db
def test_legacy_api_path_emits_deprecation_header(user, authed_pair):
    access, _ = authed_pair
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/user/balance/")
    assert response.headers.get("Deprecation") == "true"
    assert "Sunset" in response.headers


@pytest.mark.django_db
def test_refresh_rotation_blacklists_old_token(user, authed_pair):
    _access, refresh = authed_pair
    client = APIClient()
    # First refresh: should succeed and return new tokens.
    r1 = client.post(reverse("token_refresh"), data={"refresh": refresh})
    assert r1.status_code == 200
    new_refresh = r1.data.get("refresh") or r1.data.get("data", {}).get("refresh")
    assert new_refresh and new_refresh != refresh
    # Reusing the original refresh must now fail (blacklisted).
    r2 = client.post(reverse("token_refresh"), data={"refresh": refresh})
    assert r2.status_code in (400, 401)
