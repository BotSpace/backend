"""
DebugErrorEventView (POST /api/debug/error-event/) va
DebugErrorListView (GET /api/debug/errors/) testlari.
"""
import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel

ERROR_EVENT_URL = "/api/debug/error-event/"
ERROR_LIST_URL = "/api/debug/errors/"
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
# POST /api/debug/error-event/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_error_event_publishes_ws(project, client, settings):
    """To'g'ri token bilan kelgan xato WS orqali publish bo'lishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish") as mock_publish, \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.post(
            ERROR_EVENT_URL,
            data={
                "project_id": project.pk,
                "chat_id": 42,
                "node_id": "node_abc",
                "node_type": "HttpRequestNode",
                "message": "Connection timeout",
                "detail": "requests.exceptions.Timeout",
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
    assert schema.node_id == "node_abc"
    assert schema.message == "Connection timeout"
    from core.domain.ws import EventTypes
    assert event_type == EventTypes.ERROR


@pytest.mark.django_db
def test_error_event_saves_to_cache(project, client, settings):
    """Xato Redis ro'yxatiga JSON sifatida yozilishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.post(
            ERROR_EVENT_URL,
            data={
                "project_id": project.pk,
                "chat_id": 7,
                "node_id": "n1",
                "message": "Xato xabar",
            },
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200
    mock_cache.set.assert_called_once()
    key, value, _ = mock_cache.set.call_args[0]
    assert key == f"proj_errors_{project.pk}"
    errors = json.loads(value)
    assert len(errors) == 1
    assert errors[0]["message"] == "Xato xabar"
    assert errors[0]["chat_id"] == 7


@pytest.mark.django_db
def test_error_event_cap_at_100(project, client, settings):
    """101-xato kelsa ro'yxat 100 ta bilan cheklanishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    existing = [{"project": project.pk, "chat_id": i, "node_id": None, "node_type": None,
                 "message": f"err{i}", "detail": None, "ts": None} for i in range(100)]
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = json.dumps(existing)
        client.post(
            ERROR_EVENT_URL,
            data={"project_id": project.pk, "chat_id": 999, "message": "yangi"},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    _, value, _ = mock_cache.set.call_args[0]
    saved = json.loads(value)
    assert len(saved) == 100
    # Eng oxirgi qo'shilgan (101-chi) saqlanishi, eng birinchi chiqib ketishi kerak.
    assert saved[-1]["message"] == "yangi"
    assert saved[0]["message"] == "err1"


@pytest.mark.django_db
def test_error_event_wrong_token_returns_403(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        ERROR_EVENT_URL,
        data={"project_id": project.pk, "chat_id": 1, "message": "test"},
        format="json",
        HTTP_X_INTERNAL_TOKEN="yalg'on-token",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_error_event_missing_project_id_returns_400(client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        ERROR_EVENT_URL,
        data={"chat_id": 1, "message": "test"},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_error_event_missing_message_returns_400(project, client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        ERROR_EVENT_URL,
        data={"project_id": project.pk, "chat_id": 1},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_error_event_unknown_project_returns_404(client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    resp = client.post(
        ERROR_EVENT_URL,
        data={"project_id": 999999, "chat_id": 1, "message": "test"},
        format="json",
        HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_error_event_noslash_url(project, client, settings):
    """Trailing-slash-siz URL ham 200 qaytarishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.post(
            "/api/debug/error-event",
            data={"project_id": project.pk, "chat_id": 1, "message": "test"},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_error_event_uuid_lookup(project, client, settings):
    """project_id UUID sifatida ham qabul qilinishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.post(
            ERROR_EVENT_URL,
            data={"project_id": str(project.uuid), "chat_id": 5, "message": "uuid test"},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/debug/errors/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_error_list_returns_errors(project, client):
    """Cache'da xatolar bo'lsa, eng yangi birinchi qaytarishi kerak."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    stored = [
        {"project": project.pk, "chat_id": 1, "node_id": "n1", "node_type": None,
         "message": "birinchi", "detail": None, "ts": 1000},
        {"project": project.pk, "chat_id": 2, "node_id": "n2", "node_type": None,
         "message": "ikkinchi", "detail": None, "ts": 2000},
    ]
    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = json.dumps(stored)
        resp = client.get(ERROR_LIST_URL, {"project_id": project.pk})

    assert resp.status_code == 200
    errors = resp.data["errors"]
    assert len(errors) == 2
    # Eng yangi (oxirgi) birinchi bo'lishi kerak.
    assert errors[0]["message"] == "ikkinchi"
    assert errors[1]["message"] == "birinchi"


@pytest.mark.django_db
def test_error_list_empty_cache(project, client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.get(ERROR_LIST_URL, {"project_id": project.pk})

    assert resp.status_code == 200
    assert resp.data["errors"] == []


@pytest.mark.django_db
def test_error_list_limit_param(project, client):
    """limit parametri ishlashi kerak."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    stored = [{"project": project.pk, "chat_id": i, "node_id": None, "node_type": None,
               "message": f"err{i}", "detail": None, "ts": i} for i in range(10)]
    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = json.dumps(stored)
        resp = client.get(ERROR_LIST_URL, {"project_id": project.pk, "limit": 3})

    assert resp.status_code == 200
    assert len(resp.data["errors"]) == 3
    # Oxirgi 3 ta, yangi birinchi.
    assert resp.data["errors"][0]["message"] == "err9"


@pytest.mark.django_db
def test_error_list_other_user_returns_403(project, client):
    """Boshqa foydalanuvchi project xatolarini ko'ra olmasligi kerak."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other = User.objects.create_user(phone="+998901234568", password="pass")
    client.force_authenticate(user=other)

    resp = client.get(ERROR_LIST_URL, {"project_id": project.pk})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_error_list_unauthenticated_returns_401(project, client):
    resp = client.get(ERROR_LIST_URL, {"project_id": project.pk})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_error_list_missing_project_id_returns_400(project, client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    resp = client.get(ERROR_LIST_URL)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_error_list_unknown_project_returns_404(project, client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    owner = User.objects.get(pk=project.owner_id)
    client.force_authenticate(user=owner)

    resp = client.get(ERROR_LIST_URL, {"project_id": 999999})
    assert resp.status_code == 404
