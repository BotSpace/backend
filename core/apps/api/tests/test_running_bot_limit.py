"""Running-bot limit (feat/running-bot-limit) uchun testlar.

Nima tekshiriladi:
1. 10 ta running bot bor user 11-chisini release qilsa → 409, body to'liq assert.
2. Allaqachon running loyihasini qayta release/debug qilsa → ruxsat (bloklanmaydi).
3. is_template=True loyihalar hisobga kirmaydi.
4. debug action uchun limit testi.
5. create_from_template uchun limit testi.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models.project import DebugModel, ProjectModel, RelaseModel

# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------

RUNNING = ContainerStatusEnum.RUNNING.value
INIT = ContainerStatusEnum.INIT.value
STOPPED = ContainerStatusEnum.STOPPED.value


def _make_user() -> User:
    import random
    phone = f"+9989000{random.randint(10000, 99999)}"
    return User.objects.create_user(phone=phone, username=phone, password="pass")


def _make_project(owner: User, *, is_template: bool = False) -> ProjectModel:
    return ProjectModel.objects.create(name="test-bot", owner=owner, is_template=is_template)


def _set_debug_running(project: ProjectModel, status: str = RUNNING) -> DebugModel:
    debug, _ = DebugModel.objects.get_or_create(project=project)
    debug.status = status
    debug.save()
    return debug


def _make_release(project: ProjectModel, status: str = RUNNING) -> RelaseModel:
    return RelaseModel.objects.create(project=project, version=1, status=status)


def _make_auth_client(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# Global patch: k8s / deploy / webhook — CI da bu servislar yo'q
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_external_services():
    magic = MagicMock()
    magic.metadata.name = "test-svc-123"
    with (
        patch("core.apps.api.signals.project.deploy_service", return_value=magic),
        patch("core.apps.api.signals.project.sync_bot"),
        patch("core.apps.api.views.project.deploy_service", return_value=magic),
        patch("core.apps.api.views.project.set_webhook"),
        patch("core.apps.api.views.project.copy_collections"),
    ):
        yield


# ---------------------------------------------------------------------------
# 1. Release: 10 ta running bot bor — 11-chisi bloklana
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_release_blocked_when_limit_reached():
    """10 ta running loyiha bo'lsa 11-chi release 409 qaytaradi."""
    user = _make_user()
    # 10 ta loyiha bilan running release yaratish
    for _ in range(10):
        proj = _make_project(user)
        _make_release(proj, status=RUNNING)

    # 11-chi loyiha
    new_proj = _make_project(user)

    client = _make_auth_client(user)
    url = reverse("relase-list")
    response = client.post(url, data={"project": new_proj.pk}, format="json")

    assert response.status_code == 409, response.json()
    body = response.json()

    # Majburiy maydonlar
    assert body["status"] is False
    assert body["code"] == "running_bot_limit"
    assert body["limit"] == 10
    assert isinstance(body["running"], list)
    assert len(body["running"]) == 10

    # running ro'yxatidagi har bir element shakli
    for entry in body["running"]:
        assert "project_id" in entry
        assert "name" in entry
        assert entry["kind"] in ("debug", "release")
        if entry["kind"] == "release":
            assert "release_id" in entry

    # detail matnida limit ko'rsatilishi shart
    assert "10" in body["detail"]


# ---------------------------------------------------------------------------
# 2. Allaqachon running loyihani qayta release qilsa — ruxsat
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_release_allowed_for_own_running_project():
    """O'zining running loyihasini qayta release qilish bloklonmaydi."""
    user = _make_user()
    # 9 ta boshqa running loyiha
    for _ in range(9):
        p = _make_project(user)
        _make_release(p, status=RUNNING)

    # Target loyiha allaqachon running
    target = _make_project(user)
    _make_release(target, status=RUNNING)
    # Jami 10 ta running bor, lekin target o'zi shular ichida — bloklanmaydi

    client = _make_auth_client(user)
    url = reverse("relase-list")
    response = client.post(url, data={"project": target.pk}, format="json")

    # 409 bo'lmasligi kerak (201 yoki kamida 4xx bo'lmagan status)
    assert response.status_code != 409, response.json()


# ---------------------------------------------------------------------------
# 3. is_template=True loyihalar hisobga kirmaydi
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_template_projects_excluded_from_count():
    """is_template=True loyihalar running hisobidan chiqarib tashlanadi."""
    user = _make_user()
    # 9 ta oddiy running loyiha
    for _ in range(9):
        p = _make_project(user)
        _make_release(p, status=RUNNING)

    # is_template=True loyihalar — ular hisobga kirmaydi
    for _ in range(5):
        tp = _make_project(user, is_template=True)
        _make_release(tp, status=RUNNING)

    # 11-chi oddiy loyiha — 10 ta limit bo'lmagan (9 ta bor)
    new_proj = _make_project(user)

    client = _make_auth_client(user)
    url = reverse("relase-list")
    response = client.post(url, data={"project": new_proj.pk}, format="json")

    # 409 bo'lmasligi kerak — 9 ta running bor, limit=10
    assert response.status_code != 409, response.json()


# ---------------------------------------------------------------------------
# 4. debug action — limit testi
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_debug_blocked_when_limit_reached():
    """10 ta running bot bor — yangi debug 409 qaytaradi."""
    user = _make_user()
    for _ in range(10):
        p = _make_project(user)
        _set_debug_running(p, status=RUNNING)

    new_proj = _make_project(user)
    client = _make_auth_client(user)
    url = reverse("project-debug", kwargs={"pk": new_proj.pk})
    response = client.get(url)

    assert response.status_code == 409, response.json()
    body = response.json()
    assert body["status"] is False
    assert body["code"] == "running_bot_limit"
    assert body["limit"] == 10
    assert len(body["running"]) == 10


@pytest.mark.django_db
def test_debug_allowed_for_own_running_project():
    """O'zining running loyihasini qayta debug qilish bloklanmaydi."""
    user = _make_user()
    for _ in range(9):
        p = _make_project(user)
        _set_debug_running(p, status=RUNNING)

    target = _make_project(user)
    _set_debug_running(target, status=RUNNING)
    # Jami 10 ta running, target shular ichida — bloklanmaydi

    client = _make_auth_client(user)
    url = reverse("project-debug", kwargs={"pk": target.pk})
    response = client.get(url)

    assert response.status_code != 409, response.json()


# ---------------------------------------------------------------------------
# 5. create_from_template — limit testi
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@patch("core.apps.api.views.project.ListProjectSerializer")
def test_create_from_template_blocked_when_limit_reached(_lps):
    """10 ta running bot bor — create_from_template 409 qaytaradi."""
    from decimal import Decimal

    from core.apps.template.models.order import TemplateOrderModel
    from core.apps.template.models.template import TemplateModel

    _lps.return_value.data = {"id": 0}

    user = _make_user()
    # 10 ta running loyiha
    for _ in range(10):
        p = _make_project(user)
        _make_release(p, status=RUNNING)

    # Shablon
    template_owner = _make_user()
    template_project = _make_project(template_owner)
    template_project.flow = {"nodes": [], "edges": []}
    template_project.save()

    template = TemplateModel.objects.create(
        author=template_owner,
        name="Test template",
        image="template/fake.png",
        project=template_project,
        short_description="short",
        description="long",
        original_price=Decimal("0.00"),
        is_verify=True,
        required_envs=[],
    )
    TemplateOrderModel.objects.create(
        user=user,
        template=template,
        payment_status=True,
        status="confirm",
        amount=Decimal("0.00"),
    )

    client = _make_auth_client(user)
    url = reverse("project-create-from-template")
    response = client.post(
        url,
        data={"template": template.pk, "name": "New bot", "token": "123:tok"},
        format="json",
    )

    assert response.status_code == 409, response.json()
    body = response.json()
    assert body["status"] is False
    assert body["code"] == "running_bot_limit"
    assert body["limit"] == 10


# ---------------------------------------------------------------------------
# 6. initializing status ham running hisoblanadi
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_initializing_debug_counted_as_running():
    """INIT (initializing) statusdagi debug containerlari ham hisobga olinadi."""
    user = _make_user()
    for _ in range(10):
        p = _make_project(user)
        _set_debug_running(p, status=INIT)  # initializing — running hisoblanadi

    new_proj = _make_project(user)
    client = _make_auth_client(user)
    url = reverse("project-debug", kwargs={"pk": new_proj.pk})
    response = client.get(url)

    assert response.status_code == 409, response.json()


@pytest.mark.django_db
def test_initializing_release_counted_as_running():
    """INIT (initializing) statusdagi releaselar ham hisobga olinadi."""
    user = _make_user()
    for _ in range(10):
        p = _make_project(user)
        _make_release(p, status=INIT)

    new_proj = _make_project(user)
    client = _make_auth_client(user)
    url = reverse("relase-list")
    response = client.post(url, data={"project": new_proj.pk}, format="json")

    assert response.status_code == 409, response.json()


# ---------------------------------------------------------------------------
# 7. stopped/failed statuslar hisobga kirmaydi
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_stopped_bots_not_counted():
    """STOPPED statusdagi botlar limit hisobiga kirmaydi."""
    user = _make_user()
    # 10 ta stopped loyiha (limit emas)
    for _ in range(10):
        p = _make_project(user)
        _make_release(p, status=STOPPED)

    new_proj = _make_project(user)
    client = _make_auth_client(user)
    url = reverse("relase-list")
    response = client.post(url, data={"project": new_proj.pk}, format="json")

    # Stopped botlar hisobga kirmaydi — 409 bo'lmasligi kerak
    assert response.status_code != 409, response.json()
