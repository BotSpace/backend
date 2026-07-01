import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.api.models.managed_bot import ManagedBotModel
from core.apps.credentials.services import crypto

User = get_user_model()


@pytest.fixture
def user(db):
    return baker.make(User)


@pytest.fixture
def client_auth(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def manager_settings(settings):
    settings.MANAGER_BOT_TOKEN = "test_token"
    settings.MANAGER_BOT_USERNAME = "testbot"
    settings.MANAGER_BOT_WEBHOOK_SECRET = "test_secret"
    return settings


WEBHOOK_URL = "/api/managed-bot/webhook/test_secret/"


@pytest.mark.django_db
class TestManagedBotWebhook:
    def test_wrong_secret_path_returns_403(self, client, manager_settings):
        resp = client.post(
            "/api/managed-bot/webhook/wrong_secret/",
            data={},
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test_secret",
        )
        assert resp.status_code == 403

    def test_wrong_header_returns_403(self, client, manager_settings):
        resp = client.post(
            WEBHOOK_URL,
            data={},
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong",
        )
        assert resp.status_code == 403

    def test_no_managed_bot_returns_200(self, client, manager_settings):
        resp = client.post(
            WEBHOOK_URL,
            data={"update_id": 1},
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test_secret",
        )
        assert resp.status_code == 200

    @patch("core.apps.api.services.managed_bot.fetch_managed_bot_token", return_value="bot_token_123")
    def test_managed_bot_update_creates_model(self, mock_fetch, client, db, manager_settings):
        payload = {
            "managed_bot": {
                "bot": {"id": 999, "username": "mynewbot", "first_name": "My Bot"},
                "user": {"id": 1234567},
            }
        }
        resp = client.post(
            WEBHOOK_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test_secret",
        )
        assert resp.status_code == 200
        mb = ManagedBotModel.objects.get(tg_bot_id=999)
        assert mb.username == "mynewbot"
        assert mb.get_token() == "bot_token_123"

    @patch("core.apps.api.services.managed_bot.fetch_managed_bot_token", return_value="tok")
    def test_creator_linked_to_user(self, mock_fetch, client, db, manager_settings, user):
        from core.apps.authbot.models.user import BotUser

        bot_user = BotUser.objects.create(user_id=77777, phone=user.phone)
        payload = {
            "managed_bot": {
                "bot": {"id": 888, "username": "linkedbot", "first_name": "Linked"},
                "user": {"id": 77777},
            }
        }
        resp = client.post(
            WEBHOOK_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test_secret",
        )
        assert resp.status_code == 200
        mb = ManagedBotModel.objects.get(tg_bot_id=888)
        assert mb.owner_id == user.pk

    @patch("core.apps.api.services.managed_bot.fetch_managed_bot_token", return_value=None)
    def test_no_token_from_api_returns_200(self, mock_fetch, client, db, manager_settings):
        payload = {
            "managed_bot": {
                "bot": {"id": 111, "username": "notoken", "first_name": "NoToken"},
                "user": {"id": 9999},
            }
        }
        resp = client.post(
            WEBHOOK_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test_secret",
        )
        assert resp.status_code == 200
        assert not ManagedBotModel.objects.filter(tg_bot_id=111).exists()


@pytest.mark.django_db
class TestManagedBotConfig:
    def test_enabled(self, client_auth, manager_settings):
        resp = client_auth.get("/api/managed-bot/config/")
        assert resp.status_code == 200
        assert resp.data["enabled"] is True
        assert "manager_username" in resp.data

    def test_disabled_when_no_token(self, client_auth, settings):
        settings.MANAGER_BOT_TOKEN = ""
        resp = client_auth.get("/api/managed-bot/config/")
        assert resp.status_code == 200
        assert resp.data["enabled"] is False

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/managed-bot/config/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestManagedBotList:
    def test_returns_only_own_bots(self, client_auth, db, user):
        other_user = baker.make(User)
        mb1 = baker.make(ManagedBotModel, owner=user, tg_bot_id=1001, token_encrypted=crypto.encrypt({"token": "t1"}))
        baker.make(ManagedBotModel, owner=other_user, tg_bot_id=1002, token_encrypted=crypto.encrypt({"token": "t2"}))

        resp = client_auth.get("/api/managed-bot/")
        assert resp.status_code == 200
        ids = [b["id"] for b in resp.data]
        assert mb1.id in ids
        assert len(ids) == 1

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/managed-bot/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestManagedBotIdorProtection:
    def test_managed_bot_id_idor_protection(self, client_auth, db, user):
        other_user = baker.make(User)
        mb = baker.make(
            ManagedBotModel,
            owner=other_user,
            tg_bot_id=5555,
            token_encrypted=crypto.encrypt({"token": "secret_tok"}),
        )

        from decimal import Decimal
        from unittest.mock import patch, MagicMock

        from core.apps.template.models import TemplateModel
        from core.apps.template.models.order import TemplateOrderModel

        tmpl = baker.make(
            TemplateModel,
            spec={"flow": {"nodes": [], "edges": []}},
            required_envs=[],
            is_verify=True,
        )
        TemplateOrderModel.objects.create(
            user=user,
            template=tmpl,
            payment_status=True,
            status="confirm",
            amount=Decimal("0.00"),
        )

        magic = MagicMock()
        magic.metadata.name = "test-svc"
        with (
            patch("core.apps.api.views.project.set_webhook"),
            patch("core.apps.api.views.project.deploy_service", return_value=magic),
            patch("core.apps.api.signals.project.deploy_service", return_value=magic),
            patch("core.apps.api.signals.project.sync_bot"),
            patch("core.apps.api.views.project.copy_collections"),
        ):
            resp = client_auth.post(
                "/api/project/create-from-template/",
                data={"template": tmpl.id, "name": "Test", "managed_bot_id": mb.id},
                format="json",
            )
        assert resp.status_code in (400, 403)

    def test_no_token_no_managed_bot_400(self, client_auth, db, user):
        from decimal import Decimal

        from core.apps.template.models import TemplateModel
        from core.apps.template.models.order import TemplateOrderModel

        tmpl = baker.make(
            TemplateModel,
            spec={"flow": {"nodes": [], "edges": []}},
            required_envs=[],
            is_verify=True,
        )
        TemplateOrderModel.objects.create(
            user=user,
            template=tmpl,
            payment_status=True,
            status="confirm",
            amount=Decimal("0.00"),
        )

        resp = client_auth.post(
            "/api/project/create-from-template/",
            data={"template": tmpl.id, "name": "Test"},
            format="json",
        )
        assert resp.status_code == 400
