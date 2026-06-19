import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel

CONTEXT_EVENT_URL = "/api/debug/context-event/"
CONTEXT_LATEST_URL = "/api/debug/context/latest/"
INTERNAL_TOKEN = "test-internal-secret"


@pytest.fixture
def plan(db):
    return PlanModel._create_fake()


@pytest.fixture
def project(db, plan):
    return ProjectModel._create_fake()


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# POST /api/debug/context-event/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_event_publishes_ws(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish") as mock_publish, \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.add.return_value = False  # keepalive throttle (node-event path yo'q bu yerda)
        resp = client.post(
            CONTEXT_EVENT_URL,
            data={
                "project_id": project.pk,
                "chat_id": 42,
                "variables": {"name": "Ali", "step": 3},
                "ts": 1700000000000,
            },
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200
    assert resp.data["ok"] is True
    mock_publish.assert_called_once()
    owner_id, schema, event_type = mock_publish.call_args[0]
    assert owner_id == project.owner_id
    assert schema.chat_id == 42
    assert schema.variables == {"name": "Ali", "step": 3}
    assert schema.ts == 1700000000000
    from core.domain.ws import EventTypes
    assert event_type == EventTypes.CONTEXT_SNAPSHOT


@pytest.mark.django_db
def test_context_event_wrong_token_returns_403(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        CONTEXT_EVENT_URL,
        data={"project_id": project.pk, "chat_id": 1, "variables": {}, "ts": 0},
        format="json",
        HTTP_X_INTERNAL_TOKEN="wrong-token",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_context_event_missing_project_id_returns_400(client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        CONTEXT_EVENT_URL,
        data={"chat_id": 1, "variables": {}},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_context_event_unknown_project_returns_404(client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        CONTEXT_EVENT_URL,
        data={"project_id": 999999, "chat_id": 1, "variables": {}},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_context_event_saves_to_cache(project, client, settings):
    """Snapshot Redis'ga to'g'ri JSON bilan yozilishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.add.return_value = False
        resp = client.post(
            CONTEXT_EVENT_URL,
            data={"project_id": project.pk, "chat_id": 7, "variables": {"x": 1}},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200
    # cache.set chaqirildi va to'g'ri key/value yuborildi
    mock_cache.set.assert_called_once()
    call_args = mock_cache.set.call_args
    key = call_args[0][0]
    assert f"debug_ctx_{project.pk}_7" == key
    payload = json.loads(call_args[0][1])
    assert payload["chat_id"] == 7
    assert payload["variables"] == {"x": 1}


@pytest.mark.django_db
def test_context_event_uuid_lookup(project, client, settings):
    """project_id UUID sifatida ham qabul qilinishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache"):
        resp = client.post(
            CONTEXT_EVENT_URL,
            data={"project_id": str(project.uuid), "chat_id": 5, "variables": {}},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_context_event_noslash_url(project, client, settings):
    """Trailing-slash-siz URL ham 200 qaytarishi kerak (engine eski versiyalari)."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache"):
        resp = client.post(
            "/api/debug/context-event",
            data={"project_id": project.pk, "chat_id": 1, "variables": {}},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/debug/context/latest/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_latest_returns_snapshot(project, client, settings):
    """Cache'da snapshot bo'lsa, uni qaytarish kerak."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    snapshot = {"project": project.pk, "chat_id": 42, "variables": {"k": "v"}, "ts": 123}
    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = json.dumps(snapshot)
        resp = client.get(
            CONTEXT_LATEST_URL,
            {"project_id": project.pk, "chat_id": 42},
        )
    assert resp.status_code == 200
    assert resp.data["snapshot"]["variables"] == {"k": "v"}


@pytest.mark.django_db
def test_context_latest_no_snapshot_returns_null(project, client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.get(
            CONTEXT_LATEST_URL,
            {"project_id": project.pk, "chat_id": 42},
        )
    assert resp.status_code == 200
    assert resp.data["snapshot"] is None


@pytest.mark.django_db
def test_context_latest_missing_params_returns_400(project, client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    resp = client.get(CONTEXT_LATEST_URL, {"project_id": project.pk})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_context_latest_other_user_returns_403(project, client, settings):
    """Boshqa foydalanuvchi project owner'ining context'ini ko'ra olmasligi kerak."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other_user = User.objects.create_user(phone="+998901234567", password="pass")
    client.force_authenticate(user=other_user)

    resp = client.get(
        CONTEXT_LATEST_URL,
        {"project_id": project.pk, "chat_id": 42},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_context_latest_unauthenticated_returns_401(project, client):
    resp = client.get(
        CONTEXT_LATEST_URL,
        {"project_id": project.pk, "chat_id": 42},
    )
    assert resp.status_code == 401
