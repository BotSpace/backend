"""create_from_template `mode=debug` (tokensiz) va bot-info enrichment testlari.

Debug rejimida: token/managed_bot_id shart emas, release yaratilmaydi, RELEASE_BOT_TOKEN
o'rnatilmaydi — buning o'rniga loyihaning DEBUG konteyneri ishga tushadi (platforma
TEST_BOT_TOKEN fallback bilan, kubernetes_service.deploy_service ichida). Javobga
bot_mode/bot_username/bot_link qo'shiladi (ikkala rejimda ham).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.api.models.project import DebugModel, EnviromentModel, ProjectModel, RelaseModel
from core.apps.template.models import TemplateModel
from core.apps.template.models.order import TemplateOrderModel


def _make_user() -> User:
    import random

    phone = f"+9989001{random.randint(10000, 99999)}"
    return User.objects.create_user(phone=phone, username=phone, password="pass")


def _make_auth_client(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


def _make_purchased_template(user: User, **extra) -> TemplateModel:
    defaults = dict(
        name="Test template",
        image="template/fake.png",
        short_description="short",
        description="long",
        original_price=Decimal("0.00"),
        is_verify=True,
        required_envs=[],
        spec={"flow": {"nodes": [], "edges": []}},
    )
    defaults.update(extra)
    template = TemplateModel.objects.create(**defaults)
    TemplateOrderModel.objects.create(
        user=user,
        template=template,
        payment_status=True,
        status="confirm",
        amount=Decimal("0.00"),
    )
    return template


URL = None  # resolved lazily inside tests (reverse needs urlconf ready)


@pytest.mark.django_db
class TestCreateFromTemplateDebugMode:
    def test_debug_mode_no_token_deploys_debug_container_and_returns_bot_link(self):
        user = _make_user()
        template = _make_purchased_template(user)

        deploy_result = MagicMock()
        deploy_result.metadata.name = "debug-svc-123"

        with (
            patch("core.apps.api.views.project.deploy_service", return_value=deploy_result) as mock_deploy,
            patch("core.apps.api.views.project.set_webhook") as mock_set_webhook,
            patch("telebot.TeleBot") as mock_telebot,
        ):
            mock_telebot.return_value.get_me.return_value.username = "botspace_test_bot"

            client = _make_auth_client(user)
            url = reverse("project-create-from-template")
            response = client.post(
                url,
                data={"template": template.pk, "name": "Debug bot", "mode": "debug"},
                format="json",
            )

        assert response.status_code == 200, response.json()
        body = response.json()

        # Release umuman yaratilmagan / RELEASE_BOT_TOKEN o'rnatilmagan
        project = ProjectModel.objects.get(pk=body["id"])
        assert not RelaseModel.objects.filter(project=project).exists()
        assert not EnviromentModel.objects.filter(project=project, key="RELEASE_BOT_TOKEN").exists()

        # Debug konteyner ishga tushirilgan
        debug = DebugModel.objects.get(project=project)
        assert debug.service_id == "debug-svc-123"
        assert debug.status == "initializing"
        mock_deploy.assert_called_once()
        args, kwargs = mock_deploy.call_args
        assert args[1] == "debug"
        # Release uchun webhook o'rnatilmaydi
        mock_set_webhook.assert_not_called()

        # Bot-info enrichment
        assert body["bot_mode"] == "debug"
        assert body["bot_username"] == "botspace_test_bot"
        assert body["bot_link"] == "https://t.me/botspace_test_bot"

    def test_debug_mode_writes_template_envs_before_deploy(self):
        user = _make_user()
        template = _make_purchased_template(
            user,
            spec={
                "flow": {"nodes": [], "edges": []},
                "envs": [{"key": "ADMIN_CHAT_ID", "required": True}],
            },
            required_envs=[{"key": "ADMIN_CHAT_ID", "required": True}],
        )

        deploy_result = MagicMock()
        deploy_result.metadata.name = "debug-svc-456"

        captured_envs = {}

        def _fake_deploy(project, prefix, flow, key, _env=None, **kw):
            captured_envs["_env"] = list(_env or [])
            return deploy_result

        with (
            patch("core.apps.api.views.project.deploy_service", side_effect=_fake_deploy),
            patch("core.apps.api.views.project.set_webhook"),
            patch("telebot.TeleBot") as mock_telebot,
        ):
            mock_telebot.return_value.get_me.return_value.username = "botspace_test_bot"

            client = _make_auth_client(user)
            url = reverse("project-create-from-template")
            response = client.post(
                url,
                data={
                    "template": template.pk,
                    "name": "Debug bot 2",
                    "mode": "debug",
                    "envs": {"ADMIN_CHAT_ID": "123456789"},
                },
                format="json",
            )

        assert response.status_code == 200, response.json()
        project = ProjectModel.objects.get(pk=response.json()["id"])
        assert EnviromentModel.objects.filter(project=project, key="ADMIN_CHAT_ID", value="123456789").exists()
        assert any("ADMIN_CHAT_ID=123456789" in e for e in captured_envs["_env"])

    def test_debug_mode_missing_required_env_still_400(self):
        """envs validatsiyasi mode'dan qat'i nazar ishlaydi."""
        user = _make_user()
        template = _make_purchased_template(
            user,
            spec={
                "flow": {"nodes": [], "edges": []},
                "envs": [{"key": "ADMIN_CHAT_ID", "required": True}],
            },
            required_envs=[{"key": "ADMIN_CHAT_ID", "required": True}],
        )

        client = _make_auth_client(user)
        url = reverse("project-create-from-template")
        response = client.post(
            url,
            data={"template": template.pk, "name": "Debug bot 3", "mode": "debug"},
            format="json",
        )
        assert response.status_code == 400

    def test_release_mode_still_requires_token(self):
        user = _make_user()
        template = _make_purchased_template(user)

        client = _make_auth_client(user)
        url = reverse("project-create-from-template")
        response = client.post(
            url,
            data={"template": template.pk, "name": "Release bot"},
            format="json",
        )
        assert response.status_code == 400

    def test_release_mode_creates_release_and_bot_link(self):
        user = _make_user()
        template = _make_purchased_template(user)

        with (
            patch("core.apps.api.views.project.set_webhook") as mock_set_webhook,
            patch("core.apps.api.signals.project.deploy_service") as mock_signal_deploy,
            patch("core.apps.api.signals.project.sync_bot"),
            patch("telebot.TeleBot") as mock_telebot,
        ):
            mock_signal_deploy.return_value.metadata.name = "release-svc-1"
            mock_telebot.return_value.get_me.return_value.username = "my_release_bot"

            client = _make_auth_client(user)
            url = reverse("project-create-from-template")
            response = client.post(
                url,
                data={
                    "template": template.pk,
                    "name": "Release bot",
                    "mode": "release",
                    "token": "123456:ABCDEF",
                },
                format="json",
            )

        assert response.status_code == 200, response.json()
        body = response.json()
        project = ProjectModel.objects.get(pk=body["id"])
        assert RelaseModel.objects.filter(project=project).exists()
        assert EnviromentModel.objects.filter(project=project, key="RELEASE_BOT_TOKEN", value="123456:ABCDEF").exists()
        mock_set_webhook.assert_called_once()

        assert body["bot_mode"] == "release"
        assert body["bot_username"] == "my_release_bot"
        assert body["bot_link"] == "https://t.me/my_release_bot"
