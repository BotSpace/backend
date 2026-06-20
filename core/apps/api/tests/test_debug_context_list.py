"""
DebugContextListView testlari.

GET /api/debug/context/?project_id=<id>
- project bo'yicha barcha faol chat snapshot'larini qaytaradi
- owner guard: boshqa user 403
- TTL o'tgan chat (cache miss) o'tkazib yuboriladi
"""
import json
from unittest.mock import patch, call

import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel

CONTEXT_EVENT_URL = "/api/debug/context-event/"
CONTEXT_LIST_URL = "/api/debug/context/"
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


def _owner(project):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.get(pk=project.owner_id)


# ---------------------------------------------------------------------------
# POST iki chat → GET list ikkisini qaytaradi
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_list_returns_two_chats(project, client, settings):
    """POST 2 ta chat → GET list'da 2 ta chat qaytadi."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN

    snap1 = {"project": project.pk, "chat_id": 101, "variables": {"name": "Ali"}, "ts": 1700000001}
    snap2 = {"project": project.pk, "chat_id": 202, "variables": {"name": "Vali"}, "ts": 1700000002}

    # chats_set va har bir chat uchun snapshot'ni simulatsiya qilamiz
    chats_set = json.dumps([101, 202])
    cache_store = {
        f"debug_ctx_chats_{project.pk}": chats_set,
        f"debug_ctx_{project.pk}_101": json.dumps(snap1),
        f"debug_ctx_{project.pk}_202": json.dumps(snap2),
    }

    def fake_cache_get(key):
        return cache_store.get(key)

    owner = _owner(project)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.side_effect = fake_cache_get
        resp = client.get(CONTEXT_LIST_URL, {"project_id": project.pk})

    assert resp.status_code == 200
    chats = resp.data["chats"]
    assert len(chats) == 2
    chat_ids = {c["chat_id"] for c in chats}
    assert chat_ids == {101, 202}


@pytest.mark.django_db
def test_context_list_ttl_expired_chat_skipped(project, client, settings):
    """TTL o'tgan chat (cache miss) natijadan o'tkazib yuboriladi."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN

    snap_alive = {"project": project.pk, "chat_id": 10, "variables": {"x": 1}, "ts": 1700000010}
    chats_set = json.dumps([10, 20])  # 20 — TTL o'tgan

    cache_store = {
        f"debug_ctx_chats_{project.pk}": chats_set,
        f"debug_ctx_{project.pk}_10": json.dumps(snap_alive),
        # debug_ctx_{pk}_20 — yo'q (TTL)
    }

    owner = _owner(project)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.side_effect = lambda key: cache_store.get(key)
        resp = client.get(CONTEXT_LIST_URL, {"project_id": project.pk})

    assert resp.status_code == 200
    chats = resp.data["chats"]
    assert len(chats) == 1
    assert chats[0]["chat_id"] == 10


@pytest.mark.django_db
def test_context_list_empty_when_no_chats(project, client):
    """Hech qanday chat bo'lmasa, bo'sh ro'yxat qaytadi."""
    owner = _owner(project)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None  # chats_set ham yo'q
        resp = client.get(CONTEXT_LIST_URL, {"project_id": project.pk})

    assert resp.status_code == 200
    assert resp.data["chats"] == []


# ---------------------------------------------------------------------------
# Owner guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_list_other_user_returns_403(project, client):
    """Boshqa foydalanuvchi project'ning context list'ini ko'ra olmasligi kerak."""
    from django.contrib.auth import get_user_model
    other = get_user_model().objects.create_user(phone="+998909999999", password="pass")
    client.force_authenticate(user=other)

    resp = client.get(CONTEXT_LIST_URL, {"project_id": project.pk})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_context_list_unauthenticated_returns_401(project, client):
    resp = client.get(CONTEXT_LIST_URL, {"project_id": project.pk})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_context_list_missing_project_id_returns_400(project, client):
    owner = _owner(project)
    client.force_authenticate(user=owner)
    resp = client.get(CONTEXT_LIST_URL)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_context_list_unknown_project_returns_404(project, client):
    owner = _owner(project)
    client.force_authenticate(user=owner)
    resp = client.get(CONTEXT_LIST_URL, {"project_id": 999999})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Noslash URL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_list_noslash_url(project, client):
    """Trailing-slash-siz URL ham 200 qaytarishi kerak."""
    owner = _owner(project)
    client.force_authenticate(user=owner)

    with patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None
        resp = client.get("/api/debug/context", {"project_id": project.pk})

    assert resp.status_code == 200
    assert "chats" in resp.data


# ---------------------------------------------------------------------------
# POST context-event → chats_set'ga qo'shilishi
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_event_adds_chat_id_to_set(project, client, settings):
    """POST /context-event/ → chats_set kaliti ham yangilanishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN

    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.return_value = None  # chats_set bo'sh
        resp = client.post(
            CONTEXT_EVENT_URL,
            data={"project_id": project.pk, "chat_id": 55, "variables": {"a": 1}, "ts": 1700000055},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )

    assert resp.status_code == 200

    # cache.set ikkita marta chaqirilgan: snapshot + chats_set
    set_calls = mock_cache.set.call_args_list
    set_keys = [c[0][0] for c in set_calls]
    assert f"debug_ctx_{project.pk}_55" in set_keys
    chats_key = f"debug_ctx_chats_{project.pk}"
    assert chats_key in set_keys

    # chats_set qiymatida chat_id=55 bo'lishi kerak
    for c in set_calls:
        if c[0][0] == chats_key:
            saved = json.loads(c[0][1])
            assert 55 in saved
            break


@pytest.mark.django_db
def test_context_event_does_not_duplicate_chat_id(project, client, settings):
    """Bir xil chat_id ikki marta POST qilinsa, SET'da faqat bir marta bo'lishi kerak."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN

    existing_set = json.dumps([55])

    with patch("core.apps.api.views.debug.ws_publish"), \
         patch("core.apps.api.views.debug.cache") as mock_cache:
        mock_cache.get.side_effect = lambda key: existing_set if "chats" in key else None
        resp = client.post(
            CONTEXT_EVENT_URL,
            data={"project_id": project.pk, "chat_id": 55, "variables": {}, "ts": 0},
            format="json",
            HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN,
        )

    assert resp.status_code == 200

    for c in mock_cache.set.call_args_list:
        if "chats" in c[0][0]:
            saved = json.loads(c[0][1])
            assert saved.count(55) == 1
            break
