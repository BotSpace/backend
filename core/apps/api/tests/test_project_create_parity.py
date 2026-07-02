"""Plain project create (`POST /api/project/`) parity bilan create_from_template.

Yangi qo'llab-quvvatlanadigan maydonlar: `managed_bot_id` (Telegram-managed bot tokeni
RELEASE_BOT_TOKEN sifatida yoziladi) va `mode=debug` (tokensiz — DEBUG konteyner platforma
TEST_BOT_TOKEN fallback bilan ishga tushadi). Ikkala holatda ham javobga
bot_mode/bot_username/bot_link qo'shiladi. Legacy (faqat name/description/token) chaqiruvlar
o'zgarishsiz ishlashi kerak.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.api.models.managed_bot import ManagedBotModel
from core.apps.api.models.project import DebugModel, EnviromentModel, ProjectModel, RelaseModel
from core.apps.credentials.services import crypto


def _make_user() -> User:
    import random

    phone = f"+9989002{random.randint(10000, 99999)}"
    return User.objects.create_user(phone=phone, username=phone, password="pass")


def _make_auth_client(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


def _make_managed_bot(owner: User, *, token: str = "123456:MANAGEDTOKEN", username: str = "managed_bot") -> ManagedBotModel:
    return ManagedBotModel.objects.create(
        owner=owner,
        tg_bot_id=987654321,
        username=username,
        name="Managed Bot",
        token_encrypted=crypto.encrypt({"token": token}),
    )


@pytest.mark.django_db
class TestPlainProjectCreateLegacyBehavior:
    def test_name_only_unchanged(self):
        """Faqat name yuborilsa — hech qanday token/release/debug wiring yo'q, xuddi avvalgidek."""
        user = _make_user()
        client = _make_auth_client(user)
        url = reverse("project-list")

        response = client.post(url, data={"name": "Legacy bot"}, format="json")

        assert response.status_code == 201, response.json()
        body = response.json()["data"]
        project = ProjectModel.objects.get(pk=body["id"])

        assert not RelaseModel.objects.filter(project=project).exists()
        assert not EnviromentModel.objects.filter(project=project, key="RELEASE_BOT_TOKEN").exists()
        assert body["bot_mode"] == "release"
        assert body["bot_username"] is None
        assert body["bot_link"] is None

    def test_name_description_token_ignored_like_before(self):
        """token maydoni hali ham backendda hech qanday ta'sir qilmaydi (legacy)."""
        user = _make_user()
        client = _make_auth_client(user)
        url = reverse("project-list")

        response = client.post(
            url,
            data={"name": "Legacy bot 2", "description": "desc", "token": "1234:ABCDEF"},
            format="json",
        )

        assert response.status_code == 201, response.json()
        body = response.json()["data"]
        project = ProjectModel.objects.get(pk=body["id"])
        assert not EnviromentModel.objects.filter(project=project, key="RELEASE_BOT_TOKEN").exists()
        assert body["bot_mode"] == "release"
        assert body["bot_username"] is None


@pytest.mark.django_db
class TestPlainProjectCreateDebugMode:
    def test_mode_debug_starts_debug_container_no_release(self):
        user = _make_user()
        client = _make_auth_client(user)
        url = reverse("project-list")

        deploy_result = MagicMock()
        deploy_result.metadata.name = "debug-svc-plain-1"

        with (
            patch("core.apps.api.views.project.deploy_service", return_value=deploy_result) as mock_deploy,
            patch("telebot.TeleBot") as mock_telebot,
        ):
            mock_telebot.return_value.get_me.return_value.username = "botspace_test_bot"

            response = client.post(url, data={"name": "Debug plain bot", "mode": "debug"}, format="json")

        assert response.status_code == 201, response.json()
        body = response.json()["data"]
        project = ProjectModel.objects.get(pk=body["id"])

        assert not RelaseModel.objects.filter(project=project).exists()
        assert not EnviromentModel.objects.filter(project=project, key="RELEASE_BOT_TOKEN").exists()

        debug = DebugModel.objects.get(project=project)
        assert debug.service_id == "debug-svc-plain-1"
        assert debug.status == "initializing"
        mock_deploy.assert_called_once()
        args, kwargs = mock_deploy.call_args
        assert args[1] == "debug"

        assert body["bot_mode"] == "debug"
        assert body["bot_username"] == "botspace_test_bot"
        assert body["bot_link"] == "https://t.me/botspace_test_bot"

    def test_mode_debug_running_bot_limit_checked_before_create(self):
        """Limit oshib ketsa — 409, va orphan loyiha qolmasligi kerak (parity bilan
        create_from_template: limit tekshiruvi loyiha yaratilishidan OLDIN)."""
        from core.apps.api.exceptions.running_bot_limit import RunningBotLimitExceeded

        user = _make_user()
        client = _make_auth_client(user)
        url = reverse("project-list")

        before_count = ProjectModel.objects.filter(owner=user).count()

        with patch(
            "core.apps.api.views.project.check_running_bot_limit",
            side_effect=RunningBotLimitExceeded(limit=10, running=[]),
        ):
            response = client.post(url, data={"name": "Debug over limit", "mode": "debug"}, format="json")

        assert response.status_code == 409
        assert ProjectModel.objects.filter(owner=user).count() == before_count


@pytest.mark.django_db
class TestPlainProjectCreateManagedBot:
    def test_managed_bot_id_resolves_token_and_returns_bot_info(self):
        user = _make_user()
        managed_bot = _make_managed_bot(user, token="555666:MANAGEDTOK", username="my_managed_bot")
        client = _make_auth_client(user)
        url = reverse("project-list")

        response = client.post(
            url, data={"name": "Managed plain bot", "managed_bot_id": managed_bot.id}, format="json"
        )

        assert response.status_code == 201, response.json()
        body = response.json()["data"]
        project = ProjectModel.objects.get(pk=body["id"])

        env = EnviromentModel.objects.get(project=project, key="RELEASE_BOT_TOKEN")
        assert env.value == "555666:MANAGEDTOK"
        # Release umuman yaratilmaydi — bu faqat token wiring, deploy keyingi /release/ orqali
        assert not RelaseModel.objects.filter(project=project).exists()

        managed_bot.refresh_from_db()
        assert managed_bot.used is True

        assert body["bot_mode"] == "release"
        assert body["bot_username"] == "my_managed_bot"
        assert body["bot_link"] == "https://t.me/my_managed_bot"

    def test_managed_bot_id_not_owned_returns_400_and_no_project(self):
        user = _make_user()
        other_user = _make_user()
        managed_bot = _make_managed_bot(other_user)
        client = _make_auth_client(user)
        url = reverse("project-list")

        response = client.post(
            url, data={"name": "IDOR attempt", "managed_bot_id": managed_bot.id}, format="json"
        )

        assert response.status_code == 400

    def test_managed_bot_id_unknown_returns_400(self):
        user = _make_user()
        client = _make_auth_client(user)
        url = reverse("project-list")

        response = client.post(url, data={"name": "Unknown managed", "managed_bot_id": 999999}, format="json")

        assert response.status_code == 400
