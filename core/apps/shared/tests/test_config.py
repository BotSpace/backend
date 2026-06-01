"""Tests for the global Config system.

Covers:
- Public endpoint returns seeded ai_agent keys.
- Non-public configs are excluded from /public/.
- Admin PATCH updates a value.
- Anonymous user cannot access admin list/update endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.shared.models import Config

User = get_user_model()

AI_AGENT_KEYS = {
    "ai_agent.provider": "bedrock",
    "ai_agent.model": "qwen.qwen3-coder-480b-a35b-v1:0",
    "ai_agent.region": "us-west-2",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anon():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(phone="+99890000001", password="testpass123")


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def seed_configs(db):
    """Create the three ai_agent config entries plus one private entry."""
    for key, value in AI_AGENT_KEYS.items():
        group, _, name = key.partition(".")
        Config.objects.get_or_create(
            key=key,
            defaults={"value": value, "group": group, "label": name, "is_public": True},
        )
    Config.objects.get_or_create(
        key="internal.secret",
        defaults={"value": "s3cr3t", "group": "internal", "label": "Secret", "is_public": False},
    )


# ---------------------------------------------------------------------------
# Public endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_endpoint_returns_seeded_ai_agent_keys(anon, seed_configs):
    url = reverse("v1:config-public")
    response = anon.get(url)
    assert response.status_code == 200
    data = response.json()["data"]
    for key, expected_value in AI_AGENT_KEYS.items():
        assert key in data, f"Missing key: {key}"
        assert data[key] == expected_value, f"Wrong value for {key}"


@pytest.mark.django_db
def test_public_endpoint_excludes_non_public_configs(anon, seed_configs):
    url = reverse("v1:config-public")
    response = anon.get(url)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "internal.secret" not in data


@pytest.mark.django_db
def test_public_endpoint_no_auth_required(seed_configs):
    """Completely unauthenticated call must succeed."""
    client = APIClient()
    url = reverse("v1:config-public")
    response = client.get(url)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Admin list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_list_requires_auth(anon, seed_configs):
    url = reverse("v1:config-list")
    response = anon.get(url)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_list_returns_all_configs(admin_client, seed_configs):
    url = reverse("v1:config-list")
    response = admin_client.get(url)
    assert response.status_code == 200
    keys = [item["key"] for item in response.json()["data"]]
    for key in AI_AGENT_KEYS:
        assert key in keys
    assert "internal.secret" in keys


# ---------------------------------------------------------------------------
# Admin PATCH endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_patch_updates_value(admin_client, seed_configs):
    url = reverse("v1:config-detail", kwargs={"key": "ai_agent.provider"})
    response = admin_client.patch(url, {"value": "openai"}, format="json")
    assert response.status_code == 200
    Config.objects.filter(key="ai_agent.provider").get()
    assert Config.objects.get(key="ai_agent.provider").value == "openai"


@pytest.mark.django_db
def test_admin_patch_requires_admin(anon, seed_configs):
    url = reverse("v1:config-detail", kwargs={"key": "ai_agent.provider"})
    response = anon.patch(url, {"value": "openai"}, format="json")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_patch_regular_user_forbidden(db, seed_configs):
    regular = baker.make(User, is_staff=False, is_superuser=False)
    client = APIClient()
    client.force_authenticate(user=regular)
    url = reverse("v1:config-detail", kwargs={"key": "ai_agent.provider"})
    response = client.patch(url, {"value": "openai"}, format="json")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_patch_can_toggle_is_public(admin_client, seed_configs):
    url = reverse("v1:config-detail", kwargs={"key": "internal.secret"})
    response = admin_client.patch(url, {"is_public": True}, format="json")
    assert response.status_code == 200
    assert Config.objects.get(key="internal.secret").is_public is True
